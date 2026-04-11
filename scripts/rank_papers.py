#!/usr/bin/env python3
"""rank_papers.py — score papers in state with a transparent formula.

Formula:
    score = α·relevance + β·log10(citations+1)/3 + γ·recency_decay + δ·venue_prior

Components (each ∈ [0,1]):
  - relevance: Jaccard-style similarity between the question terms and the
               paper's title+abstract (cheap but transparent; users who want
               semantic similarity should re-rank with an embedding model and
               write the result back into score_components.relevance).
  - citations: log10(c+1)/3, capped at 1.0 (≈1000 cites = full credit).
  - recency_decay: exp(-Δyears / half_life), default half-life = 5 years.
  - venue_prior: 1.0 if venue matches a tier-1 list, 0.5 otherwise.

The formula and per-paper components are written into state so the report can
cite its own ranking methodology in the appendix.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from research_state import load_state, save_state

# Tier-1 venues. Conservative; users should extend per field.
TIER1_VENUES = {
    # General science
    "nature", "science", "cell", "pnas", "nature communications",
    "science advances", "nature methods", "nature biotechnology",
    "nature medicine", "nature genetics", "nature reviews",
    # ML / AI
    "neurips", "icml", "iclr", "cvpr", "iccv", "eccv", "acl",
    "emnlp", "naacl", "aaai", "ijcai", "kdd", "siggraph",
    # CS systems
    "sosp", "osdi", "sigcomm", "stoc", "focs",
    # Bio
    "elife", "plos biology", "current biology", "molecular cell",
    "immunity", "neuron",
}


def tokenize(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def relevance(question: str, paper: dict[str, Any]) -> float:
    qtok = tokenize(question)
    if not qtok:
        return 0.0
    haystack = " ".join([
        paper.get("title") or "",
        paper.get("abstract") or "",
    ])
    htok = tokenize(haystack)
    if not htok:
        return 0.0
    overlap = qtok & htok
    return len(overlap) / max(len(qtok), 1)


def cite_score(citations: int | None) -> float:
    c = citations or 0
    return min(math.log10(c + 1) / 3.0, 1.0)


def recency(year: int | None, half_life: float, now_year: int) -> float:
    if not year:
        return 0.0
    delta = max(0, now_year - year)
    return math.exp(-delta / half_life)


def venue_prior(venue: str | None) -> float:
    if not venue:
        return 0.5
    v = venue.lower()
    for t in TIER1_VENUES:
        if t in v:
            return 1.0
    return 0.5


def main() -> None:
    p = argparse.ArgumentParser(description="Rank papers in state.")
    p.add_argument("--state", default="research_state.json")
    p.add_argument("--question",
                   help="Override the question used for relevance "
                        "(default: state.question)")
    p.add_argument("--alpha", type=float, default=0.4, help="weight: relevance")
    p.add_argument("--beta", type=float, default=0.3, help="weight: citations")
    p.add_argument("--gamma", type=float, default=0.2, help="weight: recency")
    p.add_argument("--delta", type=float, default=0.1, help="weight: venue prior")
    p.add_argument("--half-life", type=float, default=5.0,
                   help="Years until recency weight halves (default 5)")
    p.add_argument("--top", type=int, default=20,
                   help="Print top-N to stdout for inspection")
    args = p.parse_args()

    path = Path(args.state)
    state = load_state(path)
    question = args.question or state["question"]
    now = datetime.now().year

    formula = (
        f"score = {args.alpha}·relevance "
        f"+ {args.beta}·log10(citations+1)/3 "
        f"+ {args.gamma}·exp(-Δyears/{args.half_life}) "
        f"+ {args.delta}·venue_prior"
    )

    for pid, paper in state["papers"].items():
        rel = relevance(question, paper)
        cit = cite_score(paper.get("citations"))
        rec = recency(paper.get("year"), args.half_life, now)
        ven = venue_prior(paper.get("venue"))
        score = (args.alpha * rel
                 + args.beta * cit
                 + args.gamma * rec
                 + args.delta * ven)
        paper["score"] = round(score, 4)
        paper["score_components"] = {
            "relevance": round(rel, 4),
            "citations": round(cit, 4),
            "recency": round(rec, 4),
            "venue": round(ven, 4),
        }

    state["ranking"] = {
        "formula": formula,
        "weights": {
            "alpha": args.alpha, "beta": args.beta,
            "gamma": args.gamma, "delta": args.delta,
        },
        "half_life": args.half_life,
        "ranked_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_state(path, state)

    ranked = sorted(state["papers"].values(),
                    key=lambda x: x.get("score", 0), reverse=True)
    top = ranked[: args.top]
    print(json.dumps({
        "formula": formula,
        "ranked": len(state["papers"]),
        "top": [
            {
                "id": p["id"],
                "title": p.get("title"),
                "year": p.get("year"),
                "venue": p.get("venue"),
                "citations": p.get("citations"),
                "score": p.get("score"),
                "components": p.get("score_components"),
            }
            for p in top
        ],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
