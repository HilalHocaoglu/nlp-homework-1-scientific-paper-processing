"""PDF text extraction baseline for Homework 2.

This module deliberately keeps the extraction step small and inspectable. It
does not try to infer sections or repair equations; those are later pipeline
steps and known sources of extraction error.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pymupdf


WORD_PATTERN = re.compile(r"(?u)\b[\w]+(?:[’'-][\w]+)*\b")


def extract_pdf(pdf_path: str | Path, *, sort_blocks: bool = True) -> list[dict[str, Any]]:
    """Extract text page by page, retaining page numbers and line breaks.

    ``sort_blocks=True`` asks PyMuPDF to sort text blocks by their position on
    the page. This is a useful baseline for reading order, but can still mix
    columns or disrupt complex layouts; the experiment log will track examples.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages: list[dict[str, Any]] = []
    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            pages.append(
                {
                    "page": page_number,
                    "text": page.get_text("text", sort=sort_blocks).strip(),
                }
            )
    return pages


def document_statistics(pages: list[dict[str, Any]]) -> dict[str, int]:
    """Return basic extraction counts for the Homework 2 input PDF."""
    text = "\n".join(page["text"] for page in pages)
    return {
        "pages": len(pages),
        "characters": len(text),
        "words": len(WORD_PATTERN.findall(text)),
    }


def save_extracted_text(pages: list[dict[str, Any]], output_path: str | Path) -> None:
    """Save extracted text with explicit page markers for later inspection."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    page_chunks = [f"===== PAGE {page['page']} =====\n{page['text']}" for page in pages]
    path.write_text("\n\n".join(page_chunks) + "\n", encoding="utf-8")


def process_pdf(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    sort_blocks: bool = True,
) -> dict[str, Any]:
    """Extract one PDF, save its text, and return its basic statistics."""
    source = Path(pdf_path)
    pages = extract_pdf(source, sort_blocks=sort_blocks)
    output_path = Path(output_dir) / f"{source.stem}.txt"
    save_extracted_text(pages, output_path)
    return {
        "paper": source.stem,
        "source": str(source),
        "text_file": str(output_path),
        **document_statistics(pages),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from scientific paper PDFs.")
    parser.add_argument("pdfs", nargs="+", type=Path, help="PDF file paths")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/extracted_text"))
    parser.add_argument(
        "--preserve-pdf-order",
        action="store_true",
        help="Keep PyMuPDF's default text order instead of sorting blocks by page position.",
    )
    args = parser.parse_args()

    results = [
        process_pdf(pdf_path, args.output_dir, sort_blocks=not args.preserve_pdf_order)
        for pdf_path in args.pdfs
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
