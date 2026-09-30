"""Experimental paragraph extraction and structure assignment for papers.

The implementation uses PDF text blocks as paragraph candidates, then removes
recognizable headings and non-prose material. It is deliberately auditable:
excluded blocks and their reasons are returned beside the paragraph records.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Literal

import pymupdf

from .sections import detect_sections


ParagraphMethod = Literal["blank_lines", "layout_blocks"]
CAPTION_PATTERN = re.compile(r"^\s*(?:fig(?:ure)?|table)\s*\d+(?:\.\d+)?\s*[:.]", re.I)
PAGE_NUMBER_PATTERN = re.compile(r"^\s*(?:\d{1,4}|[ivxlcdm]{1,8})\s*$", re.I)
MATH_OPERATORS = set("=∑∏√≤≥±×÷→←∫")


def _clean(text: str) -> str:
    """Normalize whitespace while retaining visible line-end hyphens."""
    return re.sub(r"\s+", " ", text).strip()


def _repair_line_hyphenation(text: str) -> str:
    """Join words split by a PDF line break, without removing lexical hyphens."""
    return re.sub(r"(?<=[A-Za-z])[-‐]\s+(?=[a-z])", "", text)


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE)


def _edge_fingerprint(text: str) -> str:
    """Normalize text for conservative repeated running-header/footer checks."""
    return re.sub(r"[^\w]+", " ", text.casefold(), flags=re.UNICODE).strip()


def _heading_match(
    text: str, headings: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str]:
    """Match a detected heading at a block's start and return any body tail."""
    raw_tokens = list(re.finditer(r"[\w]+", text, flags=re.UNICODE))
    tokens = [match.group(0).casefold() for match in raw_tokens]
    best: tuple[int, dict[str, Any]] | None = None
    for heading in headings:
        label = " ".join(
            item for item in (heading.get("section_id"), heading.get("title")) if item
        )
        expected = _word_tokens(label)
        if expected and tokens[: len(expected)] == expected:
            if best is None or len(expected) > best[0]:
                best = (len(expected), heading)
        # Unnumbered headings are stored without an ID.
        if not heading.get("section_id"):
            expected = _word_tokens(str(heading.get("title", "")))
            if expected and tokens[: len(expected)] == expected:
                if best is None or len(expected) > best[0]:
                    best = (len(expected), heading)

    if best is None:
        return None, text
    matched_count, heading = best
    if len(raw_tokens) <= matched_count:
        return heading, ""
    tail = text[raw_tokens[matched_count - 1].end() :].lstrip(" .:–—-\t")
    # A heading sharing a block with body text should not cause that prose to
    # disappear. Keep a meaningful tail as a paragraph under the new section.
    if len(_word_tokens(tail)) >= 4 and re.search(r"[A-Za-z]{3,}", tail):
        return heading, tail
    return heading, ""


def _is_table_like(candidate: dict[str, Any]) -> bool:
    """Detect text between repeated horizontal rules in a table region."""
    bbox = candidate.get("bbox")
    page_width = candidate.get("page_width")
    rule_count = int(candidate.get("table_rule_count", 0))
    if not bbox or not page_width:
        return False
    width_ratio = (bbox[2] - bbox[0]) / page_width
    # A repeated horizontal rule is strong, layout-derived evidence. It avoids
    # confusing justified prose with table rows merely because the PDF splits
    # bold/italic words into many spans.
    if width_ratio >= 0.45 and rule_count >= 2:
        return True

    # Borderless tables need a separate classifier. Text-span counts alone
    # also look table-like in justified paragraphs, so retain such uncertain
    # blocks and record this as a limitation instead of dropping prose.
    return False


def _is_numeric_data_block(candidate: dict[str, Any]) -> bool:
    """Find dense numeric displays such as borderless tables or chart axes."""
    text = candidate["text"]
    tokens = re.findall(r"(?<!\w)[−+\-]?\d+(?:[,.]\d+)*(?:\.\d+)?", text)
    all_tokens = _word_tokens(text)
    return (
        candidate.get("line_count", 0) >= 6
        and len(tokens) >= 6
        and len(all_tokens) > 0
        and len(tokens) / len(all_tokens) >= 0.28
    )


