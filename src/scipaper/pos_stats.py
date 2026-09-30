"""Calculate per-paper spaCy POS counts and normalized distributions."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_POS = ("NOUN", "VERB", "ADJ", "ADV", "PROPN", "PRON", "DET", "ADP", "NUM")


def calculate_pos_statistics(document: dict[str, Any]) -> dict[str, Any]:
    """Summarize token POS labels; percentages exclude punctuation tokens."""
    counts: Counter[str] = Counter()
    token_count = 0
    punctuation_count = 0

    for paragraph in document.get("paragraphs", []):
        for sentence in paragraph.get("sentences", []):
            for token in sentence.get("tokens", []):
                token_count += 1
                pos = str(token.get("pos", "")) or "X"
                if pos == "PUNCT":
                    punctuation_count += 1
                else:
                    counts[pos] += 1

    denominator = token_count - punctuation_count
    other_count = sum(count for pos, count in counts.items() if pos not in REQUIRED_POS)
    category_counts = {pos: counts.get(pos, 0) for pos in REQUIRED_POS}
    category_counts["OTHER"] = other_count
    percentages = {
        pos: round((count / denominator * 100), 4) if denominator else 0.0
        for pos, count in category_counts.items()
    }

    return {
        "paper": document["paper"],
        "model": document.get("model", {}),
        "tokenizer_method": document.get("method"),
        "total_tokens_including_punctuation": token_count,
        "punctuation_tokens_excluded_from_pos_percentages": punctuation_count,
        "pos_percentage_denominator": denominator,
        "pos_counts": category_counts,
        "pos_percentages": percentages,
    }


def _write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "paper",
        "pos",
        "count",
        "percentage_of_non_punctuation_tokens",
        "pos_percentage_denominator",
        "punctuation_tokens_excluded",
        "total_tokens_including_punctuation",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            for pos in (*REQUIRED_POS, "OTHER"):
                writer.writerow(
                    {
                        "paper": row["paper"],
                        "pos": pos,
                        "count": row["pos_counts"][pos],
                        "percentage_of_non_punctuation_tokens": row["pos_percentages"][pos],
                        "pos_percentage_denominator": row["pos_percentage_denominator"],
                        "punctuation_tokens_excluded": row[
                            "punctuation_tokens_excluded_from_pos_percentages"
                        ],
                        "total_tokens_including_punctuation": row[
                            "total_tokens_including_punctuation"
                        ],
                    }
                )


def process_files(inputs: list[Path], output_dir: Path) -> list[dict[str, Any]]:
    """Create combined JSON and CSV summaries from Task 5 token files."""
    rows = [
        calculate_pos_statistics(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(inputs)
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pos_statistics.json").write_text(
        json.dumps(
            {
                "definition": {
                    "percentage_denominator": "All spaCy tokens except PUNCT; includes other non-punctuation tags grouped as OTHER.",
                    "required_pos": list(REQUIRED_POS),
                    "other": "Non-punctuation POS labels outside the required nine categories, including AUX, CCONJ, PART, SYM, and X.",
                },
                "papers": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(rows, output_dir / "pos_statistics.csv")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize spaCy POS labels from Task 5 token JSON files."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Task 5 token JSON files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/statistics"),
        help="Directory for the combined JSON and CSV summaries",
    )
    args = parser.parse_args()

    rows = process_files(args.inputs, args.output_dir)
    print(
        json.dumps(
            [
                {
                    "paper": row["paper"],
                    "tokens": row["total_tokens_including_punctuation"],
                    "punctuation": row["punctuation_tokens_excluded_from_pos_percentages"],
                    "pos_denominator": row["pos_percentage_denominator"],
                }
                for row in rows
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
