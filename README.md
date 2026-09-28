# Homework 1 — Scientific Paper Processing with spaCy

This repository is being developed incrementally to transform scientific
papers from PDF into structured NLP data. The first stage extracts text while
retaining page numbers and line breaks.

## Progress

- [x] Initial repository structure
- [x] Page-based PyMuPDF extraction prototype
- [x] Initial manual quality review of four representative pages
- [ ] Section and paragraph detection
- [ ] spaCy sentence segmentation, tokenization, and linguistic annotations
- [ ] Statistics and JSON outputs
- [ ] Report and final usage instructions

Experiment decisions and findings are recorded in
[`notes/experiment_log.md`](notes/experiment_log.md).

The first review found that reading order depends on page layout: sorted text
helped on the sampled single-column pages and table, while preserving PDF order
helped on the sampled two-column prose page. Neither setting is considered
best for every page.

## Installation

Create a virtual environment with Python 3 and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run the first stage

Pass PDF paths on the command line:

```bash
PYTHONPATH=src python -m scipaper.extraction \
  "$HOME/Downloads/AttentionYouNeed.pdf" \
  --output-dir outputs/extracted_text
```

Multiple PDF paths can be passed in the same command. A page-marked `.txt` file
is written under `outputs/extracted_text/` for each PDF. Page, character, and
word counts are printed as JSON in the terminal. Use `--preserve-pdf-order` to
compare PyMuPDF's default text order; without this option, text blocks are
sorted by page position.

## Input and output

- **Input:** PDF files. They do not need to be copied into the repository; pass
  their paths to the command or set them in the notebook.
- **First output:** UTF-8 text files with page boundaries marked as
  `===== PAGE n =====`.
- **Later output:** One JSON file per paper for use in Homework 2.

## Limitations

The first prototype tries to order text by page coordinates. It can make
mistakes on two-column pages, tables, equations, headers, and footers. These
cases will be documented in the experiment log after reviewing the output.
