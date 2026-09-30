"""Create dependency tables and displaCy diagrams for curated examples."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path
from typing import Any

import spacy
from spacy import displacy
from spacy.language import Language

from .tokens import configure_scientific_tokenizer


def _lookup_sentence(document: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    paragraph = next(
        (
            item
            for item in document.get("paragraphs", [])
            if item.get("page") == case["page"] and item.get("paragraph") == case["paragraph"]
        ),
        None,
    )
    if paragraph is None:
        raise ValueError(f"Paragraph not found for dependency sample {case['case_id']}")
    if paragraph.get("section") != case["section"]:
        raise ValueError(
            f"Section mismatch for {case['case_id']}: expected {case['section']!r}, "
            f"found {paragraph.get('section')!r}"
        )
    sentence = next(
        (
            item
            for item in paragraph.get("sentences", [])
            if item.get("sentence_id") == case["sentence"]
        ),
        None,
    )
    if sentence is None:
        raise ValueError(f"Sentence not found for dependency sample {case['case_id']}")
    return {"paragraph": paragraph, "sentence": sentence}


def _write_html(path: Path, title: str, details: str, doc: Any) -> None:
    rendered = displacy.render(
        doc,
        style="dep",
        page=True,
        options={"compact": True, "distance": 100},
    )
    safe_title = html.escape(title)
    safe_details = html.escape(details)
    rendered = rendered.replace("<title>displaCy</title>", f"<title>{safe_title}</title>")
    rendered = rendered.replace(
        "<figure ",
        f"<h1>{safe_title}</h1><p>{safe_details}</p><figure ",
        1,
    )
    path.write_text(rendered, encoding="utf-8")


def build_dependency_examples(
    manifest_path: Path,
    token_dir: Path,
    output_dir: Path,
    nlp: Language,
) -> dict[str, Any]:
    """Materialize selected token tables and diagrams from Task 5 outputs."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    sections = {case.get("section") for case in cases if case.get("section")}
    case_ids = [case.get("case_id") for case in cases]
    if len(cases) < 10 or len(sections) < 10:
        raise ValueError("Task 7 requires at least 10 sentences from 10 distinct sections")
    if any(not case_id for case_id in case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError("Every dependency sample must have a unique, non-empty case_id")
    if len(sections) != len(cases):
        raise ValueError("Every dependency sample must have a non-empty, distinct section")

    output_dir.mkdir(parents=True, exist_ok=True)
    paper_cache: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    diagrams: list[str] = []

    for case in cases:
        paper_id = case["paper"]
        if paper_id not in paper_cache:
            input_path = token_dir / f"{paper_id}_tokens.json"
            paper_cache[paper_id] = json.loads(input_path.read_text(encoding="utf-8"))
        source = _lookup_sentence(paper_cache[paper_id], case)
        sentence = source["sentence"]
        result = {
            **case,
            "text": sentence["text"],
            "tokens": sentence["tokens"],
        }
        results.append(result)

        for token in sentence["tokens"]:
            table_rows.append(
                {
                    "case_id": case["case_id"],
                    "paper": paper_id,
                    "page": case["page"],
                    "section": case["section"],
                    "paragraph": case["paragraph"],
                    "sentence": case["sentence"],
                    "sentence_text": sentence["text"],
                    "token_index": token["token_index"],
                    "token": token["text"],
                    "lemma": token["lemma"],
                    "pos": token["pos"],
                    "dependency": token["dependency"],
                    "head": token["head"],
                    "head_index": token["head_index"],
                }
            )

        if case.get("visualize"):
            doc = nlp(sentence["text"])
            parsed_tokens = [token.text for token in doc if not token.is_space]
            source_tokens = [token["text"] for token in sentence["tokens"]]
            if parsed_tokens != source_tokens:
                raise ValueError(f"Tokenizer output changed for diagram {case['case_id']}")
            filename = re.sub(r"[^a-z0-9]+", "_", case["case_id"].lower()).strip("_")
            diagram_path = output_dir / f"{filename}.html"
            _write_html(
                diagram_path,
                f"{case['case_id']} — {paper_id}",
                f"PDF page {case['page']} · {case['section']} · {sentence['text']}",
                doc,
            )
            diagrams.append(str(diagram_path))

    csv_path = output_dir / "dependency_tokens.csv"
    fieldnames = list(table_rows[0]) if table_rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(table_rows)

    json_path = output_dir / "dependency_examples.json"
    json_path.write_text(
        json.dumps(
            {
                "description": manifest["description"],
                "limitations": manifest.get("limitations"),
                "sample_count": len(results),
                "distinct_section_count": len(sections),
                "visualizations": diagrams,
                "examples": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "samples": len(results),
        "distinct_sections": len(sections),
        "token_rows": len(table_rows),
        "json": str(json_path),
        "csv": str(csv_path),
        "visualizations": diagrams,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create dependency tables and displaCy visualizations from curated examples."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/annotations/task7_dependency_examples.json"),
        help="JSON manifest with sentence locations and three selected diagrams",
    )
    parser.add_argument(
        "--token-dir",
        type=Path,
        default=Path("outputs/tokens"),
        help="Directory containing Task 5 token JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/dependency_examples"),
        help="Directory for the dependency table and diagrams",
    )
    parser.add_argument(
        "--model", default="en_core_web_sm", help="Installed spaCy model"
    )
    args = parser.parse_args()
    try:
        nlp = spacy.load(args.model)
    except OSError as error:
        raise SystemExit(
            f"spaCy model {args.model!r} is not installed. Run: "
            f"python -m spacy download {args.model}"
        ) from error
    configure_scientific_tokenizer(nlp)
    print(json.dumps(build_dependency_examples(args.manifest, args.token_dir, args.output_dir, nlp), indent=2))


if __name__ == "__main__":
    main()
