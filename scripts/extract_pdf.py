#!/usr/bin/env python3
"""extract_pdf.py — extract text from a PDF using pypdf.

Usage:
  python scripts/extract_pdf.py --input paper.pdf --output paper.txt
  python scripts/extract_pdf.py --url https://arxiv.org/pdf/2301.12345 --output paper.txt
  python scripts/extract_pdf.py --input paper.pdf --pages 1-5

Limitations (printed as warnings, not errors):
  - Scanned (image-only) PDFs return empty or junk text. Use OCR separately.
  - Multi-column layouts may interleave columns; this is a known pypdf limit.
  - Math/figures are dropped.

The script never crashes the pipeline — it always exits 0 with a JSON status.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from _common import (
    EXIT_RUNTIME, EXIT_UPSTREAM, EXIT_VALIDATION, err, maybe_emit_schema, ok,
)

try:
    from pypdf import PdfReader
except ImportError:
    err("missing_dependency",
        "pypdf not installed. Run: pip install pypdf",
        retryable=False, exit_code=EXIT_RUNTIME,
        dependency="pypdf")


def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    pages: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            pages.update(range(int(a) - 1, int(b)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total)


def extract(pdf_path: Path, pages: list[int]) -> tuple[str, dict]:
    reader = PdfReader(str(pdf_path))
    parts = []
    warnings = []
    for i in pages:
        try:
            t = reader.pages[i].extract_text() or ""
        except Exception as e:
            warnings.append(f"page {i+1}: {e}")
            t = ""
        parts.append(t)
    text = "\n\n".join(parts)
    char_count = len(text.strip())
    is_scanned = char_count < 200 * len(pages)
    meta = {
        "pages_extracted": len(pages),
        "total_pages": len(reader.pages),
        "char_count": char_count,
        "looks_scanned": is_scanned,
        "warnings": warnings,
    }
    return text, meta


def main() -> None:
    p = argparse.ArgumentParser(description="Extract text from PDF.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Local PDF path")
    src.add_argument("--url", help="URL to download then extract")
    p.add_argument("--output", help="Write extracted text to this path")
    p.add_argument("--pages", help="Page range, e.g. 1-5,8,10-12")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "extract_pdf")
    args = p.parse_args()

    if args.url:
        import httpx
        try:
            r = httpx.get(args.url, follow_redirects=True, timeout=60.0,
                          headers={"User-Agent": "scholar-deep-research/0.1"})
            r.raise_for_status()
        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            err("download_failed",
                f"Failed to download {args.url}: {type(e).__name__}: {e}",
                retryable=True, exit_code=EXIT_UPSTREAM,
                url=args.url, status=status)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(r.content)
        tmp.close()
        pdf_path = Path(tmp.name)
    else:
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            err("file_not_found",
                f"PDF not found: {pdf_path}",
                retryable=False, exit_code=EXIT_VALIDATION,
                path=str(pdf_path))

    try:
        reader = PdfReader(str(pdf_path))
        page_indices = parse_pages(args.pages, len(reader.pages))
        text, meta = extract(pdf_path, page_indices)
    except Exception as e:
        err("pypdf_failure",
            f"pypdf failed to read {pdf_path}: {type(e).__name__}: {e}",
            retryable=False, exit_code=EXIT_RUNTIME,
            path=str(pdf_path))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        meta["output"] = str(out)
    else:
        meta["text_preview"] = text[:500]

    ok(meta)


if __name__ == "__main__":
    main()
