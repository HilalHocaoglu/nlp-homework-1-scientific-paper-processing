# Experiment log

This log records actual experiments and the decisions they informed. Failed
and incomplete attempts remain part of the record.

## September 28 — Setup and PDF text extraction

- **Question:** Which local tool can extract page text from the supplied PDFs?
- **Environment check:** Checked for `pdftotext`, `mutool`, PyMuPDF,
  `pdfplumber`, `pypdf`, and spaCy.
- **Observation:** No PDF tools were installed initially. PyMuPDF was installed
  in the local `.venv` after network access was approved. spaCy is not
  installed yet.
- **First method:** Tried PyMuPDF's `page.get_text("text", sort=True)` as the
  baseline. It retains page numbers and extracts text page by page, but does
  not guarantee correct reading order.
- **Reason for this choice:** PyMuPDF is allowed by the assignment. With
  `sort=True`, it attempts to order text by page position; columns and complex
  figures need separate inspection.
- **Output:** Processed all nine PDFs with the same code: 107 pages, 465,733
  characters, and 57,726 words. The regex word count treats Unicode letters,
  digits, and hyphenated compounds as single words.
- **First observation:** On page 2 of Attention Is All You Need, `sort=True`
  produced clean spacing around the heading and paragraphs. On page 2 of
  `1406.1078v3.pdf`, however, figure labels were mixed into text blocks (for
  example, `Decoder2` and `xTwhere`). On page 2 of `N16-1024.pdf`, `sort=True`
  interleaved lines from the left and right columns.
- **Controlled comparison:** Compared `sort=False` and `sort=True` on the same
  three pages. On Attention page 2, `sort=False` preserved paragraph text but
  split the section heading across lines. On N16 page 2, `sort=False` preserved
  the left-column paragraph flow, while `sort=True` mixed it with the right
  column. No single setting worked best for every layout.
- **Decision:** Keep both ordering options (`sort_blocks` and
  `--preserve-pdf-order`). Neither is being treated as universally superior.
- **Next experiment:** Compare both settings systematically on single-column
  and two-column pages. Then decide whether a third method, such as grouping
  text by horizontal coordinates before ordering it, is worth the added
  complexity.
- **Open limitations:** Equations and tables can be distorted when converted
  to plain text; headers and footers have not been removed. The current review
  covers only three pages and is not a quality claim about all nine papers.
