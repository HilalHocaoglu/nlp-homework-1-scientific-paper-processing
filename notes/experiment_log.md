# Experiment log

Short chronological record of the methods tried, what we observed, and why we
kept or changed each method. Scores apply only to the labeled examples named
here; they are not claims about every page.

## Current-version audit — September 30

- **Why rerun:** The Task 3 paragraph filter changed, so paragraph IDs and
  downstream counts no longer matched earlier Task 4 labels, Task 7 sentence
  locations, or saved Task 8 statistics. Treat counts recorded below as the
  history of earlier runs unless this section gives a newer value.
- **Task 3:** The notebook regenerated all nine paragraph files: 928 records
  over 107 pages. The two fully labeled development pages still match 14/14
  paragraph groups. Visual inspection of later outputs found some table rows
  and equation-adjacent fragments retained as paragraph candidates, so the
  small page score does not cover those layouts.
- **Task 4:** The former 20-case review was tied to old paragraph numbers and
  cannot be transferred by page and number alone. A fresh visual sample of
  three paragraphs across three papers matched 3/3 expected sentence endings.
  This sample is deliberately small and is not a corpus-wide score. The current
  cases and expected endings are in
  `data/annotations/task4_current_manual_review.json`.
- **Tasks 5–6:** The latest notebook run generated 2,285 sentences and 48,068
  annotated tokens. The POS denominator is 40,983 non-punctuation tokens; the
  previous tokenizer comparison totals are historical and were removed from
  current-run reporting.
- **Task 7:** The first rerun exposed obsolete paragraph/section locations in
  the dependency manifest. I reselected ten sentences from ten distinct
  sections using current token outputs. The regenerated files contain 238
  token rows and three displaCy diagrams. These parses remain model outputs,
  not gold trees.
- **Tasks 8–9:** Task 8 now regenerates its CSV and JSON from current Task 5
  files instead of reading stale saved statistics. Latest totals are 107
  pages, 192 detected heading candidates, 928 paragraphs, 2,285 sentences,
  48,068 tokens, and 157 section groups with paragraphs. Task 9 regenerated
  one nested JSON file per paper.
- **Notebook run:** After the above changes, all 34 notebook cells completed
  without execution errors. The saved notebook includes those outputs. No
  commit or push was made.
- **Open limitations:** PDF blocks still split some prose around tables,
  displayed equations, and figures. The current Task 4 sample is small, and
  the Task 7 dependency examples have not been compared with manually labeled
  gold trees.

## Task 1 — PDF text extraction (September 28)

**Question:** Which allowed extraction approach keeps page text and reading
order usable across different paper layouts?

- **Tried:** PyMuPDF `sort=True` and `sort=False` on the same pages. `sort=True`
  joined some headings and read the reviewed single-column pages and one table
  more cleanly. `sort=False` preserved left-to-right column flow on some
  two-column pages. Neither worked best everywhere.
- **Third-method prototype:** Grouped text blocks by horizontal position, then
  sorted within columns. It improved one figure-page order but split equations
  into fragments. We did not adopt it as the general extraction method.
- **Decision:** Keep `sort=True` as the reproducible default and expose
  preserve-PDF-order for comparison. Record page-level differences rather
  than naming one setting universally best.
- **Evidence:** Visual comparison covered seven pages across three papers:
  single-column prose, title page, two-column prose, figures, tables, and
  equations. All nine PDFs (107 pages) processed; output totals were 465,733
  characters and 57,726 regex-counted words. Regenerated text matched the
  project outputs byte for byte and had one page marker per PDF page.
- **Limits:** This is a small visual sample, not a reading-order benchmark.
  Equations, table structure, figures, headers/footers, and line-end hyphens
  can still be distorted.

## Task 2 — Section and subsection detection (September 28)

**Question:** Can one detector find headings across papers without a
paper-specific heading list?

- **Attempt 1 — numbered-line regex:** Found many real headings, but also
  affiliations, years in prose, footnotes, equations, figure labels, and
  parsing examples. Some heading text merged with following prose.
