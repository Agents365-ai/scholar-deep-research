#!/usr/bin/env python3
"""search_crossref.py — query the Crossref REST API.

Crossref is the authoritative source for DOI-backed metadata. Use it to:
  - Resolve a DOI to canonical metadata
  - Find papers in a specific journal
  - Check what cited a known DOI

Polite pool: pass --email for higher rate limits.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

from _common import USER_AGENT, make_paper, make_payload, emit

API = "https://api.crossref.org/works"


def search(query: str, limit: int, email: str | None,
           year_from: int | None, year_to: int | None) -> list[dict]:
    params: dict[str, Any] = {
        "query": query,
        "rows": min(limit, 1000),
    }
    filters = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if year_to:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)
    if email:
        params["mailto"] = email

    headers = {"User-Agent": USER_AGENT}
    if email:
        headers["From"] = email

    try:
        r = httpx.get(API, params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.stderr.write(f"crossref error: {e}\n")
        return []
    items = r.json().get("message", {}).get("items", [])
    return [_normalize(it) for it in items[:limit]]


def _normalize(it: dict[str, Any]) -> dict[str, Any]:
    title = ""
    if it.get("title"):
        title = it["title"][0] if isinstance(it["title"], list) else it["title"]
    authors = []
    for a in it.get("author", []):
        name = " ".join(filter(None, [a.get("given"), a.get("family")]))
        if name:
            authors.append(name)
    venue = None
    if it.get("container-title"):
        venue = (it["container-title"][0]
                 if isinstance(it["container-title"], list)
                 else it["container-title"])

    year = None
    issued = it.get("issued", {}).get("date-parts")
    if issued and issued[0]:
        year = issued[0][0]
    elif it.get("published-print", {}).get("date-parts"):
        year = it["published-print"]["date-parts"][0][0]

    pdf_url = None
    for link in it.get("link", []):
        if link.get("content-type") == "application/pdf":
            pdf_url = link.get("URL")
            break

    return make_paper(
        doi=it.get("DOI"),
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=it.get("abstract"),
        citations=it.get("is-referenced-by-count", 0),
        url=it.get("URL"),
        pdf_url=pdf_url,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search Crossref.")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--email")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--output")
    p.add_argument("--state")
    args = p.parse_args()

    papers = search(args.query, args.limit, args.email,
                    args.year_from, args.year_to)
    payload = make_payload("crossref", args.query, args.round, papers)
    emit(payload, args.output, args.state)


if __name__ == "__main__":
    main()
