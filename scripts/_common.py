"""Shared helpers for search scripts.

Each search script normalizes its source into the common paper schema, then
either writes the result to a file (--output) or hands it directly to
research_state.py (--state). When --state is given the script invokes the
state module's ingest command in-process.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

USER_AGENT = (
    "scholar-deep-research/0.1 "
    "(+https://github.com/Agents365-ai/scholar-deep-research; "
    "polite-pool)"
)

# Fields that every normalized paper should have (None if unknown).
PAPER_FIELDS = (
    "doi", "title", "authors", "year", "venue", "abstract",
    "citations", "url", "pdf_url",
    "openalex_id", "arxiv_id", "pmid",
)


def make_paper(**kwargs: Any) -> dict[str, Any]:
    """Build a paper dict with all standard fields, missing → None."""
    p: dict[str, Any] = {f: None for f in PAPER_FIELDS}
    p.update({k: v for k, v in kwargs.items() if v is not None})
    # type discipline
    if p.get("authors") and not isinstance(p["authors"], list):
        p["authors"] = [p["authors"]]
    if p.get("year"):
        try:
            p["year"] = int(p["year"])
        except (TypeError, ValueError):
            p["year"] = None
    if p.get("citations") is not None:
        try:
            p["citations"] = int(p["citations"])
        except (TypeError, ValueError):
            p["citations"] = 0
    return p


def make_payload(source: str, query: str, round_: int,
                 papers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": source,
        "query": query,
        "round": round_,
        "papers": papers,
    }


def emit(payload: dict[str, Any], output: str | None,
         state: str | None) -> None:
    """Write payload to --output JSON, and/or hand to research_state.py ingest.

    If neither is given, print the payload to stdout.
    """
    if not output and not state:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    tmp = None
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        tmp = out_path
    if state:
        # If we don't already have a file, write to a temp path.
        if tmp is None:
            tmp = Path(".search_payload.tmp.json")
            tmp.write_text(json.dumps(payload, ensure_ascii=False))
        here = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, str(here / "research_state.py"),
             "--state", state, "ingest", "--input", str(tmp)],
            capture_output=True, text=True,
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)
        if tmp == Path(".search_payload.tmp.json"):
            try:
                tmp.unlink()
            except OSError:
                pass


def reconstruct_inverted_abstract(idx: dict[str, list[int]] | None) -> str | None:
    """OpenAlex returns abstracts as inverted indexes; reconstruct flat text."""
    if not idx:
        return None
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None
