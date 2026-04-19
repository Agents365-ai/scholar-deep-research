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
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from _common import (
    EXIT_STATE, EXIT_VALIDATION, err, maybe_emit_schema, ok,
)
from _locking import StateLockTimeout, locked_rmw

SCHEMA_VERSION = 1

# Whitelist of fields `set` is permitted to write. `papers`, `queries`,
# `self_critique`, and everything else must be mutated through the dedicated
# commands so an agent cannot silently wipe the corpus via `set --field papers`.
SETTABLE_FIELDS = {"phase", "archetype", "report_path"}


# ---------- IO ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        err("state_not_found",
            f"State file not found: {path}. "
            f"Run `research_state.py init --question ...` first.",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path))
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        err("state_corrupt",
            f"State file {path} is not valid JSON: {e}",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    """Atomic, unlocked write. Caller is responsible for locking.

    Used by `cmd_init` (where the file is created fresh under --force
    control) and by the mutator passed to `_locked_rmw` after it has
    already acquired the exclusive lock. Do NOT call from outside this
    module or without holding the state lock — use `_locked_rmw` or one
    of the public `apply_*` helpers instead.
    """
    state["updated_at"] = now_iso()
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def _locked_rmw(
    path: Path,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run `mutator` on the state file under an exclusive lock.

    The mutator receives the current state and returns the new state.
    `updated_at` is stamped automatically after the mutator returns.
    If the lock cannot be acquired within `timeout`, emits a structured
    `state_locked` error and exits with EXIT_STATE (retryable).
    """
    def _wrap(state: dict[str, Any]) -> dict[str, Any]:
        new_state = mutator(state)
        new_state["updated_at"] = now_iso()
        return new_state

    try:
        return locked_rmw(path, _wrap, timeout=timeout, loader=load_state)
    except StateLockTimeout as exc:
        err("state_locked", str(exc),
            retryable=True, exit_code=EXIT_STATE, path=str(path))


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
        err("state_exists",
            f"{path} already exists. Pass --force to overwrite.",
            retryable=False, exit_code=EXIT_VALIDATION,
            path=str(path))
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
    # init writes a fresh file; no prior state to RMW. --force controls
    # overwrite races at the human/orchestrator layer, not via the lock.
    path.parent.mkdir(parents=True, exist_ok=True)
    _save_state(path, state)
    ok({"state": str(path), "phase": 0, "schema_version": SCHEMA_VERSION})


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest search results from a JSON file produced by a search script.

    Input shape: {"source": "openalex", "query": "...", "round": 1, "papers": [...]}
    """
    payload = json.loads(Path(args.input).read_text())
    summary = apply_ingest(Path(args.state), payload)
    ok(summary)


def apply_ingest(state_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Library API for ingesting a search payload into state.

    Called by the ingest subcommand AND by `_common.emit()` (which used to
    spawn this script as a subprocess and pass a shared temp-file path —
    that race is gone now). Serializes via the exclusive state lock, so
    concurrent Phase 1 searches are safe.

    Returns the ingestion summary dict (to be emitted by the caller).
    """
    source = payload.get("source", "unknown")
    query = payload.get("query", "")
    rnd = payload.get("round", 1)
    incoming = payload.get("papers", [])

    summary: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
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
        summary.update({
            "source": source,
            "query": query,
            "round": rnd,
            "ingested": len(incoming),
            "new": new_count,
            "merged": merged_count,
            "total_papers": len(state["papers"]),
        })
        return state

    _locked_rmw(state_path, mutator)
    return summary


# ---------- library API for other scripts ----------
#
# Scripts that mutate state (rank_papers, dedupe_papers, build_citation_graph)
# call these instead of writing the state file directly. The public `apply_*`
# functions are the ONLY supported write path — `_save_state` is private and
# only used from inside the lock. Together they enforce the "only research_state
# writes the state file" invariant at the module boundary.

def apply_ranking(
    state_path: Path,
    scored_papers: dict[str, dict[str, Any]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Apply ranking scores + components to state.

    `scored_papers` maps `paper_id -> {"score": float, "score_components": {...}}`.
    `meta` is the ranking metadata dict (formula, weights, half_life, ranked_at).
    Returns a summary dict with `ranked` count and formula.
    """
    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        for pid, scoring in scored_papers.items():
            if pid in state["papers"]:
                state["papers"][pid]["score"] = scoring["score"]
                state["papers"][pid]["score_components"] = scoring["score_components"]
        state["ranking"] = meta
        return state

    _locked_rmw(state_path, mutator)
    return {"ranked": len(scored_papers), "formula": meta.get("formula")}


def apply_dedupe(
    state_path: Path,
    new_papers: dict[str, dict[str, Any]],
    id_remap: dict[str, str],
) -> dict[str, Any]:
    """Replace state.papers with `new_papers` and rewrite ID-bearing collections.

    The rewrite uses `id_remap: {old_id -> new_id}`. References to IDs that
    no longer exist in `new_papers` are dropped. Runs inside the lock so the
    swap and the rewrite are atomic — a concurrent reader sees either the
    pre-dedupe or the post-dedupe state, never a mix.
    """
    def remap(pid: str) -> str:
        return id_remap.get(pid, pid)

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["papers"] = new_papers
        if state.get("selected_ids"):
            seen: set[str] = set()
            rewritten: list[str] = []
            for pid in state["selected_ids"]:
                new_pid = remap(pid)
                if new_pid in new_papers and new_pid not in seen:
                    rewritten.append(new_pid)
                    seen.add(new_pid)
            state["selected_ids"] = rewritten
        for theme in state.get("themes", []):
            if "paper_ids" in theme:
                theme["paper_ids"] = sorted({
                    remap(pid) for pid in theme["paper_ids"]
                    if remap(pid) in new_papers
                })
        for tension in state.get("tensions", []):
            for side in tension.get("sides", []):
                if "paper_ids" in side:
                    side["paper_ids"] = sorted({
                        remap(pid) for pid in side["paper_ids"]
                        if remap(pid) in new_papers
                    })
        return state

    _locked_rmw(state_path, mutator)
    return {"after": len(new_papers), "ids_remapped": len(id_remap)}


def apply_citation_chase(
    state_path: Path,
    new_records: list[dict[str, Any]],
    query_entry: dict[str, Any],
) -> dict[str, Any]:
    """Merge `new_records` into state.papers and append a chase query entry.

    `query_entry` is a partial record: `source`, `query` (description), and
    optionally `round` must be provided. `hits`, `new`, `merged`, and
    `timestamp` are computed here.
    """
    summary: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        added = 0
        merged = 0
        for rec in new_records:
            pid = make_paper_id(rec)
            rec["id"] = pid
            rec.setdefault("source", ["openalex"])
            rec.setdefault(
                "first_seen_round",
                state["queries"][-1]["round"] if state["queries"] else 1,
            )
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

        final_query = dict(query_entry)
        if "round" not in final_query:
            final_query["round"] = (
                state["queries"][-1]["round"] + 1
                if state["queries"] else 1
            )
        final_query["hits"] = len(new_records)
        final_query["new"] = added
        final_query["merged"] = merged
        final_query["timestamp"] = now_iso()
        state["queries"].append(final_query)

        summary.update({
            "added": added,
            "merged": merged,
            "total_papers": len(state["papers"]),
            "round": final_query["round"],
        })
        return state

    _locked_rmw(state_path, mutator)
    return summary


def cmd_select(args: argparse.Namespace) -> None:
    """Mark the top-N papers (by .score) as selected."""
    chosen_ids: list[str] = []

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        ranked = sorted(
            state["papers"].values(),
            key=lambda p: p.get("score", 0.0),
            reverse=True,
        )
        chosen = ranked[: args.top]
        ids = [p["id"] for p in chosen]
        for pid, p in state["papers"].items():
            p["selected"] = pid in ids
        state["selected_ids"] = ids
        chosen_ids.extend(ids)
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"selected": len(chosen_ids), "ids": chosen_ids})


def cmd_saturation(args: argparse.Namespace) -> None:
    """Check whether discovery has saturated, evaluated per source.

    A single source is saturated when ALL of:
      - it has been queried at least `--min-rounds` times (default 2), AND
      - its last round's `new` count is < `--threshold`% of its last round's
        `hits`, AND
      - no paper first seen in that last round (and linked to this source)
        has more than `--max-citations` citations.

    `overall_saturated` is True only when every queried source individually
    satisfies the rule — the gate that P1 #10 from the review targets.

    The old single-source check was broken for multi-source discovery: it
    read only `queries[-1]` and would fire "saturated" after one quiet
    source even when others were still producing new papers.
    """
    state = load_state(Path(args.state))
    if not state["queries"]:
        err("no_queries",
            "No queries recorded yet. Run a search first.",
            retryable=False, exit_code=EXIT_VALIDATION)

    # Group queries by source, preserving insertion order within each bucket.
    by_source: dict[str, list[dict[str, Any]]] = {}
    for q in state["queries"]:
        by_source.setdefault(q["source"], []).append(q)

    if args.source:
        if args.source not in by_source:
            err("source_not_queried",
                f"Source '{args.source}' has no queries in state.",
                retryable=False, exit_code=EXIT_VALIDATION,
                source=args.source,
                available=sorted(by_source.keys()))
        by_source = {args.source: by_source[args.source]}

    per_source: dict[str, dict[str, Any]] = {}
    for source, queries in by_source.items():
        last = queries[-1]
        rounds_run = len(queries)
        hits = last.get("hits", 0) or 0
        new = last.get("new", 0) or 0
        pct_new = (new / hits * 100) if hits else 0.0
        # Max citations among papers linked to this source that were first
        # seen globally in the same round number as this source's last round.
        # This is an approximation — the `round` field in query entries is
        # not strictly per-source — but paired with the `source in p.source`
        # filter it's correct whenever rounds don't alias across sources.
        max_cit = 0
        for p in state["papers"].values():
            if (p.get("first_seen_round") == last["round"]
                    and source in (p.get("source") or [])):
                max_cit = max(max_cit, p.get("citations") or 0)
        saturated = (
            rounds_run >= args.min_rounds
            and pct_new < args.threshold
            and max_cit < args.max_citations
        )
        per_source[source] = {
            "rounds_run": rounds_run,
            "last_round": last["round"],
            "last_query": last.get("query", ""),
            "hits_last_round": hits,
            "new_last_round": new,
            "new_pct": round(pct_new, 1),
            "max_new_citations": max_cit,
            "saturated": saturated,
        }

    overall_saturated = bool(per_source) and all(
        ps["saturated"] for ps in per_source.values()
    )
    ok({
        "per_source": per_source,
        "overall_saturated": overall_saturated,
        "threshold_pct": args.threshold,
        "max_citations_threshold": args.max_citations,
        "min_rounds": args.min_rounds,
    })


def cmd_set(args: argparse.Namespace) -> None:
    """Set a whitelisted top-level state field (phase, archetype, report_path).

    Collection fields (`papers`, `queries`, `themes`, `tensions`,
    `self_critique`) are NOT settable through this command — use the dedicated
    subcommands (`ingest`, `theme`, `tension`, `critique`, etc). This prevents
    an agent from silently wiping the corpus via `set --field papers`.
    """
    if args.field not in SETTABLE_FIELDS:
        err("field_not_settable",
            f"Field '{args.field}' is not settable via `set`. "
            f"Use the dedicated subcommand for collection fields.",
            retryable=False, exit_code=EXIT_VALIDATION,
            field=args.field,
            allowed=sorted(SETTABLE_FIELDS))
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state[args.field] = value
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"field": args.field, "value": value})


