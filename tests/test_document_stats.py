"""Tests for Task 8 document-level counts and exported summaries."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scipaper.document_stats import calculate_document_statistics, process_files


def token(text: str, pos: str) -> dict[str, str]:
    return {"text": text, "pos": pos}


def example_document() -> dict[str, object]:
    return {
        "paper": "fixture-paper",
        "statistics": {"pages": 2, "sections": 3, "paragraphs": 2, "sentences": 3, "tokens": 9},
        "paragraphs": [
            {
                "sentences": [
                    {"tokens": [token("Model", "NOUN"), token("runs", "VERB"), token(".", "PUNCT")]},
                    {"tokens": [token("model", "NOUN"), token("fast", "ADV"), token(".", "PUNCT")]},
                ]
            },
            {"sentences": [{"tokens": [token("we", "PRON"), token("run", "VERB"), token("!", "PUNCT")]}]},
        ],
    }


class DocumentStatisticsTests(unittest.TestCase):
    def test_counts_normalized_unique_forms_and_average_lengths(self) -> None:
        result = calculate_document_statistics(example_document())

        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["sections_detected"], 3)
        self.assertEqual(result["paragraphs"], 2)
        self.assertEqual(result["sentences"], 3)
        self.assertEqual(result["tokens_including_punctuation"], 9)
        self.assertEqual(result["lexical_tokens_excluding_punctuation"], 6)
        self.assertEqual(result["unique_tokens_casefolded_excluding_punctuation"], 5)
        self.assertEqual(result["average_sentence_length_lexical_tokens"], 2.0)
        self.assertEqual(result["average_paragraph_length_lexical_tokens"], 3.0)

    def test_zero_sentence_document_returns_zero_averages(self) -> None:
        document = {
            "paper": "empty-paper",
            "statistics": {"pages": 1, "sections": 0, "paragraphs": 0, "sentences": 0, "tokens": 0},
            "paragraphs": [],
        }
        result = calculate_document_statistics(document)
        self.assertEqual(result["average_sentence_length_lexical_tokens"], 0.0)
        self.assertEqual(result["average_paragraph_length_lexical_tokens"], 0.0)
        self.assertEqual(result["unique_tokens_casefolded_excluding_punctuation"], 0)

    def test_detected_sections_falls_back_to_extraction_metadata_name(self) -> None:
        document = example_document()
        document["statistics"] = {"detected_sections": 7}
        result = calculate_document_statistics(document)
        self.assertEqual(result["sections_detected"], 7)

    def test_mismatched_metadata_is_rejected(self) -> None:
        for field, bad_value in (("paragraphs", 99), ("sentences", 99), ("tokens", 99)):
            with self.subTest(field=field):
                document = example_document()
                document["statistics"][field] = bad_value
                with self.assertRaisesRegex(ValueError, "count mismatch"):
                    calculate_document_statistics(document)

    def test_process_files_writes_comparable_csv_and_definition_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "fixture.json"
            input_path.write_text(json.dumps(example_document()), encoding="utf-8")
            output_dir = root / "statistics"

            rows = process_files([input_path], output_dir)

            csv_path = output_dir / "document_statistics.csv"
            json_path = output_dir / "document_statistics.json"
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                csv_rows = list(csv.DictReader(stream))
            json_result = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(csv_rows[0]["paper"], "fixture-paper")
            self.assertEqual(csv_rows[0]["tokens_including_punctuation"], "9")
            self.assertIn("average_sentence_length_lexical_tokens", json_result["definitions"])
            self.assertEqual(json_result["papers"][0]["unique_tokens_casefolded_excluding_punctuation"], 5)


if __name__ == "__main__":
    unittest.main()