- **Attempt 2 — typography-aware rule:** Combined numbering with bold/medium
  style or size relative to body text, plus common unnumbered labels. It
  reduced false positives but missed same-size small-caps headings in
  `1409.0473v7.pdf` and some appendix subsections.
- **Attempt 3 — small-caps and appendix support:** Added a short uppercase
  fallback and appendix IDs. A broad lettered pattern then misclassified
  equation and parsing labels. Narrowing the pattern, requiring style for
  single-letter appendix headings, and trimming following body text corrected
  those examples.
- **Decision:** Keep the style-aware detector with the revised small-caps and
  appendix rules. It is general across the supplied set, not a guaranteed
  section parser.
- **Evidence:** Visual checks covered `1409.0473v7` p.2, `1610.02357v3` p.2,
  `1703.03906v2` p.3, and `N16-1024` p.2. The batch returned 192 heading
  candidates across nine papers; per-paper counts in filename order were 23,
  33, 14, 14, 22, 19, 20, 25, and 22.
- **Limits / next:** There is no complete manually labeled heading inventory,
  so 192 is a candidate count, not measured accuracy or recall. Missed or
  false headings can affect Task 3 section labels.

## Input storage decision (September 28)

Copied the nine course PDFs into local `data/papers/` and made the notebook
and CLI use those repository-relative paths. The PDFs are ignored by Git due
to unverified redistribution terms for these exact versions; the source links
and local-file instructions are in `data/papers/README.md`. The local pipeline
reads these files directly; no Downloads path or chat attachment is needed.

## Task 3 — Paragraph candidates and manual checks (September 28–29)

**Question:** Which candidate boundaries preserve body paragraphs while
separating headings and non-prose material?

- **Attempt 1 — blank-line splitting:** Simple and readable on some prose, but
  merged whole columns/pages into a few large candidates (for example, one
  candidate on the reviewed two-column `1406.1078v3` p.5).
- **Attempt 2 — PyMuPDF layout blocks:** Preserved column-level blocks better.
  The first span-joining pass lost spaces; adding a space when x-coordinates
  showed a gap fixed examples such as words running together. Raw blocks still
  included headings, captions, equations, tables, footnotes, and figure labels.
- **Manual checks:**
  - `AttentionYouNeed.pdf` p.2: student classified 13 candidates as 9 body
    paragraphs, 3 headings, and 1 page number after clarifying candidate 2.
  - `1406.1078v3.pdf` p.5: 10 paragraphs and 3 headings. Layout blocks kept
    them separate; blank-line splitting merged the page. Candidate IDs were
    interleaved across columns, showing segmentation and reading order are
    separate issues.
  - `AttentionYouNeed.pdf` p.3: 4 paragraphs, 2 headings, 1 figure caption,
    and 1 page number. Both candidate methods preserved paragraph boundaries;
    candidate filtering was still necessary.
  - `AttentionYouNeed.pdf` p.6: table caption and table body were separate
    candidates but not paragraphs. The two formula lines form one displayed
    equation group; the following `where pos...` text is prose. Blank-line
    splitting kept the formula group together, while layout blocks split its
    two lines.
- **Filter attempts:** A span-count table rule wrongly tagged the bold
  `Encoder:`/`Decoder:` paragraphs and `where pos...` explanation as tables.
  Removed that rule. Current exclusions use visible horizontal-rule overlap
  for tables, a separate dense-numeric rule, and patterns/geometry for
  headings, captions, equations, page numbers, and short fragments. Excluded
  blocks and reasons stay in the JSON for inspection.
- **Continuation rule:** Join a block to the previous paragraph only when it
  appears visually adjacent on the same page, section, and column; starts in
  lowercase; and the previous text has no sentence-ending punctuation. This
  recovered split prose while avoiding joins across columns. Page-break
  continuations are not joined.
- **Front-matter correction:** The first batch counted title-page titles,
  authors, affiliations, and permission text as paragraphs. Updated page 1
  handling to exclude blocks before the first detected structural heading as
  `front_matter`, while keeping the abstract and later text.
- **Decision:** Use layout blocks plus auditable filters as the provisional
  paragraph-record method. Keep blank-line splitting as a comparison baseline.
