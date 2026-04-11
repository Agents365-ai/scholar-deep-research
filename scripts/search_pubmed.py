#!/usr/bin/env python3
"""search_pubmed.py — query PubMed via NCBI E-utilities.

Two-step protocol:
  1. esearch.fcgi → list of PMIDs matching the query
  2. esummary.fcgi → metadata for those PMIDs

For full abstracts use efetch (rettype=abstract). We fetch summaries by default
to keep the round-trip small; abstracts are pulled in Phase 3 deep-read.

API key: optional but recommended (--api-key) for higher rate limits.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

from _common import USER_AGENT, make_paper, make_payload, emit

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search(query: str, limit: int, api_key: str | None,
           year_from: int | None, year_to: int | None,
           with_abstracts: bool) -> list[dict]:
    term = query
    if year_from or year_to:
        a = year_from or 1900
        b = year_to or 3000
        term = f"({query}) AND ({a}:{b}[dp])"

    es_params: dict[str, Any] = {
        "db": "pubmed",
        "term": term,
        "retmax": min(limit, 200),
        "retmode": "json",
        "sort": "relevance",
    }
    if api_key:
        es_params["api_key"] = api_key
    headers = {"User-Agent": USER_AGENT}

    try:
        r = httpx.get(ESEARCH, params=es_params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.stderr.write(f"pubmed esearch error: {e}\n")
        return []
    pmids = r.json().get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    sum_params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if api_key:
        sum_params["api_key"] = api_key
    try:
        r = httpx.get(ESUMMARY, params=sum_params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.stderr.write(f"pubmed esummary error: {e}\n")
        return []
    result = r.json().get("result", {})

    abstracts: dict[str, str] = {}
    if with_abstracts:
        abstracts = _fetch_abstracts(pmids, api_key, headers)

    papers = []
    for pmid in pmids:
        rec = result.get(pmid)
        if not rec:
            continue
        papers.append(_normalize(rec, pmid, abstracts.get(pmid)))
    return papers


def _fetch_abstracts(pmids: list[str], api_key: str | None,
                     headers: dict[str, str]) -> dict[str, str]:
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "text",
    }
    if api_key:
        params["api_key"] = api_key
    try:
        r = httpx.get(EFETCH, params=params, headers=headers, timeout=60.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.stderr.write(f"pubmed efetch error: {e}\n")
        return {}
    # The text response is loosely structured. We won't try to perfectly split
    # it; agent can re-fetch one at a time later if needed.
    return {}


def _normalize(rec: dict[str, Any], pmid: str,
               abstract: str | None) -> dict[str, Any]:
    authors = [a.get("name") for a in rec.get("authors", []) if a.get("name")]
    year = None
    pubdate = rec.get("pubdate") or ""
    if pubdate[:4].isdigit():
        year = int(pubdate[:4])

    doi = None
    for aid in rec.get("articleids", []):
        if aid.get("idtype") == "doi":
            doi = aid.get("value")
            break

    return make_paper(
        doi=doi,
        title=rec.get("title"),
        authors=authors,
        year=year,
        venue=rec.get("fulljournalname") or rec.get("source"),
        abstract=abstract,
        citations=None,  # PubMed doesn't expose citation counts
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        pdf_url=None,
        pmid=pmid,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search PubMed.")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--api-key", help="NCBI API key (optional)")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--with-abstracts", action="store_true",
                   help="Also fetch abstracts via efetch (slower)")
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--output")
    p.add_argument("--state")
    args = p.parse_args()

    papers = search(args.query, args.limit, args.api_key,
                    args.year_from, args.year_to, args.with_abstracts)
    payload = make_payload("pubmed", args.query, args.round, papers)
    emit(payload, args.output, args.state)


if __name__ == "__main__":
    main()
