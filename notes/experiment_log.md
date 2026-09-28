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

## September 28 — Controlled reading-order review

- **Question:** Does one PyMuPDF ordering option preserve headings, paragraph
  flow, and figure/table context across different page layouts?
- **Sample selection:** Manually reviewed the rendered source page alongside
  both extraction outputs for four pages: `AttentionYouNeed.pdf` pages 2 and 6,
  `1406.1078v3.pdf` page 2, and `N16-1024.pdf` page 2. This gives us single-
  column prose, a single-column table, a two-column page with a figure, and a
  two-column prose page. This is a small, purposive sample, not a benchmark of
  all pages or papers.
- **Procedure:** Kept the PDF, page, and extraction code fixed; compared
  `page.get_text("text", sort=False)` with `sort=True`. Checked the visual page
  against heading order, column order, paragraph continuity, and table/figure
  placement. No automatic quality score was used.
- **Observations:**

  | Page type | `sort=False` | `sort=True` | Page-level decision |
  | --- | --- | --- | --- |
  | `AttentionYouNeed.pdf`, p. 2; single-column prose | Paragraphs stay in order, but the heading number and title are separate lines. | Joins `1 Introduction`, keeps paragraphs in order, and makes paragraph boundaries clearer. | Prefer `sort=True` for this page. |
  | `AttentionYouNeed.pdf`, p. 6; single-column Table 1 | Emits table headers and values by column, so row-to-value relationships are hard to recover. | Reconstructs the visible table row by row; following section text remains in order. | Prefer `sort=True` for this page. |
  | `1406.1078v3.pdf`, p. 2; two columns and Figure 1 | Preserves the left prose column, then figure labels/caption, then right prose; figure content interrupts the page-level stream. | Interleaves figure labels with prose (`Decoder2`, `xTwhere`) and is harder to read. | `sort=False` is less disruptive here, but neither is fully satisfactory. |
  | `N16-1024.pdf`, p. 2; two-column prose | Reads the complete left column before the right column, preserving section and paragraph flow. | Alternates lines across columns, breaking paragraph flow. | Prefer `sort=False` for this page. |

- **Third-method trial:** Because neither built-in option gave a clean result on
  the figure page, tried a one-off prototype: assign text blocks to the left or
  right half by horizontal center, then sort each half from top to bottom. It
  moved Figure 1 labels and caption together at the start of the right column,
  but fragmented equation components into separate blocks. This one-page
  prototype is not ready to replace either production option; it needs a more
  careful treatment of equations, full-width material, and tables.
- **Decision:** Keep both existing options. Use `sort=True` as a useful choice
  for the reviewed single-column prose and table pages, and preserve PDF order
  as a useful choice for the reviewed two-column prose page. We have not
  selected a universal setting. Do not integrate the coordinate prototype yet.
- **Next experiment:** Apply the same manual comparison to additional pages,
  including a second table/figure layout and a page with a full-width heading.
  If the coordinate prototype still helps without damaging paragraph flow,
  refine it as an explicit third strategy; otherwise keep the two current
  options. Once the extraction choice is supported by more examples, begin
  section-heading detection and record its failures in the same way.
- **Open limitations:** Four pages from three papers cannot establish which
  setting is best across all nine PDFs. Math and complex visual layouts remain
  difficult, and this review does not yet measure downstream spaCy effects.
