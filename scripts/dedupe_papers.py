#!/usr/bin/env python3
"""dedupe_papers.py — collapse duplicate papers in the state file.

Why this exists: searches across OpenAlex, Crossref, PubMed, and arXiv produce
overlapping records. The ingest step already deduplicates by ID, but the same
paper can appear under different IDs (e.g., a DOI from Crossref and an arXiv
ID from arXiv before the journal version was indexed).

Strategy:
  1. Group by normalized DOI when present (canonical).
  2. For records without DOIs, group by normalized title + first-author last name.
  3. Within each group, merge into the record with the most populated DOI/abstract,
     accumulating `source` and preferring richer metadata.

This script is idempotent: running it twice on the same state file produces
the same result.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from _common import maybe_emit_schema, ok
from research_state import load_state, save_state, normalize_title


def first_author_key(p: dict[str, Any]) -> str:
    authors = p.get("authors") or []
    if not authors:
        return ""
    first = authors[0].lower()
    # last token is usually the surname (works for "First Last", less so
    # for "Last, First" but acceptable as a clustering key)
    parts = re.split(r"[,\s]+", first.strip())
    parts = [x for x in parts if x]
    return parts[-1] if parts else ""


def cluster_key(p: dict[str, Any]) -> str:
    """Key for grouping potentially-duplicate records."""
    if p.get("doi"):
        return f"doi:{p['doi'].lower()}"
    nt = normalize_title(p.get("title") or "")
    if not nt:
        return f"id:{p.get('id', '')}"
    return f"t:{nt[:80]}::a:{first_author_key(p)}::y:{p.get('year') or ''}"


def merge(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge a cluster of duplicates into one record."""
    # Sort by score: most DOI > most-populated abstract > highest cite count
    def populated(r: dict[str, Any]) -> int:
        return sum(1 for f in ("doi", "abstract", "pdf_url", "venue", "year",
                                "citations") if r.get(f))
    records = sorted(records, key=populated, reverse=True)
    base = dict(records[0])
    for other in records[1:]:
        for s in other.get("source", []):
            if s not in base.setdefault("source", []):
                base["source"].append(s)
        for k in ("doi", "abstract", "pdf_url", "url", "venue",
                  "openalex_id", "arxiv_id", "pmid"):
            if not base.get(k) and other.get(k):
                base[k] = other[k]
        # citation count: max wins
        bc = base.get("citations") or 0
        oc = other.get("citations") or 0
        if oc > bc:
            base["citations"] = oc
        # round info: keep earliest first_seen_round
        if other.get("first_seen_round") and (
            not base.get("first_seen_round")
            or other["first_seen_round"] < base["first_seen_round"]
        ):
            base["first_seen_round"] = other["first_seen_round"]
    return base


def main() -> None:
    p = argparse.ArgumentParser(description="Deduplicate papers in state.")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Print clusters without modifying state")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "dedupe_papers")
    args = p.parse_args()

    path = Path(args.state)
    state = load_state(path)
    papers = list(state["papers"].values())

    clusters: dict[str, list[dict[str, Any]]] = {}
    for pap in papers:
        clusters.setdefault(cluster_key(pap), []).append(pap)

    duplicates = {k: v for k, v in clusters.items() if len(v) > 1}
    if args.dry_run:
        ok({
            "dry_run": True,
            "total_papers": len(papers),
            "duplicate_clusters": len(duplicates),
            "clusters": [{"key": k, "ids": [r["id"] for r in v]}
                         for k, v in duplicates.items()],
        })
        return

    # Build new papers dict from merged clusters
    from research_state import make_paper_id
    new_papers: dict[str, dict[str, Any]] = {}
    merged_count = 0
    for cluster in clusters.values():
        merged = merge(cluster) if len(cluster) > 1 else cluster[0]
        if len(cluster) > 1:
            merged_count += 1
        new_id = make_paper_id(merged)
        merged["id"] = new_id
        # If two clusters collapse to the same id (rare), prefer the more populated
        if new_id in new_papers:
            new_papers[new_id] = merge([new_papers[new_id], merged])
        else:
            new_papers[new_id] = merged

    state["papers"] = new_papers
    save_state(path, state)
    ok({
        "before": len(papers),
        "after": len(new_papers),
        "merged_clusters": merged_count,
    })


if __name__ == "__main__":
    main()