- **Current output:** All nine PDFs (107 pages) produce 1,396 records:
  `1406.1078v3` 203; `1409.0473v7` 179; `1412.3555v1` 125;
  `1601.06733v7` 115; `1607.06450v1` 249; `1610.02357v3` 81;
  `1703.03906v2` 121; `AttentionYouNeed` 167; `N16-1024` 156. These are
  extracted-record counts, not a correctness rate; they supersede earlier
  iteration totals.
- **Manual score:** On the two fully labeled pages used during development,
  the code exactly matched 10/10 and 4/4 paragraph groups: TP=14, FP=0, FN=0;
  precision, recall, and F1 are each 1.00 on this small development sample.
  The partial p.6 review is not included. This is not a held-out or corpus-wide
  score.
- **Validation:** Re-generated one JSON per paper; checked required fields,
  sequential paragraph numbering, Python module compilation, notebook code
  syntax, and `git diff --check`.
- **Limits / next:** Some first-page footnotes/publication text after the
  abstract may remain; borderless tables and figure labels are ambiguous;
  paragraphs across pages are split; section errors propagate. Task 3's
  implementation is provisionally complete with these limits. Continue to
  Task 4 sentence segmentation and append new failures if later review finds
  concrete examples.

## Task 4 — Sentence segmentation (September 29)

**Question:** Which spaCy sentence-boundary option handles citations and
scientific abbreviations without splitting a paragraph at every period?

- **Attempt 1 — `text.split(".")`:** Compared it with real PDF prose. It
  breaks citations/labels such as `Devlin et al. (Devlin et al., 2014)` and
  `Eq. (9)` into fragments; a decimal or section number would also be split
  mechanically. Rejected as the sentence segmenter.
- **Attempt 2 — spaCy `sentencizer`:** Tried the rule-based component on the
  `Devlin et al.` example. It produced four fragments from two sentences,
  splitting both around `et al.` and inside the parenthetical citation.
- **Attempt 3 — trained spaCy parser:** Used `en_core_web_sm` (spaCy 3.8.16,
  model 3.8.0). It preserved the example's actual two sentence endings, but
  introduced a false boundary after `Devlin et al.`; on another paragraph it
  split the single sentence at `Eq.` before `(9)`.
- **Revision:** Keep parser boundaries and merge only when a sentence ends in
  a known abbreviation (`et al.`, `Eq.`, `Sec.`, `Fig.`, `Figs.`, `Table`, or
  `No.`) and the next span begins with `(`. This corrected both observed
  failures without overriding the other sentence boundaries in the examples.
- **Manual development sample:** In `1406.1078v3.pdf` PDF p.4, paragraph 48
  should be one sentence containing `Eq. (9)` (parser: 2; repaired: 1).
  Paragraph 56 should be two sentences; the parser returned 3 and the repair
  returned 2. The two references and expected counts are stored in
  `data/annotations/task4_manual_review.json`. Both examples match after the
  repair; this is a two-paragraph development check, not corpus-wide accuracy.
- **Batch result:** Processed all Task 3 paragraph JSONs: 3,666 sentence
  records across 1,396 paragraphs and nine papers. The narrow rule merged 16
  boundaries. Output retains paper/page/section/paragraph context and nests
  numbered sentence records in each paragraph under `outputs/sentences/`.
- **Validation:** Compiled the new module, ran the CLI on all nine inputs, and
  confirmed the two labeled paragraph counts before/after repair. Outputs are
  reproducible; they remain local and are ignored by Git.
- **Limits / next:** Two reviewed paragraphs are not enough to estimate
  segmentation accuracy. The abbreviation list can miss other false splits,
  and a rare legitimate parenthetical sentence after a listed abbreviation
  could be merged. PDF paragraph and reading-order errors also pass through.
  Keep the repair narrow and expand the manual sample before treating the
  result as reliable.

### Expanded manual review (September 29)

- **Sample:** Visually checked 20 paragraphs from all nine PDFs: the two
  development cases plus 18 varied cases with citations, equation/figure/table
  references, abbreviations, numbers, enumerations, and ordinary prose.
