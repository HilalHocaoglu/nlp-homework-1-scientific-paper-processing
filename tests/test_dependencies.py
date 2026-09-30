"""Focused tests for Task 7 dependency sample generation."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scipaper.dependencies import _lookup_sentence, build_dependency_examples


def make_token(text: str) -> dict[str, object]:
    return {
        "token_index": 0,
        "text": text,
        "lemma": text.lower(),
        "pos": "NOUN",
        "dependency": "ROOT",
        "head": text,
        "head_index": 0,
    }


def make_cases(count: int = 10) -> list[dict[str, object]]:
    return [
        {
            "case_id": f"sample_{index}",
            "paper": "paper_a" if index < 2 else f"paper_{index}",
            "page": index + 1,
            "paragraph": index + 1,
            "sentence": 1,
            "section": f"Section {index + 1}",
            "visualize": index < 3,
        }
        for index in range(count)
    ]


def make_token_document(case: dict[str, object]) -> dict[str, object]:
    sentence = {
        "sentence_id": case["sentence"],
        "text": "alpha beta",
        "tokens": [make_token("alpha"), {**make_token("beta"), "token_index": 1}],
    }
    return {
        "paper": case["paper"],
        "paragraphs": [
            {
                "page": case["page"],
                "paragraph": case["paragraph"],
                "section": case["section"],
                "sentences": [sentence],
            }
        ],
    }


class FakeNLP:
    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens or ["alpha", "beta"]

    def __call__(self, text: str) -> list[SimpleNamespace]:
        return [SimpleNamespace(text=token, is_space=False) for token in self.tokens]


class DependencyTests(unittest.TestCase):
    def test_lookup_requires_exact_page_paragraph_section_and_sentence(self) -> None:
        case = make_cases(1)[0]
        document = make_token_document(case)

        found = _lookup_sentence(document, case)
        self.assertEqual(found["sentence"]["text"], "alpha beta")
        self.assertEqual(found["paragraph"]["section"], "Section 1")

        wrong_section = {**case, "section": "Wrong section"}
        with self.assertRaisesRegex(ValueError, "Section mismatch"):
            _lookup_sentence(document, wrong_section)

        missing_sentence = {**case, "sentence": 9}
        with self.assertRaisesRegex(ValueError, "Sentence not found"):
            _lookup_sentence(document, missing_sentence)

    def test_manifest_requires_ten_distinct_nonempty_sections(self) -> None:
        cases = make_cases()
        for case in cases[1:]:
            case["section"] = cases[0]["section"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"cases": cases}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "10 sentences from 10 distinct sections"):
                build_dependency_examples(manifest, root, root / "out", FakeNLP())

    def test_manifest_rejects_duplicate_case_ids(self) -> None:
        cases = make_cases()
        cases[1]["case_id"] = cases[0]["case_id"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"cases": cases}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unique, non-empty case_id"):
                build_dependency_examples(manifest, root, root / "out", FakeNLP())

    def test_build_writes_traceable_token_table_json_and_three_diagrams(self) -> None:
        cases = make_cases()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps({"description": "test manifest", "cases": cases}),
                encoding="utf-8",
            )
            token_dir = root / "tokens"
            token_dir.mkdir()
            for case in cases:
                path = token_dir / f"{case['paper']}_tokens.json"
                if not path.exists():
                    path.write_text(json.dumps(make_token_document(case)), encoding="utf-8")
                else:
                    document = json.loads(path.read_text(encoding="utf-8"))
                    document["paragraphs"].append(
                        make_token_document(case)["paragraphs"][0]
                    )
                    path.write_text(json.dumps(document), encoding="utf-8")

            rendered_page = (
                '<html><head><title>displaCy</title></head>'
                '<body style="font-size: 16px"><figure class="displacy">'
                "<svg></svg></figure></body></html>"
            )
            with patch("scipaper.dependencies.displacy.render", return_value=rendered_page):
                summary = build_dependency_examples(
                    manifest_path, token_dir, root / "out", FakeNLP()
                )

            self.assertEqual(summary["samples"], 10)
            self.assertEqual(summary["distinct_sections"], 10)
            self.assertEqual(summary["token_rows"], 20)
            self.assertEqual(len(summary["visualizations"]), 3)

            with Path(summary["csv"]).open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 20)
            self.assertTrue(
                {"token", "lemma", "pos", "dependency", "head", "page", "section"}
                <= set(rows[0])
            )
            self.assertEqual(rows[0]["token"], "alpha")
            self.assertEqual(rows[0]["head"], "alpha")

            result = json.loads(Path(summary["json"]).read_text(encoding="utf-8"))
            self.assertEqual(result["sample_count"], 10)
            self.assertEqual(result["distinct_section_count"], 10)
            self.assertEqual(result["examples"][0]["text"], "alpha beta")

            for diagram in summary["visualizations"]:
                contents = Path(diagram).read_text(encoding="utf-8")
                self.assertIn("<svg>", contents)
                self.assertEqual(contents.count("<body"), 1)
                self.assertEqual(contents.count("style="), 1)

    def test_build_stops_if_diagram_tokenization_differs_from_task5(self) -> None:
        cases = make_cases()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            token_dir = root / "tokens"
            token_dir.mkdir()
            for case in cases:
                path = token_dir / f"{case['paper']}_tokens.json"
                if not path.exists():
                    path.write_text(json.dumps(make_token_document(case)), encoding="utf-8")
                else:
                    document = json.loads(path.read_text(encoding="utf-8"))
                    document["paragraphs"].append(
                        make_token_document(case)["paragraphs"][0]
                    )
                    path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Tokenizer output changed"):
                build_dependency_examples(
                    manifest_path, token_dir, root / "out", FakeNLP(["different"])
                )


if __name__ == "__main__":
    unittest.main()
