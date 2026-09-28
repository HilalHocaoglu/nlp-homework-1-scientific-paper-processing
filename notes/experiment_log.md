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
  to plain text; headers and footers have not been removed. That initial review
  covered only three pages and was not a quality claim about all nine papers.

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

## September 28 — Expanded extraction review and batch verification

- **Question:** Do the first observations hold on a title page and on tables
  embedded in two-column papers, and are the saved outputs reproducible?
- **Additional sample:** Reviewed three more rendered pages with both ordering
  settings: `AttentionYouNeed.pdf` page 1 (full-width title, author block, and
  abstract), `1406.1078v3.pdf` page 7 (Table 2 above two-column prose), and
  `N16-1024.pdf` page 7 (Table 1 in a two-column page).
- **Additional observations:**
  - On Attention page 1, `sort=False` keeps the title, author details, and
    abstract in a readable sequence. `sort=True` pulls the margin arXiv date and
    identifier into the author/email lines and joins separate author blocks.
  - On the two-column table pages, `sort=True` places table cells into more
    row-like sequences, but can mix the prose columns below or beside the table.
    `sort=False` keeps more of the source block order, but may emit table values
    column by column, making row relationships less clear. The trade-off depends
    on the page.
  - Together with the earlier pages, the sample confirms errors in column
    ordering, table reading order, figure labels entering prose, margin metadata
    entering body text, equation extraction, and line-break hyphenation. For
    example, the sorted RNN Encoder–Decoder page joins figure text as
    `Decoder2`/`xTwhere`; the N16 prose page retains a line break in
    `approx-` / `imating`; and equations are split into positioned fragments.
- **Batch run:** Ran the current extraction module with its default setting on
  all nine supplied PDFs, without paper-specific code changes. The generated
  files matched all nine text files in the VS Code project byte for byte, and
  each file had one page marker per PDF page.

  | Paper | Pages | Characters | Words |
  | --- | ---: | ---: | ---: |
  | `AttentionYouNeed.pdf` | 15 | 44,623 | 6,240 |
  | `1406.1078v3.pdf` | 15 | 66,324 | 7,804 |
  | `1409.0473v7.pdf` | 15 | 60,133 | 8,311 |
  | `1412.3555v1.pdf` | 9 | 28,097 | 3,967 |
  | `1601.06733v7.pdf` | 11 | 58,932 | 7,024 |
  | `1607.06450v1.pdf` | 14 | 62,658 | 7,698 |
  | `1610.02357v3.pdf` | 8 | 38,972 | 4,474 |
  | `1703.03906v2.pdf` | 9 | 47,065 | 5,424 |
  | `N16-1024.pdf` | 11 | 58,929 | 6,784 |
  | **Total** | **107** | **465,733** | **57,726** |

- **Task 1 decision:** The page-based extraction, per-paper counts, and saved
  text outputs work for all supplied PDFs using the same program. Keep
  `sort=True` as the reproducible default baseline and retain
  `--preserve-pdf-order` for comparison. Neither option is claimed to be best
  for every layout. The coordinate prototype remains unintegrated because it
  improves one figure example but damages equation order.
- **Task 1 status:** The required extraction outputs and counts are available,
  and more than three concrete extraction limitations have been observed and
  documented. This completes the first task stage; it does not claim perfect
  reconstruction or a page-by-page quality guarantee.
- **Next step:** Start Task 2 with a general section-heading baseline. Collect
  heading examples from multiple supplied papers, record false positives and
  missed headings, and revise the rule only when those examples show a specific
  failure.
- **Open limitations:** The manual sample covers seven pages from three papers,
  not every page. Page count and text-file consistency verify the batch run,
  not reading-order accuracy. Headers/footers, equations, tables, and line-end
  hyphenation still need downstream handling or explicit reporting.

## September 28 — Task 2: section and subsection detection

- **Question:** Can one general detector find section headings across the nine
  supplied papers without maintaining a separate list for each paper?
- **Baseline attempt:** Applied a numbered-line regular expression to the
  extracted text. It found many headings in the Transformer paper, but also
  treated author affiliations (`2 Google Research...`), body text beginning
  with years (`2014 English-French dataset...`), footnotes, equations, figure
  labels, and numbered parsing examples as section candidates. It also merged
  some headings with following body text on two-column pages. This is a useful
  candidate generator, but too noisy by itself.
- **Attempt 2 — typography-aware numbered headings:** Read PyMuPDF's PDF text
  blocks and span metadata. Required a numbered heading pattern plus bold or
  medium font styling, or a font size larger than the page's estimated body
  size. Added a short allowlist of common unnumbered labels (Abstract,
  Acknowledgments, References, and Appendix). This substantially reduced
  false positives and found the major headings in most papers.
- **Failure found:** The first style-aware version missed legitimate
  subsections in `1409.0473v7.pdf`: its small-caps headings (for example
  `2.1 RNN ENCODER–DECODER`) use the same regular font size as body text. A
  strict emphasis/size requirement therefore missed whole subsection groups
  and lettered appendix subsections.
- **Attempt 3 — compact small-caps and appendix headings:** Added a fallback
  for short, standalone, mostly uppercase numbered headings, and extended
  section IDs to appendix forms such as `A.1.1`. Added detection for styled
  lettered appendix headings such as `A Model Architecture`. The fallback
  recovered the 1409 subsection list and appendix structure.
- **Second failure and revision:** Applying the broad lettered pattern
  temporarily classified equation fragments such as `G = GlGr` and parsing
  labels such as `0 NT(S)` as headings. We narrowed ordinary appendix IDs to
  letter-plus-number forms, allowed a single-letter appendix label only when
  its title has heading styling, rejected very short or punctuation-led
  titles, and used font-style transitions to trim body text that shared a PDF
  block with a bold heading. This also corrected the merged `A.1.1 Decoder The
  decoder starts...` candidate to the heading `A.1.1 Decoder`.
- **Visual review:** Compared detector output with rendered source pages for
  four representative pages: `1409.0473v7.pdf` page 2 (small-caps subsection
  2.1), `1610.02357v3.pdf` page 2 (wrapped subsection 1.2),
  `1703.03906v2.pdf` page 3 (two-column subsections 3.2 and 3.3), and
  `N16-1024.pdf` page 2 (sections 2, 3, and 3.1). Those visible headings were
  found with the expected page and reading order. This review checks selected
  examples; it is not a complete page-by-page gold annotation.
- **Batch run:** Ran the same final detector on all nine PDFs. Candidate
  counts were: `1406.1078v3` 23; `1409.0473v7` 33; `1412.3555v1` 14;
  `1601.06733v7` 14; `1607.06450v1` 22; `1610.02357v3` 19;
  `1703.03906v2` 20; `AttentionYouNeed` 25; and `N16-1024` 22 (192 total).
  The output includes section IDs, titles, and one-based page numbers.
- **Decision:** Keep the style-aware rules plus the compact small-caps and
  lettered appendix cases. They capture distinct formats present in the
  supplied papers while filtering the concrete equation, footnote, and table
  examples found in the baseline. The rules are general rather than
  paper-specific.
- **Task 2 status:** The detector is implemented and run on all supplied
  papers, its output is available in the notebook, and representative pages
  have been visually checked. Treat the result as provisional: no full gold
  heading inventory exists, some styles and unnumbered labels may still be
  missed, and the coordinate-based page ordering is not a guarantee for
  complex layouts. Task 3 is paragraph boundary detection within the detected
  sections.
- **Next experiment:** For Task 3, compare blank-line boundaries with a
  layout-aware paragraph grouping on selected single- and two-column pages.
  Record where each merges or splits paragraphs before choosing one.