def _is_equation_like(text: str) -> bool:
    """Identify short formula-like blocks without discarding prose equations."""
    compact = re.sub(r"\s+", "", text)
    word_count = len(_word_tokens(text))
    operator_count = sum(character in MATH_OPERATORS for character in compact)
    if operator_count == 0:
        return False
    return len(compact) <= 220 and word_count <= 14


def _classify_nonparagraph(
    candidate: dict[str, Any], page_width: float, page_height: float
) -> str | None:
    """Return an exclusion reason for a recognizable non-paragraph block."""
    text = candidate["text"].strip()
    if CAPTION_PATTERN.match(text):
        return "caption"
    bbox = candidate.get("bbox")
    if PAGE_NUMBER_PATTERN.fullmatch(text) and bbox and bbox[3] >= page_height * 0.9:
        return "page_number"
    if _is_table_like(candidate):
        return "table"
    if _is_numeric_data_block(candidate):
        return "numeric_data_block"
    if _is_equation_like(text):
        return "equation"

    words = _word_tokens(text)
    if (
        bbox
        and len(words) <= 2
        and len(text) <= 32
        and (bbox[2] - bbox[0]) < page_width * 0.25
        and not text.endswith((".", "!", "?"))
    ):
        return "short_nonprose_fragment"
    return None


def _reading_order(candidates: list[dict[str, Any]], page_width: float) -> list[dict[str, Any]]:
    """Order blocks by columns when the page has two clearly separated columns."""
    if not candidates:
        return []
    narrow = [
        item for item in candidates
        if item.get("bbox") and item["bbox"][2] - item["bbox"][0] < page_width * 0.62
    ]
    left = [item for item in narrow if (item["bbox"][0] + item["bbox"][2]) / 2 < page_width / 2]
    right = [item for item in narrow if item not in left]
    two_columns = len(left) >= 2 and len(right) >= 2
    if not two_columns:
        return sorted(candidates, key=lambda item: (item["bbox"][1], item["bbox"][0]))

    # Full-width items form visual bands. Within each band, finish the left
    # column before reading the right column, as a reader normally would.
    spanning = [item for item in candidates if item not in narrow]
    left.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    right.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    spanning.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    ordered: list[dict[str, Any]] = []
    emitted: set[int] = set()
    for item in spanning:
        boundary = item["bbox"][1]
        for column in (left, right):
            for block in column:
                if id(block) not in emitted and block["bbox"][1] < boundary:
                    ordered.append(block)
                    emitted.add(id(block))
        ordered.append(item)
        emitted.add(id(item))
    for column in (left, right):
        for block in column:
            if id(block) not in emitted:
                ordered.append(block)
                emitted.add(id(block))
    for item in candidates:
        if id(item) not in emitted:
            ordered.append(item)
    return ordered