- **Result:** 20/20 exact boundary matches in this selected sample. All spaCy
  sentence texts also reassemble to their source paragraph after whitespace
  normalization. Paragraph IDs, expected counts, boundary notes, and review
  limits are in `data/annotations/task4_manual_review_expanded.json`.
- **Correction to the review set:** Excluded `1607.06450v1`, p.4, paragraph 37
  from sentence scoring because it ends with “Then we have,” before a displayed
  equation. It is an incomplete prose unit caused by layout segmentation.
  Replaced it with paragraph 40 on the same page, which has two complete
  prose sentences; both boundaries match.
- **Interpretation / next:** This purposive sample tests known risk patterns
  and is encouraging, but it is not random, exhaustive, or a corpus-wide
  accuracy estimate. Task 4 is provisionally complete for the pipeline; retain
  the narrow repair and move to Task 5 tokenization, recording new failures if
  later tasks expose them.

## Task 5 — Tokenization and linguistic annotations (September 29)

**Question:** Does spaCy's default tokenization keep scientific notation
readable, and should tags be assigned in the paragraph or the corrected
sentence context?

- **Attempt 1 — spaCy English defaults:** Token boundaries for decimals and
  spaced citations looked useful, but attached inline forms such as `p(xt)`
  and `f(Wx` stayed partly joined. A scan of the 3,666 sentence records found
  138 word-plus-parenthesis tokens of this kind.
- **Attempt 2 — split only before `(`:** This separated `f` from its opening
  parenthesis but left forms such as `(Wx` joined. It was incomplete, so it was
  not retained.
- **Attempt 3 — two Unicode-aware spaCy infix rules:** Split at both letter/`(`
  and `(`/letter joins, keeping spaCy's default English rules. Examples now
  tokenize as `p ( xt )`, `f ( Wx + b )`, and `NT ( X )`. On the current corpus,
  total tokens rise from 60,401 to 60,748; 130 of 3,666 sentences change.
  Sample citations, decimals (`2.0`, `28.4`), and already spaced prose retained
  their default boundaries. This is a corpus-wide count comparison plus spot
  inspection, not a tokenization gold-standard score.
- **Context experiment:** Re-parsing full paragraphs can reintroduce sentence
  boundaries that Task 4 manually repaired and makes sentence-to-token mapping
  harder. We therefore parse each corrected Task 4 sentence independently.
  This can change POS/dependency predictions compared with paragraph-context
  parsing, so the model's syntactic labels remain provisional.
- **Output:** Generated nine local token JSON files, 3,666 sentences and
  60,748 spaCy tokens. Each token stores its original text, following
  whitespace, zero-based sentence-local index, lemma, coarse POS, dependency,
  head text, and head index. Punctuation is retained. Task 7 can reuse the
  head information.
- **Limit / next:** Mathematical symbols can receive unhelpful English POS and
  dependency labels even when their token boundaries improve; inline equations
  such as `x_i` remain model-tokenized units. The model is not manually
  correcting scientific notation. Task 5 is provisionally complete; next
  calculate per-paper POS statistics for Task 6 and keep checking annotation
  quality on representative sentences.

## Task 6 — Part-of-speech statistics (September 29)

**Question:** How can we compare spaCy POS distributions across papers of
different lengths without hiding the counting choices?

- **Attempt 1 — raw counts only:** Counts are required and useful for auditing,
  but longer papers naturally accumulate more tokens, so counts alone do not
  support a fair comparison. Kept counts and added normalized percentages.
- **Attempt 2 — percentage of every token:** Punctuation is a spaCy token but
  does not belong to the nine requested lexical POS categories. In
  `AttentionYouNeed`, punctuation is 16.48% of all tokens; using every token as
  the denominator reduces NOUN from 26.48% to 22.12%. Use non-punctuation tokens
  as the POS denominator instead, while retaining punctuation and total-token
  counts as separate fields.
