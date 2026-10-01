"""Tokenize cleaned Homework 1 sentences and add spaCy linguistic annotations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import spacy
from spacy.language import Language
from spacy.tokenizer import Tokenizer
from spacy.util import compile_infix_regex


# PDF extraction can omit the visible space around inline mathematical
# notation (for example, ``p(xt)`` or ``Sublayer(x)``). Split parentheses at
# word boundaries while leaving spaCy's other English tokenizer rules intact.
SCIENTIFIC_INFIXES = [
    r"(?<=[^\W\d_])(?=\()",
    r"(?<=\()(?=[^\W\d_])",
]


def configure_scientific_tokenizer(nlp: Language) -> None:
    """Add conservative parenthesis boundaries to spaCy's English tokenizer."""
    infix_re = compile_infix_regex(list(nlp.Defaults.infixes) + SCIENTIFIC_INFIXES)
    nlp.tokenizer.infix_finditer = infix_re.finditer


def _tokenize_sentences(
    sentence_records: list[dict[str, Any]], nlp: Language
) -> tuple[list[dict[str, Any]], int]:
    texts = [str(sentence.get("text", "")) for sentence in sentence_records]
    tokenized: list[dict[str, Any]] = []
    token_count = 0

    for sentence, doc in zip(sentence_records, nlp.pipe(texts, batch_size=128), strict=True):
        tokens = [
            {
                "token_index": token.i,
                "text": token.text,
                "whitespace_after": token.whitespace_,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "dependency": token.dep_,
                "head": token.head.text,
                "head_index": token.head.i,
            }
            for token in doc
            if not token.is_space
        ]
        token_count += len(tokens)
        tokenized.append({**sentence, "token_count": len(tokens), "tokens": tokens})

    return tokenized, token_count


def annotate_document(sentence_document: dict[str, Any], nlp: Language) -> dict[str, Any]:
    """Add token-level spaCy fields to all sentence records in one paper."""
    paragraphs: list[dict[str, Any]] = []
    total_tokens = 0

    for paragraph in sentence_document.get("paragraphs", []):
        sentences, token_count = _tokenize_sentences(paragraph.get("sentences", []), nlp)
        total_tokens += token_count
        paragraphs.append({**paragraph, "sentences": sentences})

    statistics = dict(sentence_document.get("statistics", {}))
    statistics["tokens"] = total_tokens
    return {
        **sentence_document,
        "method": "spacy_parser_with_scientific_parenthesis_infixes",
        "tokenizer_notes": {
            "parentheses": "Split when attached to a Unicode letter on either side; other spaCy English infix rules are retained.",
            "token_index": "Zero-based within each sentence.",
            "token_count": "Includes punctuation tokens; whitespace is stored on the preceding token.",
            "annotation_context": "Each cleaned sentence is parsed independently.",
        },
        "paragraphs": paragraphs,
        "statistics": statistics,
    }


def process_file(path: Path, nlp: Language, output_dir: Path) -> dict[str, Any]:
    """Read one cleaned sentence JSON file, annotate it, and save the token result."""
    document = json.loads(path.read_text(encoding="utf-8"))
    result = annotate_document(document, nlp)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / path.name.replace("_sentences.json", "_tokens.json")
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"paper": result["paper"], **result["statistics"], "output": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add spaCy tokenization and linguistic annotations to cleaned sentences."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Cleaned sentence JSON files")
    parser.add_argument(
        "--model", default="en_core_web_sm", help="Installed spaCy model (default: en_core_web_sm)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/tokens"),
        help="Directory for annotated token JSON files",
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
    summaries = [process_file(path, nlp, args.output_dir) for path in args.inputs]
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
