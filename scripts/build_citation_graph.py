#!/usr/bin/env python3
"""build_citation_graph.py — snowball search via OpenAlex citation links.

Two directions:
  - backward: papers that this paper *cites* (its references)
  - forward:  papers that cite *this* paper (downstream impact)

Reads the top-N selected (or score-ranked) papers from state, queries OpenAlex
for their refs / cited-by, normalizes the new candidates, and ingests them
back into state with discovered_via="citation_chase". Existing papers (matched
on DOI / OpenAlex ID) are skipped.

Re-running this script after changing --seed-top is safe — already-fetched
papers will be re-merged, not duplicated.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from _common import USER_AGENT, make_paper, make_payload
from research_state import load_state, make_paper_id, save_state, now_iso

WORKS = "https://api.openalex.org/works"


def fetch_work(oa_id: str, email: str | None) -> dict | None:
    headers = {"User-Agent": USER_AGENT}
    params = {}
    if email:
        params["mailto"] = email
        headers["From"] = email
    try:
        r = httpx.get(f"{WORKS}/{oa_id}", params=params,
                      headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        sys.stderr.write(f"openalex fetch error for {oa_id}: {e}\n")
        return None


def fetch_referenced(oa_ids: list[str], email: str | None) -> list[dict]:
    """Batch-fetch referenced works by OpenAlex IDs (limit 25 per request via filter)."""
    out = []
    chunk = 25
    headers = {"User-Agent": USER_AGENT}
    for i in range(0, len(oa_ids), chunk):
        batch = oa_ids[i:i + chunk]
        params: dict[str, Any] = {
            "filter": "openalex_id:" + "|".join(batch),
            "per-page": chunk,
            "select": "id,doi,title,authorships,publication_year,host_venue,"
                      "primary_location,cited_by_count,abstract_inverted_index",
        }
        if email:
            params["mailto"] = email
        try:
            r = httpx.get(WORKS, params=params, headers=headers, timeout=30.0)
            r.raise_for_status()
            out.extend(r.json().get("results", []))
        except httpx.HTTPError as e:
            sys.stderr.write(f"openalex batch error: {e}\n")
        time.sleep(0.1)
    return out


def fetch_cited_by(oa_id: str, limit: int, email: str | None) -> list[dict]:
    headers = {"User-Agent": USER_AGENT}
    params: dict[str, Any] = {
        "filter": f"cites:{oa_id}",
        "per-page": min(limit, 200),
        "select": "id,doi,title,authorships,publication_year,host_venue,"
                  "primary_location,cited_by_count,abstract_inverted_index",
    }
    if email:
        params["mailto"] = email
    try:
        r = httpx.get(WORKS, params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json().get("results", [])
    except httpx.HTTPError as e:
        sys.stderr.write(f"openalex cited-by error for {oa_id}: {e}\n")
        return []


def normalize(w: dict[str, Any]) -> dict[str, Any]:
    # Reuse the OpenAlex normalizer logic (kept inline to avoid cross-import).
    from search_openalex import _normalize  # local import for clarity
    return _normalize(w)


def main() -> None:
    p = argparse.ArgumentParser(description="Build citation graph from state.")
    p.add_argument("--state", default="research_state.json")
    p.add_argument("--seed-top", type=int, default=8,
                   help="Number of top-ranked papers to use as seeds")
    p.add_argument("--direction", choices=["forward", "backward", "both"],
                   default="both")
    p.add_argument("--depth", type=int, default=1,
                   help="Currently only depth=1 supported")
    p.add_argument("--cited-by-limit", type=int, default=50,
                   help="Max cited-by results per seed")
    p.add_argument("--email", help="Polite pool email")
    args = p.parse_args()

    path = Path(args.state)
    state = load_state(path)

    # pick seeds: prefer .selected_ids, fall back to top-by-score
    if state.get("selected_ids"):
        seeds = [state["papers"][pid] for pid in state["selected_ids"]
                 if pid in state["papers"]][: args.seed_top]
    else:
        seeds = sorted(state["papers"].values(),
                       key=lambda x: x.get("score", 0),
                       reverse=True)[: args.seed_top]

    if not seeds:
        sys.exit("error: no seed papers (run rank_papers.py and select first)")

    new_records: list[dict[str, Any]] = []

    for seed in seeds:
        oa_id = seed.get("openalex_id")
        if not oa_id:
            sys.stderr.write(f"skipping seed without openalex_id: {seed['id']}\n")
            continue

        if args.direction in ("backward", "both"):
            full = fetch_work(oa_id, args.email)
            if full:
                refs = full.get("referenced_works", [])
                ref_ids = [r.rsplit("/", 1)[-1] for r in refs if r]
                if ref_ids:
                    works = fetch_referenced(ref_ids, args.email)
                    for w in works:
                        new_records.append(normalize(w))

        if args.direction in ("forward", "both"):
            cited_by = fetch_cited_by(oa_id, args.cited_by_limit, args.email)
            for w in cited_by:
                new_records.append(normalize(w))

    # Merge new records into state, marking discovered_via
    added = 0
    merged = 0
    for rec in new_records:
        pid = make_paper_id(rec)
        rec["id"] = pid
        rec.setdefault("source", ["openalex"])
        rec.setdefault("first_seen_round", state["queries"][-1]["round"]
                       if state["queries"] else 1)
        rec["discovered_via"] = "citation_chase"
        rec.setdefault("selected", False)
        rec.setdefault("depth", "shallow")
        if pid in state["papers"]:
            existing = state["papers"][pid]
            for k in ("doi", "abstract", "pdf_url", "url", "venue"):
                if not existing.get(k) and rec.get(k):
                    existing[k] = rec[k]
            merged += 1
        else:
            state["papers"][pid] = rec
            added += 1

    state["queries"].append({
        "source": "openalex_citation_chase",
        "query": f"seeds={len(seeds)} direction={args.direction}",
        "round": (state["queries"][-1]["round"] + 1) if state["queries"] else 1,
        "hits": len(new_records),
        "new": added,
        "merged": merged,
        "timestamp": now_iso(),
    })
    save_state(path, state)

    print(json.dumps({
        "ok": True,
        "seeds": len(seeds),
        "fetched": len(new_records),
        "added": added,
        "merged": merged,
        "total_papers": len(state["papers"]),
    }))


if __name__ == "__main__":
    main()