- **Aggregation:** Count the required nine POS tags, group remaining
  non-punctuation tags (such as AUX, CCONJ, PART, SYM, and X) as `OTHER`, and
  report counts plus percentages. The CSV and JSON definition records state
  the denominator explicitly.
- **Batch output:** Processed all nine Task 5 JSON files: 60,748 total tokens,
  of which 10,291 were punctuation; POS percentages therefore use 50,457
  non-punctuation tokens. Wrote combined local CSV and JSON under
  `outputs/statistics/`.
- **Three-paper comparison:** `AttentionYouNeed` has NOUN 26.48%, NUM 6.12%,
  PROPN 13.02%; `N16-1024` has NOUN 25.45%, NUM 4.12%, PROPN 18.48%; and
  `1607.06450v1` has NOUN 26.78%, NUM 4.25%, PROPN 14.43%. This shows different
  observed distributions, not why they differ.
- **Limit / next:** Scientific notation contributes tokens that spaCy may label
  as PROPN, NUM, or SYM; references also contain many names and numbers.
  `OTHER` hides its internal tag mix in the compact table. POS percentages are
  descriptive outputs, not a manual linguistic gold standard. Task 6 is
  provisionally complete; continue to Task 7 dependency examples and
  visualizations, with the same model-label caveats.

## Task 7 — Dependency parsing and visualization (September 29)

- **Sample design:** Selected 10 sentences from 10 distinct sections across
  all nine papers. Each example records its paper, page, section, paragraph,
  and sentence location so it can be traced to the source and reproduced.
- **Output:** Reused Task 5's spaCy token annotations to create a 223-row token
  table with token, lemma, POS, dependency label, and syntactic head. The
  manifest, JSON sample, and CSV are generated by one command; three selected
  cases also have standalone displaCy HTML diagrams.
- **Structure review:** The diagrams illustrate a passive training-objective
  sentence, a relative clause in *The Machine Reader*, and a reported-results
  list. The coordinated list is attached imperfectly by the model; its output
  is shown as a prediction rather than corrected to a gold parse.
- **Checks:** The generator found all 10 source sentences in their recorded
  locations, preserved the Task 5 token boundaries for each diagram, and
  produced the required columns and all three SVG diagrams. Fixed duplicate
  HTML body styling discovered during output inspection. Module compilation
  and `git diff --check` passed.
- **Automated test attempt:** Added five focused `unittest` checks for exact
  location/section lookup, the 10-section minimum, unique sample IDs, CSV/JSON
  fields, three HTML diagrams, and tokenizer mismatch rejection. The first
  run exposed a fixture bug: two examples from one paper caused the fixture to
  overwrite one paragraph. Preserving both fixture paragraphs fixed it; all
  five tests then passed. A rerun on the real Task 7 data produced 10 examples,
  10 sections, 223 token rows, and three diagrams.
- **Limit / next:** This checks reproducibility and output shape, not dependency
  accuracy: no gold dependency trees were manually annotated. Technical
  notation, PDF hyphenation (including `Tensor- Flow`), and long coordinated
  lists can lead to poor POS or attachment decisions. Explain three parses
  with those caveats, then move to Task 8 document statistics and final JSON.

## Task 8 — Document statistics (September 29)

- **Definition choice:** Kept total spaCy token counts inclusive of punctuation
  to stay consistent with Task 5. For average sentence/paragraph length and
  unique token types, excluded `PUNCT`; casefolded surface forms so `Model` and
  `model` count as one type. The JSON records these choices.
- **Compared alternatives:** In `AttentionYouNeed`, average sentence length is
  16.08 tokens when punctuation is included and 13.43 when excluded. Its
  unique non-punctuation types are 1,582 with case-sensitive surfaces and
  1,491 after casefolding. The detector reports 25 section candidates, while
  paragraph records cover 24 distinct section labels. Kept the explicit
  casefolded/non-punctuation definition and the detector's candidate count;
  the alternate values show why the table must document its counting rules.
- **Section-count choice:** Reported the Task 2 detector's section candidates
  from inherited metadata. These counts are not treated as verified headings.
