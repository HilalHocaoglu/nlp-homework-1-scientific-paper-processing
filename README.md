# Homework 1 — Scientific Paper Processing with spaCy

This repository is being developed incrementally to transform scientific
papers from PDF into structured NLP data. The first stage extracts text while
retaining page numbers and line breaks.

## Progress

- [x] Initial repository structure
- [x] Page-based PyMuPDF extraction prototype
- [x] PDF extraction, per-paper counts, and manual review of seven sample pages
- [x] Section heading and subsection detection, with a small visual review
- [ ] Paragraph detection
- [ ] spaCy sentence segmentation, tokenization, and linguistic annotations
- [ ] Statistics and JSON outputs
- [ ] Report and final usage instructions

Experiment decisions and findings are recorded in
[`notes/experiment_log.md`](notes/experiment_log.md).

The extraction stage processes all nine supplied PDFs with the same code and
saves page-marked text and per-paper page, character, and word counts. Manual
review found that reading order depends on layout: sorted text helps on some
single-column and table pages, while preserving PDF order helps on some
multi-column pages. Neither setting is considered best for every page.

The current section detector also runs on all nine PDFs. It combines section
number patterns with PDF font and position cues, and handles small-caps and
lettered appendix headings observed in the supplied set. Its output is a
candidate list, not verified ground truth: only a small set of pages has been
visually reviewed. See the experiment log for false positives, missed
headings, revisions, and remaining limitations.

## Installation

Create a virtual environment with Python 3 and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run the first stage

The notebook and examples expect the nine course PDFs under `data/papers/`.
Place the course-provided files there first; their exact source links and local
storage note are in [`data/papers/README.md`](data/papers/README.md). PDF
copies are excluded from Git until redistribution rights for these versions are
confirmed.

Run extraction from the repository root:

```bash
PYTHONPATH=src python -m scipaper.extraction \
  data/papers/AttentionYouNeed.pdf \
  --output-dir outputs/extracted_text
```

Multiple PDF paths can be passed in the same command. A page-marked `.txt`
file is written under `outputs/extracted_text/` for each PDF. Page, character,
and word counts are printed as JSON in the terminal. Use
`--preserve-pdf-order` to compare PyMuPDF's default text order; without this
option, text blocks are sorted by page position.

## Run section detection

Use the same detector on the supplied PDFs:

```bash
PYTHONPATH=src python -m scipaper.sections \
  data/papers/AttentionYouNeed.pdf \
  data/papers/1406.1078v3.pdf
```

Pass additional paths from `data/papers/` as needed. The JSON printed to the
terminal contains each candidate's section ID (when present), title, and
one-based page number. The notebook runs the detector against all nine files
listed in `PDF_FILES`.

## Run section detection

Use the same detector on the supplied PDFs:

```bash
PYTHONPATH=src python -m scipaper.sections \
  "$HOME/Downloads/AttentionYouNeed.pdf" \
  "$HOME/Downloads/1406.1078v3.pdf"
```

Pass additional PDF paths as needed. The JSON printed to the terminal contains
each candidate's section ID (when present), title, and one-based page number.
The notebook runs the detector against all nine files listed in `PDF_FILES`.

## Input and output

- **Input:** The nine course PDFs stored locally under `data/papers/`; the
  notebook and CLI use these repository-relative paths.
- **First output:** UTF-8 text files with page boundaries marked as
  `===== PAGE n =====`.
- **Later output:** One JSON file per paper for use in Homework 2.

## Limitations

PDF text and heading extraction can make mistakes on two-column pages, tables,
equations, headers, and footers. The current heading rules are provisional;
visual review and their observed limits are documented in the experiment log.
