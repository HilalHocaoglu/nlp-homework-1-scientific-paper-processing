"""spaCy sentence segmentation for the cleaned Homework 1 paragraphs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import spacy
from spacy.language import Language


# spaCy's parser can treat the period in a scientific label/citation as a
# sentence boundary when the following parenthetical is on the same line.
# Repair only this narrow, observed pattern; do not rewrite arbitrary spans.
ABBREVIATION_BEFORE_PARENTHESIS = re.compile(
    r"(?:et\s+al|Eq|Sec|Fig|Figs|Table|No)\.$", re.IGNORECASE
)


def _join_known_false_splits(sentence_texts: list[str]) -> tuple[list[str], int]:
    """Join parser splits after a known abbreviation before a parenthetical."""
    joined: list[str] = []
    repairs = 0
    for text in sentence_texts:
        cleaned = text.strip()
        if (
            joined
            and ABBREVIATION_BEFORE_PARENTHESIS.search(joined[-1])
            and cleaned.startswith("(")
        ):
            joined[-1] = f"{joined[-1]} {cleaned}"
            repairs += 1
        else:
            joined.append(cleaned)
    return joined, repairs


def segment_paragraphs(
    paragraph_document: dict[str, Any], nlp: Language
) -> dict[str, Any]:
    """Add spaCy sentence records to each cleaned paragraph."""
    paragraphs = paragraph_document.get("paragraphs", [])
    texts = [str(paragraph.get("text", "")) for paragraph in paragraphs]
    segmented: list[dict[str, Any]] = []
    repair_count = 0
    sentence_count = 0

    for paragraph, doc in zip(paragraphs, nlp.pipe(texts, batch_size=128), strict=True):
        sentence_texts = [sentence.text.strip() for sentence in doc.sents if sentence.text.strip()]
        sentence_texts, repairs = _join_known_false_splits(sentence_texts)
        repair_count += repairs
        sentence_records = [
            {"sentence_id": index, "text": text}
            for index, text in enumerate(sentence_texts, start=1)
        ]
        sentence_count += len(sentence_records)
        segmented.append({**paragraph, "sentences": sentence_records})

    output = {
        "paper": paragraph_document["paper"],
        "method": "spacy_parser_with_conservative_abbreviation_repair",
        "model": {"name": nlp.meta["name"], "version": nlp.meta["version"]},
        "paragraphs": segmented,
        "statistics": {
            "pages": paragraph_document["statistics"]["pages"],
            "sections": paragraph_document["statistics"]["detected_sections"],
            "paragraphs": len(segmented),
            "sentences": sentence_count,
            "abbreviation_boundary_repairs": repair_count,
        },
    }
    return output


def process_file(path: Path, nlp: Language, output_dir: Path) -> dict[str, Any]:
    """Read one cleaned paragraph JSON file, segment it, and save it."""
    document = json.loads(path.read_text(encoding="utf-8"))
    result = segment_paragraphs(document, nlp)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / path.name.replace("_paragraphs.json", "_sentences.json")
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"paper": result["paper"], **result["statistics"], "output": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Segment cleaned Homework 1 paragraph JSON files into spaCy sentences."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Cleaned paragraph JSON files")
    parser.add_argument(
        "--model", default="en_core_web_sm", help="Installed spaCy model (default: en_core_web_sm)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/sentences"),
        help="Directory for sentence JSON files",
    )
    args = parser.parse_args()

    try:
        nlp = spacy.load(args.model)
    except OSError as error:
        raise SystemExit(
            f"spaCy model {args.model!r} is not installed. Run: "
            f"python -m spacy download {args.model}"
        ) from error

    summaries = [process_file(path, nlp, args.output_dir) for path in args.inputs]
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