def extract_paragraph_candidates(
    pdf_path: str | Path,
    *,
    method: ParagraphMethod,
    pages: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Return page-level candidates from blank-line or text-block boundaries.

    Candidates deliberately include headings, captions, tables, equations,
    and page numbers. Use :func:`extract_document_paragraphs` to classify and
    assemble paragraph records.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    if method not in {"blank_lines", "layout_blocks"}:
        raise ValueError(f"Unsupported paragraph method: {method}")

    candidates: list[dict[str, Any]] = []
    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            if pages is not None and page_number not in pages:
                continue
            page_candidates: list[dict[str, Any]] = []
            if method == "blank_lines":
                for chunk in re.split(r"\n\s*\n+", page.get_text("text", sort=True)):
                    cleaned = _clean(chunk)
                    if cleaned:
                        page_candidates.append(
                            {"text": cleaned, "bbox": None, "source_block": None}
                        )
            else:
                page_dict = page.get_text("dict", sort=True)
                horizontal_rules: list[tuple[float, float, float]] = []
                for drawing in page.get_drawings():
                    for item in drawing.get("items", []):
                        if item[0] != "l":
                            continue
                        start, end = item[1], item[2]
                        if abs(start.y - end.y) <= 1.25 and abs(start.x - end.x) >= 12:
                            horizontal_rules.append(
                                (min(float(start.x), float(end.x)),
                                 max(float(start.x), float(end.x)),
                                 float(start.y))
                            )
                for block_index, block in enumerate(page_dict.get("blocks", [])):
                    if block.get("type") != 0:
                        continue
                    lines: list[str] = []
                    line_span_counts: list[int] = []
                    span_sizes: list[float] = []
                    for line in block.get("lines", []):
                        pieces: list[str] = []
                        previous_end: float | None = None
                        span_count = 0
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if not span_text.strip():
                                continue
                            x0, _, x1, _ = span.get("bbox", (0, 0, 0, 0))
                            if pieces and previous_end is not None and float(x0) - previous_end > 1.5:
                                pieces.append(" ")
                            pieces.append(span_text)
                            previous_end = float(x1)
                            span_count += 1
                            span_sizes.append(float(span.get("size", 0)))
                        line_text = "".join(pieces).strip()
                        if line_text:
                            lines.append(line_text)
                            line_span_counts.append(span_count)
                    cleaned = _clean("\n".join(lines))
                    if cleaned:
                        x0, y0, x1, y1 = (float(value) for value in block["bbox"])
                        block_width = x1 - x0
                        overlapping_rules = 0
                        for rule_x0, rule_x1, rule_y in horizontal_rules:
                            overlap = max(0.0, min(x1, rule_x1) - max(x0, rule_x0))
                            if (
                                y0 - 4 <= rule_y <= y1 + 4
                                and overlap >= min(block_width, rule_x1 - rule_x0) * 0.6
                            ):
                                overlapping_rules += 1
                        page_candidates.append(
                            {
                                "text": cleaned,
                                "bbox": [round(float(value), 2) for value in block["bbox"]],
                                "source_block": block_index,
                                "line_count": len(lines),
                                "line_span_counts": line_span_counts,
                                "font_size_median": round(median(span_sizes), 2) if span_sizes else None,
                                "table_rule_count": overlapping_rules,
                                "page_width": round(float(page.rect.width), 2),
                            }
                        )

            for index, candidate in enumerate(page_candidates, start=1):
                candidates.append(
                    {
                        "paper": path.stem,
                        "page": page_number,
                        "candidate_id": index,
                        "method": method,
                        **candidate,
                    }
                )
    return candidates


def extract_document_paragraphs(pdf_path: str | Path) -> dict[str, Any]:
    """Extract paragraph records with page and detected section metadata.

    Layout blocks are used as the production baseline because they preserved
    the manually reviewed two-column paragraph boundaries. Recognizable
    headings, captions, table blocks, equations, page numbers, and short figure
    labels are returned in ``excluded`` for audit rather than counted as prose.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    sections = detect_sections(path)
    headings_by_page: dict[int, list[dict[str, Any]]] = {}
    for section in sections:
        headings_by_page.setdefault(int(section["page"]), []).append(section)

    candidates = extract_paragraph_candidates(path, method="layout_blocks")
    by_page: dict[int, list[dict[str, Any]]] = {}
    with pymupdf.open(path) as document:
        page_heights = {number: float(page.rect.height) for number, page in enumerate(document, start=1)}
    edge_pages: dict[str, set[int]] = defaultdict(set)
    for candidate in candidates:
        by_page.setdefault(int(candidate["page"]), []).append(candidate)
        bbox = candidate.get("bbox")
        page = int(candidate["page"])
        height = page_heights[page]
        if bbox and (bbox[1] <= height * 0.12 or bbox[3] >= height * 0.88):
            fingerprint = _edge_fingerprint(candidate["text"])
            # Ignore page numbers here; they have their own geometric rule.
            if fingerprint and not PAGE_NUMBER_PATTERN.fullmatch(candidate["text"]):
                edge_pages[fingerprint].add(page)
    repeated_edge_fingerprints = {
        fingerprint for fingerprint, pages_found in edge_pages.items() if len(pages_found) >= 2
    }
    body_font_sizes: dict[int, float] = {}
    for page_number, page_candidates in by_page.items():
        sizes = [
            round(float(candidate["font_size_median"]), 1)
            for candidate in page_candidates
            if candidate.get("font_size_median")
            and candidate.get("bbox")
            and page_heights[page_number] * 0.12 < candidate["bbox"][1]
            and candidate["bbox"][3] < page_heights[page_number] * 0.86
        ]
        if sizes:
            body_font_sizes[page_number] = float(Counter(sizes).most_common(1)[0][0])

    paragraphs: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    with pymupdf.open(path) as document:
        page_count = len(document)
        for page_number, page in enumerate(document, start=1):
            page_candidates = _reading_order(by_page.get(page_number, []), float(page.rect.width))
            page_headings = headings_by_page.get(page_number, [])
            # The first page usually contains a title, author affiliations,
            # email addresses, and publication metadata before the abstract
            # or first numbered section. These are layout blocks, but they
            # are not body paragraphs. Find the first recognized structural
            # heading so the abstract itself remains eligible for extraction.
            first_heading_index: int | None = None
            if page_number == 1:
                for index, item in enumerate(page_candidates):
                    matched_heading, _ = _heading_match(item["text"], page_headings)
                    if matched_heading:
                        first_heading_index = index
                        break
            for candidate_index, candidate in enumerate(page_candidates):
                fingerprint = _edge_fingerprint(candidate["text"])
                bbox = candidate.get("bbox")
                font_size = candidate.get("font_size_median")
                body_font_size = body_font_sizes.get(page_number)
                has_footer_url = bool(re.search(r"https?://", candidate["text"], re.I))
                if (
                    bbox
                    and body_font_size
                    and font_size
                    and bbox[1] >= page_heights[page_number] * 0.86
                    and (
                        float(font_size) <= body_font_size * 0.85
                        or (has_footer_url and float(font_size) <= body_font_size * 0.95)
                    )
                    and len(_word_tokens(candidate["text"])) <= 80
                ):
                    excluded.append(
                        {
                            "page": page_number,
                            "candidate_id": candidate["candidate_id"],
                            "type": "footer_or_footnote",
                            "text": candidate["text"],
                        }
                    )
                    continue
                if fingerprint in repeated_edge_fingerprints:
                    excluded.append(
                        {
                            "page": page_number,
                            "candidate_id": candidate["candidate_id"],
                            "type": "repeated_header_footer_or_title",
                            "text": candidate["text"],
                        }
                    )
                    continue
                if (
                    page_number == 1
                    and first_heading_index is not None
                    and candidate_index < first_heading_index
                ):
                    excluded.append(
                        {
                            "page": page_number,
                            "candidate_id": candidate["candidate_id"],
                            "type": "front_matter",
                            "text": candidate["text"],
                        }
                    )
                    continue
                detected_heading, body_tail = _heading_match(candidate["text"], page_headings)
                if detected_heading:
                    current_section = detected_heading
                    if not body_tail:
                        excluded.append(
                            {
                                "page": page_number,
                                "candidate_id": candidate["candidate_id"],
                                "type": "heading",
                                "text": candidate["text"],
                            }
                        )
                        continue
                    text = body_tail
                else:
                    text = candidate["text"]

                reason = _classify_nonparagraph(
                    candidate, float(page.rect.width), float(page.rect.height)
                )
                if reason:
                    excluded.append(
                        {
                            "page": page_number,
                            "candidate_id": candidate["candidate_id"],
                            "type": reason,
                            "text": candidate["text"],
                        }
                    )
                    continue

                normalized = _repair_line_hyphenation(_clean(text))
                if len(_word_tokens(normalized)) < 2:
                    excluded.append(
                        {
                            "page": page_number,
                            "candidate_id": candidate["candidate_id"],
                            "type": "short_fragment",
                            "text": candidate["text"],
                        }
                    )
                    continue

                section_id = current_section.get("section_id") if current_section else None
                section_title = current_section.get("title") if current_section else None
                previous = paragraphs[-1] if paragraphs else None
                previous_text = previous["text"] if previous else ""
                previous_bbox = previous.get("_bbox") if previous else None
                current_bbox = candidate.get("bbox")
                visually_adjacent = bool(
                    previous_bbox
                    and current_bbox
                    and -2 <= current_bbox[1] - previous_bbox[3] <= 18
                    and "@" not in previous_text
                    and "@" not in normalized
                )
                starts_as_continuation = bool(
                    previous
                    and previous["page"] == page_number
                    and previous["section_id"] == section_id
                    and previous.get("_column") == _column_key(candidate, float(page.rect.width))
                    and visually_adjacent
                    and not re.search(r"[.!?;:]\s*[\"')\]]*$", previous_text)
                    and normalized[:1].islower()
                )
                if starts_as_continuation:
                    if previous_text.endswith(("-", "‐")):
                        previous["text"] = previous_text[:-1] + normalized
                    else:
                        previous["text"] = previous_text + " " + normalized
                    previous["source_candidates"].append(candidate["candidate_id"])
                    previous["_bbox"][3] = current_bbox[3]
                else:
                    paragraphs.append(
                        {
                            "paper": path.stem,
                            "page": page_number,
                            "section_id": section_id,
                            "section": section_title,
                            "paragraph": len(paragraphs) + 1,
                            "text": normalized,
                            "source_candidates": [candidate["candidate_id"]],
                            "_column": _column_key(candidate, float(page.rect.width)),
                            "_bbox": candidate.get("bbox"),
                        }
                    )

    # A title page may not have a machine-detectable Abstract heading. If an
    # Abstract-labelled paragraph is present, discard all preceding page-one
    # blocks (title, authors, affiliations, and publication metadata).
    first_abstract = next(
        (index for index, item in enumerate(paragraphs)
         if item["page"] == 1 and str(item.get("section", "")).casefold() == "abstract"),
        None,
    )
    if first_abstract is not None:
        front_matter = paragraphs[:first_abstract]
        excluded.extend(
            {
                "page": item["page"],
                "candidate_id": item["source_candidates"][0],
                "type": "front_matter_title_or_author_block",
                "text": item["text"],
            }
            for item in front_matter
        )
        paragraphs = paragraphs[first_abstract:]

    # References and acknowledgments are useful for auditing section
    # boundaries, but are not part of the assignment's summary corpus.
    kept_paragraphs: list[dict[str, Any]] = []
    for item in paragraphs:
        section_name = str(item.get("section", "")).casefold()
        if section_name in {"references", "acknowledgments", "acknowledgements"}:
            excluded.append(
                {
                    "page": item["page"],
                    "candidate_id": item["source_candidates"][0],
                    "type": "excluded_section_" + section_name,
                    "text": item["text"],
                }
            )
        else:
            kept_paragraphs.append(item)
    paragraphs = kept_paragraphs

    for paragraph_id, paragraph in enumerate(paragraphs, start=1):
        paragraph["paragraph"] = paragraph_id
        paragraph.pop("_column", None)
        paragraph.pop("_bbox", None)
    excluded_counts = Counter(item["type"] for item in excluded)
    return {
        "paper": path.stem,
        "method": "layout_blocks_with_filters",
        "sections": sections,
        "paragraphs": paragraphs,
        "excluded": excluded,
        "statistics": {
            "pages": page_count,
            "detected_sections": len(sections),
            "paragraphs": len(paragraphs),
            "excluded_candidates": len(excluded),
            "excluded_by_type": dict(sorted(excluded_counts.items())),
        },
    }


def _column_key(candidate: dict[str, Any], page_width: float) -> str:
    """Return a coarse column label used only for safe within-page joining."""
    bbox = candidate.get("bbox")
    if not bbox:
        return "page"
    center = (bbox[0] + bbox[2]) / 2
    if bbox[2] - bbox[0] >= page_width * 0.62:
        return "wide"
    return "left" if center < page_width / 2 else "right"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract experimental paragraph records from scientific PDFs."
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="PDF file paths")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/paragraphs"),
        help="Directory for one JSON result per PDF (default: outputs/paragraphs)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for pdf_path in args.pdfs:
        result = extract_document_paragraphs(pdf_path)
        output_path = args.output_dir / f"{pdf_path.stem}_paragraphs.json"
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        summaries.append({"paper": result["paper"], **result["statistics"], "output": str(output_path)})
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
