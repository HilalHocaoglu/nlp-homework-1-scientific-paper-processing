"""Experimental section-heading detection for scientific-paper PDFs.

The detector combines section-number patterns, typography, and a compact
small-caps fallback. It keeps page and horizontal-position information so
headings can be reviewed in context. It is a candidate generator, not a
universal PDF parser.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf


NUMBERED_HEADING = re.compile(
    r"^\s*(?P<section_id>(?:[A-Z]\.\d+(?:\.\d+)*|\d+(?:\.\d+)*))"
    r"(?:\.)?\s+(?P<title>.+?)\s*$"
)
LETTERED_HEADING = re.compile(r"^\s*(?P<section_id>[A-Z])\s+(?P<title>.+?)\s*$")
UNNUMBERED_HEADINGS = {
    "abstract",
    "acknowledgements",
    "acknowledgments",
    "appendix",
    "references",
}
MAX_HEADING_LENGTH = 140


def _is_emphasized(span: dict[str, Any]) -> bool:
    """Check the font name and PyMuPDF's bold flag for heading emphasis."""
    font = str(span.get("font", "")).casefold()
    flags = int(span.get("flags", 0))
    return bool(flags & 16) or "bold" in font or "medi" in font


def _body_font_size(blocks: list[dict[str, Any]]) -> float | None:
    """Estimate the page's body size from the most frequent regular font size."""
    sizes: list[float] = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = float(span.get("size", 0))
                if 7.5 <= size <= 14 and not _is_emphasized(span):
                    sizes.append(round(size, 1))
    if not sizes:
        return None
    return float(Counter(sizes).most_common(1)[0][0])


def _normalize_title(text: str) -> str:
    """Join line-wrapped words without changing possible appendix labels."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[A-Za-z])[-‐]\s+(?=[a-z])", "", text)
    return text.strip()


def _normalize_heading_title(text: str) -> str:
    """Repair a letter-spaced initial found in some conference templates."""
    text = _normalize_title(text)
    # Some PDFs extract a spaced initial, e.g. ``I NTRODUCTION``.
    text = re.sub(r"\b([A-Z])\s+([A-Z]{2,})\b", r"\1\2", text)
    return text.strip()


def _block_text(block: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    spans = [
        span
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    ]
    lines = []
    for line in block.get("lines", []):
        line_spans = [span for span in line.get("spans", []) if span.get("text", "")]
        pieces: list[str] = []
        previous_end: float | None = None
        for span in line_spans:
            x0, _, x1, _ = span.get("bbox", (0, 0, 0, 0))
            if pieces and previous_end is not None and float(x0) - previous_end > 1.5:
                pieces.append(" ")
            pieces.append(span.get("text", ""))
            previous_end = float(x1)
        lines.append("".join(pieces).strip())
    text = _normalize_title(" ".join(line for line in lines if line))
    return text, spans


def _leading_heading_text(
    block: dict[str, Any], body_size: float | None
) -> tuple[str, list[dict[str, Any]], int]:
    """Drop regular body lines that share a PDF block with a bold heading."""
    lines = block.get("lines", [])
    styled_lines: list[dict[str, Any]] = []
    for line in lines:
        spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
        if spans and _has_heading_style(spans, body_size):
            styled_lines.append(line)
        elif styled_lines:
            break

    if not styled_lines:
        text, spans = _block_text(block)
        return text, spans, len(lines)

    selected_spans = [span for line in styled_lines for span in line.get("spans", [])]
    selected_block = {"lines": styled_lines}
    text, _ = _block_text(selected_block)
    return text, selected_spans, len(styled_lines)


def _has_heading_style(spans: list[dict[str, Any]], body_size: float | None) -> bool:
    if not spans:
        return False
    emphasized = sum(_is_emphasized(span) for span in spans) / len(spans)
    largest = max(float(span.get("size", 0)) for span in spans)
    larger_than_body = body_size is not None and largest >= body_size + 0.8
    return emphasized >= 0.6 or larger_than_body


def _looks_like_title(text: str) -> bool:
    if not text or len(text) > MAX_HEADING_LENGTH:
        return False
    if not text[0].isalnum() or text[-1:] in ".!?,;=" or "@" in text:
        return False
    if "http://" in text or "https://" in text:
        return False
    if not re.search(r"[A-Za-z]", text):
        return False
    if sum(character.isalpha() for character in text) < 4 and len(text.split()) < 2:
        return False
    return True


def _is_compact_small_caps_heading(
    text: str, spans: list[dict[str, Any]], line_count: int
) -> bool:
    """Recognize small-caps headings that have no font metadata distinction.

    Some conference PDFs encode small caps as regular-font uppercase text at
    body size. Requiring a short, standalone, strongly uppercase title avoids
    treating numbered prose and footnotes as headings.
    """
    if line_count > 2 or len(text) > 120 or not spans:
        return False
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters)
    return uppercase_ratio >= 0.75


def detect_sections(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Detect numbered or lettered headings and common unnumbered headings.

    Numbered candidates need bold/medium styling, a larger font, or a compact
    small-caps shape. Single-letter appendix headings need typography cues.
    Unnumbered candidates are limited to common structural labels and use the
    typography check. Each result includes its one-based PDF page number.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    sections: list[dict[str, Any]] = []
    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])
            body_size = _body_font_size(blocks)
            page_candidates: list[dict[str, Any]] = []

            for block in blocks:
                if block.get("type") != 0:
                    continue
                text, spans, heading_line_count = _leading_heading_text(block, body_size)
                match = NUMBERED_HEADING.match(text)
                letter_match = LETTERED_HEADING.match(text)
                has_style = _has_heading_style(spans, body_size)
                has_small_caps_shape = match is not None and _is_compact_small_caps_heading(
                    match.group("title"), spans, heading_line_count
                )
                if not has_style and not has_small_caps_shape:
                    continue

                if match:
                    section_id = match.group("section_id")
                    title = _normalize_heading_title(match.group("title"))
                elif letter_match and has_style:
                    section_id = letter_match.group("section_id")
                    title = _normalize_heading_title(letter_match.group("title"))
                elif text.casefold() in UNNUMBERED_HEADINGS:
                    section_id = None
                    title = _normalize_heading_title(text)
                else:
                    continue

                if not _looks_like_title(title):
                    continue

                x0, y0, *_ = block.get("bbox", (0, 0, 0, 0))
                page_candidates.append(
                    {
                        "section_id": section_id,
                        "title": title,
                        "page": page_number,
                        "_x": float(x0),
                        "_y": float(y0),
                        "_page_width": float(page.rect.width),
                    }
                )

            # Scientific papers commonly use two columns. Visit the left
            # column top-to-bottom before the right column on each page.
            page_candidates.sort(
                key=lambda item: (
                    0 if item["_x"] < item["_page_width"] / 2 else 1,
                    item["_y"],
                    item["_x"],
                )
            )
            for candidate in page_candidates:
                sections.append(
                    {
                        "section_id": candidate["section_id"],
                        "title": candidate["title"],
                        "page": candidate["page"],
                    }
                )

    return sections


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect section headings in scientific-paper PDFs."
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="PDF file paths")
    args = parser.parse_args()

    results = [
        {"paper": path.stem, "sections": detect_sections(path)} for path in args.pdfs
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