- **Output:** Processed the nine Task 5 JSON files and wrote combined CSV/JSON
  under `outputs/statistics/`. Aggregate counts: 107 pages, 192 detected
  section candidates, 1,396 paragraph records, 3,666 sentences, and 60,748
  spaCy tokens (including punctuation). Per-paper averages and unique-type
  counts are in the tables.
- **Consistency check:** Confirmed nine paper rows and reconciled the totals
  against nested records and inherited metadata for paragraphs, sentences, and
  tokens. The module now stops on those metadata/count mismatches instead of
  silently producing a misleading table. Source compilation, notebook JSON
  parsing, and `git diff --check` also succeeded.
- **Automated checks:** Added five `unittest` cases for punctuation handling,
  casefolded unique types, zero-sentence documents, section metadata fallback,
  metadata/count mismatches, and CSV/JSON export. All five passed. The tests
  verify calculation behavior; they do not validate upstream PDF extraction
  or whether detected headings are correct.
- **Limit / next:** Statistics inherit errors from PDF extraction, section,
  paragraph, sentence, token, and POS stages. A casefolded surface type is not
  a lemma; unique counts can differ if hyphenation or tokenization changes.
  This completes Task 8 provisionally. Next build Homework 2-ready JSON files
  (Task 9) and ensure the README and report explain these limitations.

## Task 9 — Final nested JSON representation (September 30)

- **Attempt 1 — reuse Task 5 JSON unchanged:** It preserves every annotation,
  but its top level is a flat paragraph list with section labels on paragraphs;
  that does not match the requested `sections → paragraphs → sentences →
  tokens` structure. Kept it as the reproducible source input, not the final
  deliverable format.
- **Attempt 2 — group by first-seen `(section_id, title)`:** Built one ordered
  section object per populated heading, retaining paragraph IDs, page numbers,
  paragraph text, sentence IDs/text, token indices and whitespace, lemmas,
  POS, dependency labels, and syntactic heads. Added Task 8 statistics and an
  explicit note that empty/unassigned heading candidates are not serialized.
- **Comparison:** Across the corpus, Task 2 reports 192 section candidates,
  while Task 9 has 176 distinct section groups containing paragraphs. For
  example, `AttentionYouNeed` has 25 detected candidates and 24 populated
  groups. These values answer different questions; the output reports both
  rather than dropping or inventing empty paragraph groups.
- **Output:** Generated nine files under `outputs/json/`. Their nested records
  retain the same aggregate 1,396 paragraphs, 3,666 sentences, and 60,748
  tokens as Tasks 3–5. The CLI refuses metadata/count mismatches and duplicate
  paper IDs that would overwrite a file.
- **Limit / next:** These files preserve upstream decisions; they do not repair
  missed headings, paragraph segmentation, or spaCy errors. Empty sections
  without assigned paragraphs are omitted, and section grouping relies on
  Task 3 labels. Task 9 is provisionally complete. Remaining deliverables are
  the short report and a final README/notebook review; do not push until asked.

## Final notebook verification (September 30)

- Updated Task 6 display to show the required POS percentages for all nine
  papers, while retaining a detailed count/percentage comparison for three.
  Split Task 8 into two narrower tables so the nine-paper metrics fit the
  notebook view; all requested statistics remain available in the CSV/JSON.
- Ran all notebook cells from the project root with the project `.venv` kernel.
  All 19 code cells completed without errors. The run regenerated the current
  outputs for Tasks 1–9.
- Current run totals: 9 PDFs, 107 pages, 192 section candidates, 928 paragraphs,
  2,285 sentences, and 48,068 spaCy tokens. Nine final nested JSON files were
  generated. Task 7 produced 10 examples from 10 distinct sections and three
  visualizations. POS and document-statistics files each contain all nine
  papers.
- All 10 unit tests passed; `git diff --check` passed. Earlier aggregate totals
  recorded in dated Task 3–9 entries describe prior pipeline runs and are
  superseded by this final run. The current report and notebook use the totals
  above.
- **Limit:** A successful run and unit tests confirm execution and output
  structure, not gold-standard accuracy for every extracted heading, paragraph,
  sentence, or spaCy annotation. No GitHub push was made.