def cmd_query(args: argparse.Namespace) -> None:
    """Read a slice of state for inspection.

    All read slices return an enveloped response. List slices carry a `count`
    field so the agent does not need a follow-up call to count items.
    """
    state = load_state(Path(args.state))
    if args.what == "summary":
        ok({
            "question": state["question"],
            "archetype": state["archetype"],
            "phase": state["phase"],
            "papers": len(state["papers"]),
            "selected": len(state["selected_ids"]),
            "queries": len(state["queries"]),
            "themes": len(state["themes"]),
            "tensions": len(state["tensions"]),
            "report_path": state.get("report_path"),
        })
        return
    if args.what == "selected":
        items = [state["papers"][pid] for pid in state["selected_ids"]
                 if pid in state["papers"]]
    elif args.what == "papers":
        items = list(state["papers"].values())
    elif args.what == "queries":
        items = state["queries"]
    elif args.what == "themes":
        items = state["themes"]
    elif args.what == "tensions":
        items = state["tensions"]
    elif args.what == "critique":
        ok(state.get("self_critique",
                     {"findings": [], "resolved": [], "appendix": ""}))
        return
    else:
        err("unknown_query",
            f"Unknown query target: {args.what}",
            retryable=False, exit_code=EXIT_VALIDATION,
            what=args.what)
    ok(items, count=len(items), has_more=False)


