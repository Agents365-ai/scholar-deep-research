#!/usr/bin/env python3
"""research_state.py — central state management for scholar-deep-research.

The state file is the single source of truth. Every other script reads from
and writes to it. Operations are idempotent on the file.

Schema (abbreviated):
{
  "schema_version": 1,
  "question": "...",
  "archetype": "literature_review",
  "phase": 0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "queries": [{"source", "query", "round", "hits", "new", "timestamp"}],
  "papers": {
    "<id>": {
      "id", "doi", "title", "authors", "year", "venue", "abstract",
      "citations", "url", "pdf_url", "source": ["openalex", ...],
      "score", "score_components": {...},
      "selected": false, "depth": "shallow|full",
      "evidence": {"method", "findings", "limitations", "relevance"},
      "discovered_via": "search|citation_chase",
      "tags": [], "first_seen_round": 1
    }
  },
  "selected_ids": [],
  "themes": [{"name", "summary", "paper_ids"}],
  "tensions": [{"topic", "sides": [{"position", "paper_ids"}]}],
  "self_critique": {"findings": [], "resolved": [], "appendix": ""},
  "report_path": null
}

Paper IDs are normalized:
  doi:10.1038/nature12373    (preferred)
  openalex:W2059403765       (fallback)
  arxiv:2301.12345           (preprints without DOI)
  pmid:12345678              (PubMed without DOI)

All commands accept --state PATH (default: research_state.json) and emit
JSON to stdout when reading, or write the state file in place when mutating.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


# ---------- IO ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        sys.exit(f"error: state file not found: {path}\n"
                 f"hint: run `research_state.py init --question ...` first")
    return json.loads(path.read_text())


def save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ---------- ID normalization ----------

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip().lower()
    raw = raw.replace("https://doi.org/", "").replace("http://doi.org/", "")
    raw = raw.replace("doi:", "").strip()
    m = DOI_RE.search(raw)
    return m.group(0) if m else None


def normalize_title(title: str) -> str:
    """Aggressive normalization for fuzzy title match."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def make_paper_id(paper: dict[str, Any]) -> str:
    """Pick the best canonical ID for a paper record."""
    doi = normalize_doi(paper.get("doi"))
    if doi:
        return f"doi:{doi}"
    if paper.get("openalex_id"):
        return f"openalex:{paper['openalex_id']}"
    if paper.get("arxiv_id"):
        return f"arxiv:{paper['arxiv_id']}"
    if paper.get("pmid"):
        return f"pmid:{paper['pmid']}"
    # last resort: hash of normalized title
    nt = normalize_title(paper.get("title", ""))
    return f"title:{nt[:80]}"


# ---------- commands ----------

