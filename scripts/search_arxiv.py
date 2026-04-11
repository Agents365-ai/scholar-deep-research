#!/usr/bin/env python3
"""search_arxiv.py — query the arXiv API.

arXiv is essential for CS/ML/physics preprints and the latest unpublished work.
Returns Atom XML; we parse with stdlib xml.etree.

NOTE: Papers from arXiv are preprints unless cross-listed with a peer-reviewed
venue. The state file tags them with source="arxiv" — downstream consumers
should treat that as a flag to weight evidence accordingly.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

import httpx

from _common import USER_AGENT, make_paper, make_payload, emit

API = "http://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def search(query: str, limit: int) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(limit, 200),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        r = httpx.get(API, params=params,
                      headers={"User-Agent": USER_AGENT}, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.stderr.write(f"arxiv error: {e}\n")
        return []

    root = ET.fromstring(r.text)
    papers = []
    for entry in root.findall("atom:entry", NS):
        papers.append(_normalize(entry))
    return papers


def _normalize(entry: ET.Element) -> dict:
    def text(path: str) -> str | None:
        el = entry.find(path, NS)
        return el.text.strip() if el is not None and el.text else None

    arxiv_url = text("atom:id") or ""
    arxiv_id = arxiv_url.rsplit("/", 1)[-1].split("v")[0] if arxiv_url else None
    title = text("atom:title") or ""
    title = " ".join(title.split())  # collapse newlines
    summary = text("atom:summary") or ""
    summary = " ".join(summary.split())
    published = text("atom:published") or ""
    year = int(published[:4]) if len(published) >= 4 else None

    authors = [
        a.findtext("atom:name", default="", namespaces=NS).strip()
        for a in entry.findall("atom:author", NS)
    ]
    authors = [a for a in authors if a]

    doi = text("arxiv:doi")
    pdf_url = None
    landing = None
    for link in entry.findall("atom:link", NS):
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href")
        elif link.get("rel") == "alternate":
            landing = link.get("href")

    venue = text("arxiv:journal_ref") or "arXiv"

    return make_paper(
        doi=doi,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=summary,
        citations=None,  # arXiv doesn't expose citation counts
        url=landing or arxiv_url,
        pdf_url=pdf_url,
        arxiv_id=arxiv_id,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search arXiv.")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--output")
    p.add_argument("--state")
    args = p.parse_args()

    papers = search(args.query, args.limit)
    payload = make_payload("arxiv", args.query, args.round, papers)
    emit(payload, args.output, args.state)


if __name__ == "__main__":
    main()
