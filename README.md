# Homework 1 — Scientific Paper Processing with spaCy

NLP pipeline that transforms scientific PDF documents into structured linguistic
data. Processes all nine supplied papers with the same code:

**PDF → Text → Sections → Paragraphs → Sentences → Tokens → Linguistic Annotations**

## Installation

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Required Packages

| Package | Purpose |
|---------|---------|
| PyMuPDF | PDF text extraction |
| spaCy | NLP pipeline (tokenization, POS, dependencies) |
| en_core_web_sm | English language model for spaCy |
| pandas | Statistics tables and data display |
| jupyter | Running the notebook |

All packages are listed in `requirements.txt`.

## How to Run

### Option 1: Run the Notebook (Recommended)

1. Open the project folder in VS Code with the **Python** and **Jupyter** extensions
2. Open `notebooks/homework1.ipynb`
3. Select the `.venv` Python interpreter as the notebook kernel
4. Use **Run All** — all tasks execute in order

### Option 2: Run Individual Pipeline Stages

Each stage can also be run from the command line:

```bash
# Task 1 — Extract text from PDFs
PYTHONPATH=src python -m scipaper.extraction data/papers/*.pdf

# Task 2 — Detect sections
PYTHONPATH=src python -m scipaper.sections data/papers/*.pdf

# Task 3 — Extract paragraphs
PYTHONPATH=src python -m scipaper.paragraphs data/papers/*.pdf

# Task 4 — Segment sentences
PYTHONPATH=src python -m scipaper.sentences outputs/paragraphs/*_paragraphs.json

# Task 5 — Tokenize and annotate
PYTHONPATH=src python -m scipaper.tokens outputs/sentences/*_sentences.json

# Task 6 — POS statistics
PYTHONPATH=src python -m scipaper.pos_stats outputs/tokens/*_tokens.json

# Task 7 — Dependency examples
PYTHONPATH=src python -m scipaper.dependencies

# Task 8 — Document statistics
PYTHONPATH=src python -m scipaper.document_stats outputs/tokens/*_tokens.json

# Task 9 — Final JSON output
PYTHONPATH=src python -m scipaper.final_json outputs/tokens/*_tokens.json
```

### Run Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Input Format

Place the nine course PDFs in `data/papers/`:

```
data/papers/
├── AttentionYouNeed.pdf          # Main paper
├── 1406.1078v3.pdf               # Cited papers
├── 1409.0473v7.pdf
├── 1412.3555v1.pdf
├── 1601.06733v7.pdf
├── 1607.06450v1.pdf
├── 1610.02357v3.pdf
├── 1703.03906v2.pdf
└── N16-1024.pdf
```

## Output Format

All outputs are written to `outputs/`:

```
outputs/
├── extracted_text/     # Task 1: UTF-8 text files with page markers
├── paragraphs/         # Task 3: Paragraph JSON with section labels
├── sentences/          # Task 4: Sentence-segmented JSON
├── tokens/             # Task 5: Token-annotated JSON
├── statistics/         # Tasks 6, 8: POS and document statistics (CSV + JSON)
├── dependency_examples/ # Task 7: Token tables, CSV, and displaCy HTML
└── json/               # Task 9: One final nested JSON per paper
```

### Final JSON Structure (Task 9)

Each JSON file follows this hierarchy:

```json
{
  "paper": "AttentionYouNeed",
  "sections": [
    {
      "section_id": "3.2",
      "title": "3.2 Attention",
      "paragraphs": [
        {
          "paragraph_id": 1,
          "page": 4,
          "sentences": [
            {
              "sentence_id": 1,
              "text": "An attention function can be described...",
              "tokens": [
                {
                  "text": "attention",
                  "lemma": "attention",
                  "pos": "NOUN",
                  "dependency": "compound",
                  "head": "function"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## Submission Files

| Deliverable | Location |
|-------------|----------|
| A. Notebook | `notebooks/homework1.ipynb` |
| B. JSON files | `outputs/json/` (one per paper) |
| C. Report | `reports/homework1_report.md` |
| D. README | This file |

## Experiment Log

Detailed decisions, method comparisons, and limitations are documented in
[`notes/experiment_log.md`](notes/experiment_log.md).