def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists() and not args.force:
        sys.exit(f"error: {path} already exists. Use --force to overwrite.")
    state = {
        "schema_version": SCHEMA_VERSION,
        "question": args.question,
        "archetype": args.archetype,
        "phase": 0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "queries": [],
        "papers": {},
        "selected_ids": [],
        "themes": [],
        "tensions": [],
        "self_critique": {"findings": [], "resolved": [], "appendix": ""},
        "report_path": None,
    }
    save_state(path, state)
    print(json.dumps({"ok": True, "state": str(path), "phase": 0}))


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest search results from a JSON file produced by a search script.

    Input shape: {"source": "openalex", "query": "...", "round": 1, "papers": [...]}
    """
    state = load_state(Path(args.state))
    payload = json.loads(Path(args.input).read_text())
    source = payload.get("source", "unknown")
    query = payload.get("query", "")
    rnd = payload.get("round", 1)
    incoming = payload.get("papers", [])

    new_count = 0
    merged_count = 0
    for p in incoming:
        pid = make_paper_id(p)
        p["id"] = pid
        p.setdefault("source", [])
        if source not in p["source"]:
            p["source"].append(source)
        p.setdefault("first_seen_round", rnd)
        p.setdefault("selected", False)
        p.setdefault("depth", "shallow")
        p.setdefault("discovered_via", "search")

        if pid in state["papers"]:
            existing = state["papers"][pid]
            # merge sources, prefer richer fields
            for s in p["source"]:
                if s not in existing.get("source", []):
                    existing.setdefault("source", []).append(s)
            for k in ("doi", "abstract", "pdf_url", "url", "venue", "citations"):
                if not existing.get(k) and p.get(k):
                    existing[k] = p[k]
            merged_count += 1
        else:
            state["papers"][pid] = p
            new_count += 1

    state["queries"].append({
        "source": source,
        "query": query,
        "round": rnd,
        "hits": len(incoming),
        "new": new_count,
        "merged": merged_count,
        "timestamp": now_iso(),
    })
    save_state(Path(args.state), state)
    print(json.dumps({
        "ok": True,
        "ingested": len(incoming),
        "new": new_count,
        "merged": merged_count,
        "total_papers": len(state["papers"]),
    }))


def cmd_select(args: argparse.Namespace) -> None:
    """Mark the top-N papers (by .score) as selected."""
    state = load_state(Path(args.state))
    ranked = sorted(
        state["papers"].values(),
        key=lambda p: p.get("score", 0.0),
        reverse=True,
    )
    chosen = ranked[: args.top]
    chosen_ids = [p["id"] for p in chosen]
    for pid, p in state["papers"].items():
        p["selected"] = pid in chosen_ids
    state["selected_ids"] = chosen_ids
    save_state(Path(args.state), state)
    print(json.dumps({
        "ok": True,
        "selected": len(chosen_ids),
        "ids": chosen_ids,
    }))


def cmd_saturation(args: argparse.Namespace) -> None:
    """Check whether the latest round saturated discovery.

    Saturated when:
      - last round's `new` count is < threshold% of last round's `hits`, AND
      - no new paper in the last round has > max_citations citations.
    """
    state = load_state(Path(args.state))
    if not state["queries"]:
        sys.exit("error: no queries recorded yet")
    last = state["queries"][-1]
    pct_new = (last["new"] / last["hits"] * 100) if last["hits"] else 0
    # check max citations among papers first seen in this round
    max_cit = 0
    for p in state["papers"].values():
        if p.get("first_seen_round") == last["round"]:
            max_cit = max(max_cit, p.get("citations", 0) or 0)
    saturated = pct_new < args.threshold and max_cit < args.max_citations
    print(json.dumps({
        "round": last["round"],
        "source": last["source"],
        "new_pct": round(pct_new, 1),
        "max_new_citations": max_cit,
        "threshold_pct": args.threshold,
        "max_citations_threshold": args.max_citations,
        "saturated": saturated,
    }))


def cmd_set(args: argparse.Namespace) -> None:
    """Set a top-level state field. Used for phase advance, archetype change, etc."""
    state = load_state(Path(args.state))
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    state[args.field] = value
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "field": args.field, "value": value}))


def cmd_query(args: argparse.Namespace) -> None:
    """Read a slice of state for inspection."""
    state = load_state(Path(args.state))
    if args.what == "summary":
        out = {
            "question": state["question"],
            "archetype": state["archetype"],
            "phase": state["phase"],
            "papers": len(state["papers"]),
            "selected": len(state["selected_ids"]),
            "queries": len(state["queries"]),
            "themes": len(state["themes"]),
            "tensions": len(state["tensions"]),
            "report_path": state.get("report_path"),
        }
    elif args.what == "selected":
        out = [state["papers"][pid] for pid in state["selected_ids"]
               if pid in state["papers"]]
    elif args.what == "papers":
        out = list(state["papers"].values())
    elif args.what == "queries":
        out = state["queries"]
    elif args.what == "themes":
        out = state["themes"]
    elif args.what == "tensions":
        out = state["tensions"]
    elif args.what == "critique":
        out = state.get("self_critique", {})
    else:
        sys.exit(f"unknown query: {args.what}")
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_evidence(args: argparse.Namespace) -> None:
    """Attach evidence (extracted reading) to a paper."""
    state = load_state(Path(args.state))
    if args.id not in state["papers"]:
        sys.exit(f"unknown paper id: {args.id}")
    paper = state["papers"][args.id]
    paper["evidence"] = {
        "method": args.method,
        "findings": args.findings or [],
        "limitations": args.limitations or "",
        "relevance": args.relevance or "",
    }
    paper["depth"] = args.depth
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "id": args.id, "depth": args.depth}))


def cmd_theme(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    state["themes"].append({
        "name": args.name,
        "summary": args.summary or "",
        "paper_ids": args.paper_ids or [],
    })
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "theme": args.name}))


def cmd_tension(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    state["tensions"].append({
        "topic": args.topic,
        "sides": json.loads(args.sides),
    })
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "topic": args.topic}))


def cmd_critique(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    crit = state.setdefault("self_critique",
                            {"findings": [], "resolved": [], "appendix": ""})
    if args.finding:
        crit["findings"].append(args.finding)
    if args.resolve:
        crit["resolved"].append(args.resolve)
    if args.appendix:
        crit["appendix"] = args.appendix
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "critique": crit}))


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research_state.py",
        description="Central state file management for scholar-deep-research.",
    )
    p.add_argument("--state", default="research_state.json",
                   help="Path to the state file (default: research_state.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Create a new state file")
    s.add_argument("--question", required=True)
    s.add_argument("--archetype", default="literature_review",
                   choices=["literature_review", "systematic_review",
                            "scoping_review", "comparative_analysis",
                            "grant_background"])
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("ingest", help="Ingest search results from a JSON file")
    s.add_argument("--input", required=True)
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("select", help="Mark top-N (by score) as selected")
    s.add_argument("--top", type=int, default=20)
    s.set_defaults(func=cmd_select)

    s = sub.add_parser("saturation", help="Check whether the last round saturated")
    s.add_argument("--threshold", type=float, default=20.0,
                   help="New-paper percentage below which we consider saturated (default 20)")
    s.add_argument("--max-citations", type=int, default=100,
                   help="If a new paper has more citations than this, we are NOT saturated")
    s.set_defaults(func=cmd_saturation)

    s = sub.add_parser("set", help="Set a top-level field (e.g., phase)")
    s.add_argument("--field", required=True)
    s.add_argument("--value", required=True)
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("query", help="Read a slice of state")
    s.add_argument("what", choices=["summary", "selected", "papers", "queries",
                                    "themes", "tensions", "critique"])
    s.set_defaults(func=cmd_query)

    s = sub.add_parser("evidence", help="Attach evidence to a paper")
    s.add_argument("--id", required=True)
    s.add_argument("--method", required=True)
    s.add_argument("--findings", nargs="*")
    s.add_argument("--limitations")
    s.add_argument("--relevance")
    s.add_argument("--depth", choices=["full", "shallow"], default="full")
    s.set_defaults(func=cmd_evidence)

    s = sub.add_parser("theme", help="Add a theme")
    s.add_argument("--name", required=True)
    s.add_argument("--summary")
    s.add_argument("--paper-ids", nargs="*")
    s.set_defaults(func=cmd_theme)

    s = sub.add_parser("tension", help="Add a tension")
    s.add_argument("--topic", required=True)
    s.add_argument("--sides", required=True,
                   help='JSON array: [{"position": "...", "paper_ids": ["..."]}]')
    s.set_defaults(func=cmd_tension)

    s = sub.add_parser("critique", help="Append a self-critique finding/appendix")
    s.add_argument("--finding")
    s.add_argument("--resolve")
    s.add_argument("--appendix")
    s.set_defaults(func=cmd_critique)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
