"""Calculate cross-paper document statistics from Task 5 token JSON files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "paper",
    "pages",
    "sections_detected",
    "paragraphs",
    "sentences",
    "tokens_including_punctuation",
    "lexical_tokens_excluding_punctuation",
    "unique_tokens_casefolded_excluding_punctuation",
    "average_sentence_length_lexical_tokens",
    "average_paragraph_length_lexical_tokens",
]


def calculate_document_statistics(document: dict[str, Any]) -> dict[str, Any]:
    """Summarize one nested Task 5 paper document with explicit definitions."""
    paragraphs = document.get("paragraphs", [])
    sentences = [
        sentence
        for paragraph in paragraphs
        for sentence in paragraph.get("sentences", [])
    ]
    tokens = [
        token
        for sentence in sentences
        for token in sentence.get("tokens", [])
    ]
    lexical_tokens = [token for token in tokens if token.get("pos") != "PUNCT"]
    unique_lexical_tokens = {
        str(token.get("text", "")).casefold()
        for token in lexical_tokens
        if str(token.get("text", ""))
    }

    paragraph_lengths = [
        sum(
            1
            for sentence in paragraph.get("sentences", [])
            for token in sentence.get("tokens", [])
            if token.get("pos") != "PUNCT"
        )
        for paragraph in paragraphs
    ]
    sentence_lengths = [
        sum(1 for token in sentence.get("tokens", []) if token.get("pos") != "PUNCT")
        for sentence in sentences
    ]

    metadata = document.get("statistics", {})
    recorded_tokens = metadata.get("tokens")
    if recorded_tokens is not None and recorded_tokens != len(tokens):
        raise ValueError(
            f"Token count mismatch for {document.get('paper', '<unknown>')}: "
            f"metadata says {recorded_tokens}, nested records contain {len(tokens)}"
        )
    recorded_sentences = metadata.get("sentences")
    if recorded_sentences is not None and recorded_sentences != len(sentences):
        raise ValueError(
            f"Sentence count mismatch for {document.get('paper', '<unknown>')}: "
            f"metadata says {recorded_sentences}, nested records contain {len(sentences)}"
        )
    recorded_paragraphs = metadata.get("paragraphs")
    if recorded_paragraphs is not None and recorded_paragraphs != len(paragraphs):
        raise ValueError(
            f"Paragraph count mismatch for {document.get('paper', '<unknown>')}: "
            f"metadata says {recorded_paragraphs}, nested records contain {len(paragraphs)}"
        )

    return {
        "paper": document["paper"],
        "pages": metadata.get("pages", 0),
        "sections_detected": metadata.get("sections", metadata.get("detected_sections", 0)),
        "paragraphs": len(paragraphs),
        "sentences": len(sentences),
        "tokens_including_punctuation": len(tokens),
        "lexical_tokens_excluding_punctuation": len(lexical_tokens),
        "unique_tokens_casefolded_excluding_punctuation": len(unique_lexical_tokens),
        "average_sentence_length_lexical_tokens": round(
            sum(sentence_lengths) / len(sentence_lengths), 2
        )
        if sentence_lengths
        else 0.0,
        "average_paragraph_length_lexical_tokens": round(
            sum(paragraph_lengths) / len(paragraph_lengths), 2
        )
        if paragraph_lengths
        else 0.0,
    }


def process_files(inputs: list[Path], output_dir: Path) -> list[dict[str, Any]]:
    """Build combined JSON and CSV document-statistics tables."""
    rows = [
        calculate_document_statistics(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(inputs)
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    definitions = {
        "pages": "PDF page count carried forward from Task 1 metadata.",
        "sections_detected": "Heading candidates counted by the Task 2 detector; this is not a gold-verified section count.",
        "paragraphs": "Number of Task 3 paragraph records in the nested Task 5 JSON.",
        "sentences": "Number of Task 4 sentence records nested under paragraphs.",
        "tokens_including_punctuation": "Number of spaCy token records, including punctuation.",
        "lexical_tokens_excluding_punctuation": "Token count after excluding tokens tagged PUNCT; this is the denominator for average lengths.",
        "unique_tokens_casefolded_excluding_punctuation": "Number of distinct token surface forms after casefolding and excluding PUNCT tokens.",
        "average_sentence_length_lexical_tokens": "Mean non-PUNCT spaCy tokens per sentence.",
        "average_paragraph_length_lexical_tokens": "Mean non-PUNCT spaCy tokens per paragraph; paragraphs with zero lexical tokens remain in the denominator.",
    }
    (output_dir / "document_statistics.json").write_text(
        json.dumps({"definitions": definitions, "papers": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "document_statistics.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate document-level statistics from Task 5 token JSON files."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Task 5 token JSON files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/statistics"),
        help="Directory for the combined JSON and CSV tables",
    )
    args = parser.parse_args()
    rows = process_files(args.inputs, args.output_dir)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
