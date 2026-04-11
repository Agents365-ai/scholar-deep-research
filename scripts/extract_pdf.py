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
import json
import sys
import tempfile
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("error: pypdf not installed. Run: pip install pypdf")


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
    args = p.parse_args()

    if args.url:
        import httpx
        try:
            r = httpx.get(args.url, follow_redirects=True, timeout=60.0,
                          headers={"User-Agent": "scholar-deep-research/0.1"})
            r.raise_for_status()
        except httpx.HTTPError as e:
            print(json.dumps({"ok": False, "error": f"download failed: {e}"}))
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(r.content)
        tmp.close()
        pdf_path = Path(tmp.name)
    else:
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            print(json.dumps({"ok": False, "error": f"not found: {pdf_path}"}))
            return

    try:
        reader = PdfReader(str(pdf_path))
        page_indices = parse_pages(args.pages, len(reader.pages))
        text, meta = extract(pdf_path, page_indices)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"pypdf failure: {e}"}))
        return

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        meta["output"] = str(out)
    else:
        meta["text_preview"] = text[:500]

    print(json.dumps({"ok": True, **meta}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