def cmd_evidence(args: argparse.Namespace) -> None:
    """Attach evidence (extracted reading) to a paper."""
    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        if args.id not in state["papers"]:
            err("unknown_paper_id",
                f"No paper in state with id '{args.id}'.",
                retryable=False, exit_code=EXIT_VALIDATION,
                id=args.id)
        paper = state["papers"][args.id]
        paper["evidence"] = {
            "method": args.method,
            "findings": args.findings or [],
            "limitations": args.limitations or "",
            "relevance": args.relevance or "",
        }
        paper["depth"] = args.depth
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"id": args.id, "depth": args.depth})


def cmd_theme(args: argparse.Namespace) -> None:
    total = [0]

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["themes"].append({
            "name": args.name,
            "summary": args.summary or "",
            "paper_ids": args.paper_ids or [],
        })
        total[0] = len(state["themes"])
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"theme": args.name, "total_themes": total[0]})


def cmd_tension(args: argparse.Namespace) -> None:
    try:
        sides = json.loads(args.sides)
    except json.JSONDecodeError as e:
        err("invalid_json",
            f"--sides is not valid JSON: {e}",
            retryable=False, exit_code=EXIT_VALIDATION,
            field="sides")
    total = [0]

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["tensions"].append({
            "topic": args.topic,
            "sides": sides,
        })
        total[0] = len(state["tensions"])
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"topic": args.topic, "total_tensions": total[0]})


