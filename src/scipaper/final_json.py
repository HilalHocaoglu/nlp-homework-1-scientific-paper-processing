"""Build Homework 2-ready nested JSON documents from Task 5 outputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .document_stats import calculate_document_statistics


def build_final_document(document: dict[str, Any]) -> dict[str, Any]:
    """Nest paragraph and sentence annotations below their section heading."""
    sections: list[dict[str, Any]] = []
    section_positions: dict[tuple[str | None, str], int] = {}

    for paragraph in document.get("paragraphs", []):
        section_id = paragraph.get("section_id")
        section_title = str(paragraph.get("section") or "Unassigned")
        section_key = (section_id, section_title)
        if section_key not in section_positions:
            section_positions[section_key] = len(sections)
            sections.append(
                {
                    "section_id": section_id,
                    "title": (
                        f"{section_id} {section_title}"
                        if section_id
                        else section_title
                    ),
                    "paragraphs": [],
                }
            )

        final_paragraph = {
            "paragraph_id": paragraph.get("paragraph"),
            "page": paragraph.get("page"),
            "text": paragraph.get("text", ""),
            "sentences": [],
        }
        for sentence in paragraph.get("sentences", []):
            final_paragraph["sentences"].append(
                {
                    "sentence_id": sentence.get("sentence_id"),
                    "text": sentence.get("text", ""),
                    "tokens": [
                        {
                            "text": token.get("text", ""),
                            "token_index": token.get("token_index"),
                            "whitespace_after": token.get("whitespace_after", ""),
                            "lemma": token.get("lemma", ""),
                            "pos": token.get("pos", ""),
                            "dependency": token.get("dependency", ""),
                            "head": token.get("head", ""),
                            "head_index": token.get("head_index"),
                        }
                        for token in sentence.get("tokens", [])
                    ],
                }
            )

        sections[section_positions[section_key]]["paragraphs"].append(final_paragraph)

    stats = calculate_document_statistics(document)
    stats["sections_with_paragraphs"] = len(sections)
    return {
        "schema_version": "1.0",
        "paper": document["paper"],
        "model": document.get("model", {}),
        "processing": {
            "method": document.get("method"),
            "tokenizer_notes": document.get("tokenizer_notes", {}),
            "section_note": (
                "Sections are groups formed from Task 3 paragraph assignments. "
                "Detected section candidates with no assigned paragraph are not emitted."
            ),
        },
        "statistics": stats,
        "sections": sections,
    }


def _output_name(paper_id: str) -> str:
    """Return a safe, stable JSON filename from the paper ID."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id).strip("._-")
    if not stem:
        raise ValueError(f"Cannot form an output filename from paper ID {paper_id!r}")
    return f"{stem}.json"


def process_files(inputs: list[Path], output_dir: Path) -> list[dict[str, Any]]:
    """Build one structured JSON file per paper and return concise summaries."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    used_names: set[str] = set()

    for input_path in sorted(inputs):
        source = json.loads(input_path.read_text(encoding="utf-8"))
        final_document = build_final_document(source)
        output_name = _output_name(final_document["paper"])
        if output_name in used_names:
            raise ValueError(f"Duplicate paper ID would overwrite output {output_name}")
        used_names.add(output_name)

        output_path = output_dir / output_name
        output_path.write_text(
            json.dumps(final_document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summaries.append(
            {
                "paper": final_document["paper"],
                "sections_with_paragraphs": len(final_document["sections"]),
                "paragraphs": final_document["statistics"]["paragraphs"],
                "sentences": final_document["statistics"]["sentences"],
                "tokens": final_document["statistics"]["tokens_including_punctuation"],
                "output": str(output_path),
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one nested Homework 2 JSON representation per paper."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Task 5 annotated token JSON files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/json"),
        help="Directory for final per-paper JSON files",
    )
    args = parser.parse_args()
    print(json.dumps(process_files(args.inputs, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