def cmd_rank(args: argparse.Namespace) -> None:
    """Apply a ranking patch produced by rank_papers.py.

    Patch shape: {"scored_papers": {pid: {score, score_components}}, "meta": {...}}.
    This subcommand is for replay/audit — normal use is via rank_papers.py,
    which calls apply_ranking() directly.
    """
    patch = json.loads(Path(args.patch).read_text())
    summary = apply_ranking(
        Path(args.state),
        patch.get("scored_papers") or {},
        patch.get("meta") or {},
    )
    ok(summary)


def cmd_dedupe(args: argparse.Namespace) -> None:
    """Apply a dedupe patch produced by dedupe_papers.py.

    Patch shape: {"new_papers": {pid: paper}, "id_remap": {old_id: new_id}}.
    """
    patch = json.loads(Path(args.patch).read_text())
    summary = apply_dedupe(
        Path(args.state),
        patch.get("new_papers") or {},
        patch.get("id_remap") or {},
    )
    ok(summary)


def cmd_citation_chase(args: argparse.Namespace) -> None:
    """Apply a citation-chase patch produced by build_citation_graph.py.

    Patch shape: {"new_records": [...], "query_entry": {source, query, ...}}.
    """
    patch = json.loads(Path(args.patch).read_text())
    summary = apply_citation_chase(
        Path(args.state),
        patch.get("new_records") or [],
        patch.get("query_entry") or {},
    )
    ok(summary)


def cmd_critique(args: argparse.Namespace) -> None:
    final_crit: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        crit = state.setdefault("self_critique",
                                {"findings": [], "resolved": [], "appendix": ""})
        if args.finding:
            crit["findings"].append(args.finding)
        if args.resolve:
            crit["resolved"].append(args.resolve)
        if args.appendix:
            crit["appendix"] = args.appendix
        final_crit.update(crit)
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"critique": final_crit})


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research_state.py",
        description="Central state file management for scholar-deep-research.",
    )
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="Path to the state file "
             "(env: SCHOLAR_STATE_PATH, default: research_state.json)",
    )
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
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

    s = sub.add_parser("saturation",
                       help="Check whether discovery saturated (per source)")
    s.add_argument("--threshold", type=float, default=20.0,
                   help="New-paper percentage below which a source is "
                        "considered saturated (default 20)")
    s.add_argument("--max-citations", type=int, default=100,
                   help="If a new paper has more citations than this, the "
                        "source is NOT saturated (default 100)")
    s.add_argument("--min-rounds", type=int, default=2,
                   help="Minimum rounds before a source can be called "
                        "saturated. Prevents declaring saturation on a "
                        "single-query source (default 2).")
    s.add_argument("--source",
                   help="Check a single source only (default: all sources)")
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

    # Replay/audit subcommands: apply a pre-computed patch from a JSON file.
    # Normal usage is via rank_papers.py / dedupe_papers.py / build_citation_graph.py,
    # which call the apply_* functions directly. These exist so a failed
    # mutation can be replayed from the patch file without re-running the
    # (sometimes network-bound) compute step.
    s = sub.add_parser("rank", help="Apply a ranking patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.set_defaults(func=cmd_rank)

    s = sub.add_parser("dedupe", help="Apply a dedupe patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.set_defaults(func=cmd_dedupe)

    s = sub.add_parser("citation-chase", help="Apply a citation-chase patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.set_defaults(func=cmd_citation_chase)

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
    maybe_emit_schema(parser, "research_state", argv)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
