# Homework 1 — Scientific Paper Processing with spaCy

## 1. Introduction

In this assignment, I built a Python pipeline that converts scientific papers
from PDF files into structured linguistic data. The pipeline processes all nine
supplied papers — *Attention Is All You Need* and eight papers it cites — using
the same code. The stages are: PDF text extraction, section detection, paragraph
detection, sentence segmentation, tokenization with linguistic annotation,
POS statistics, dependency parsing, document statistics, and nested JSON output.

The work was iterative: I compared alternative methods on specific pages,
recorded what worked and what failed, and adjusted the rules based on evidence.
The experiment log (`notes/experiment_log.md`) documents each decision and its
rationale. Where manual checks were performed, I state the sample size and
limitations; candidate counts are not presented as accuracy scores.

## 2. PDF Text Extraction

I used **PyMuPDF** to extract text page by page with `page.get_text("text",
sort=True)`. The `sort=True` parameter reorders text blocks by their position
on the page, which improves reading order on single-column pages but can still
mix columns on two-column layouts. I compared sorted and unsorted extraction on
seven pages from three papers, covering single-column prose, a title page,
two-column pages, tables, figures, and equations. I also prototyped a
column-grouping method that improved one figure page but split equations.

**Decision:** Keep sorted extraction as the reproducible default and expose
`--preserve-pdf-order` for comparison.

**Current output:** 107 pages, 465,733 characters, and 57,726 words across
nine PDFs.

### PDF Extraction Problems

At least five significant problems occur when extracting scientific papers
from PDF:

1. **Two-column layouts:** Text blocks from the left and right columns can be
   interleaved. On a reviewed two-column page of `1406.1078v3.pdf`, the sorted
   extractor mixed paragraphs from both columns.

2. **Mathematical equations:** Expressions like
   `Attention(Q, K, V) = softmax(QK^T / √d_k)V` lose their spatial structure
   and become fragmented Unicode characters. Subscripts and operators appear as
   isolated symbols without mathematical meaning.

3. **Headers and footers:** Running headers (conference name, paper title) and
   page numbers appear mixed into the body text between paragraphs.

4. **Hyphenation at line breaks:** Words split across lines (e.g.,
   `"atten-\ntion"`) are not automatically rejoined, producing incomplete
   tokens.

5. **Tables:** Table structure is lost: cell contents are concatenated into
   lines of text, making it impossible to reconstruct rows and columns. A
   results table may appear as `"28.4 3.5 days 8 GPUs"` without headers.

Additional issues include figure captions appearing mid-text, footnotes mixed
with body prose, and Unicode ligatures being decomposed or lost.

## 3. Section Detection

I developed the section detector iteratively:

- **Attempt 1 (regex only):** A numbered-line regex found many real headings but
  also matched years, affiliations, footnotes, equations, and figure labels.
- **Attempt 2 (typography-aware):** Combined numbering patterns with bold/medium
  font detection and larger-than-body font size checks. This reduced false
  positives but missed same-size small-caps headings.
- **Attempt 3 (small-caps + appendix):** Added a short uppercase fallback and
  lettered appendix IDs. A broad letter pattern initially misclassified equation
  labels; I narrowed the rule and required styling evidence for single-letter
  appendix headings.

**Current output:** 192 heading candidates across nine papers. Visual review
covered selected pages from four papers. Since there is no complete manually
labeled heading inventory, 192 is a candidate count rather than a precision or
recall score.

## 4. Paragraph Detection

I compared two candidate-generation methods:

- **Blank-line splitting** was simple but merged entire columns into single
  candidates on two-column pages.
- **PyMuPDF layout blocks** preserved column-level boundaries better. Raw blocks
  included headings, captions, equations, tables, and footnotes, so I added
  auditable filters for each type.

**How paragraph boundaries are determined:** Each PDF text block becomes a
candidate. The pipeline then: (1) excludes recognized headings, (2) filters
captions, equations, tables, page numbers, and short fragments, (3) excludes
front-matter blocks on page 1, (4) excludes footer/footnotes by font size,
(5) merges visually adjacent blocks when the previous text lacks sentence-ending
punctuation and the next starts with a lowercase letter, and (6) excludes
References and Acknowledgments sections. Excluded blocks and their reasons are
retained in the output for inspection.

**Manual review:** On two fully labeled development pages, the method matched
14/14 paragraph groups exactly. This is a small development sample, not
corpus-wide accuracy. The current run produces 928 paragraph records.

## 5. Sentence Segmentation

### Why `text.split(".")` Is Inadequate

`text.split(".")` treats every period as a sentence boundary. This fails in
scientific text in at least five ways:

1. **Abbreviations:** `"Vaswani et al. proposed..."` splits after `"al"`,
   breaking a citation pattern into two fragments.
2. **Decimal numbers:** `"achieves 28.4 BLEU"` produces `"achieves 28"` and
   `"4 BLEU"` — meaningless fragments.
3. **Section references:** `"See Sec. 3.2 for details"` contains three periods,
   none of which is a sentence boundary.
4. **Parenthetical citations:** `"(Devlin et al., 2014)"` would split inside
   the parentheses.
5. **Equations:** `"We compute Eq. (1) where d_k = 64."` splits after `"Eq"`
   rather than at the actual sentence end.

### Our Approach

I compared three methods: `text.split(".")` (rejected), spaCy's rule-based
sentencizer (split `"et al."` and citations into fragments), and the trained
English parser from `en_core_web_sm`. The trained parser handled most cases
correctly but introduced false boundaries after abbreviations like `"Eq."` when
followed by parentheses. I added a narrow repair rule that joins adjacent
sentence spans when the first ends in a known abbreviation (`et al.`, `Eq.`,
`Sec.`, `Fig.`, `Figs.`, `Table`, `No.`) and the next starts with `(`.

**Current output:** 2,285 sentence records across nine papers. A visual review
of three current paragraphs (citation-rich prose, decimal-containing text, and
technical notation) matched expected sentence endings in all cases.

## 6. Tokenization

spaCy's default English tokenizer generally handled ordinary text well, but
inline formula forms like `p(xt)` and `f(Wx` remained partially joined. I
added two Unicode-aware infix rules that split at letter-parenthesis boundaries
on both sides, while retaining all other English tokenization rules. This
produced cleaner token boundaries around mathematical notation (e.g.,
`p ( xt )`) without affecting citations, decimals, or regular prose.

Each corrected Task 4 sentence is parsed independently to keep the manual
sentence repairs intact. Token records include: text, zero-based index, lemma,
coarse POS, dependency label, syntactic head text, and head index.

**Current output:** 48,068 tokens across nine papers.

## 7. POS Tagging

POS percentages use non-punctuation tokens as the denominator (punctuation
is excluded from the nine required categories; 7,085 punctuation tokens across
the corpus). The nine required categories plus an `OTHER` group for remaining
tags (AUX, CCONJ, PART, SYM, X) are reported.

### Three-Paper Comparison

| POS   | AttentionYouNeed | N16-1024 | 1607.06450v1 |
|-------|:---:|:---:|:---:|
| NOUN  | 29.08% | 27.44% | 27.93% |
| VERB  | 10.58% | 10.86% | 10.54% |
| ADJ   | 8.74%  | 7.17%  | 7.87%  |
| ADV   | 3.63%  | 3.71%  | 3.33%  |
| PROPN | 5.08%  | 11.80% | 8.33%  |
| PRON  | 2.28%  | 2.43%  | 2.59%  |
| DET   | 9.33%  | 8.71%  | 9.00%  |
| ADP   | 11.19% | 10.52% | 10.59% |
| NUM   | 5.72%  | 3.89%  | 4.25%  |

**Observations:** NOUN is the most frequent category in all three papers
(~27–29%), reflecting noun-heavy scientific prose. PROPN varies significantly:
`N16-1024` has the highest share because it discusses many named systems and
benchmarks. NUM is highest in `AttentionYouNeed` due to its extensive results
tables. VERB proportions (~10–11%) are lower than general English, as scientific
writing favors nominal constructions.

## 8. Dependency Parsing

I selected 10 sentences from 10 distinct sections across all nine papers.
For each sentence, the token table shows: token, lemma, POS, dependency label,
and syntactic head. Three sentences were visualized with displaCy:

1. **Passive training objective** (`1406.1078v3`, Abstract): `"trained"` is the
   ROOT. The encoder and decoder are coordinated passive subjects
   (`nsubjpass`), joined by `"and"`. The infinitive `"maximize"` functions as
   a purpose complement (`xcomp`), and `"probability"` is its direct object.

2. **Relative clause** (`1601.06733v7`, The Machine Reader): `"present"` is the
   ROOT with `"we"` as subject and `"reader"` as object. The relative clause
   `"which is designed to..."` modifies `"reader"` — `"which"` is the passive
   subject of `"designed"`, and `"process"` is an open clausal complement.

3. **Coordinated measures** (`1703.03906v2`, Introduction): `"report"` is the
   ROOT. Four reported measures form a coordinated list. spaCy attaches list
   items imperfectly — a known limitation with long coordinated structures.

These parses are model predictions, not gold-standard annotations. Technical
notation, PDF-split words, and long coordinated lists can lead to incorrect
POS or attachment decisions.

## 9. Document Statistics

| Paper | Pages | Sections | Paragraphs | Sentences | Tokens | Unique Tokens | Avg Sent Len | Avg Para Len |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1406.1078v3 | 15 | 23 | 152 | 328 | 6,670 | 1,132 | 17.19 | 37.10 |
| 1409.0473v7 | 15 | 33 | 119 | 276 | 6,659 | 1,135 | 20.28 | 47.04 |
| 1412.3555v1 | 9 | 14 | 86 | 185 | 3,512 | 708 | 16.06 | 34.55 |
| 1601.06733v7 | 11 | 14 | 82 | 250 | 5,746 | 1,237 | 19.48 | 59.40 |
| 1607.06450v1 | 14 | 22 | 131 | 330 | 5,996 | 1,142 | 16.01 | 40.32 |
| 1610.02357v3 | 8 | 19 | 68 | 186 | 3,962 | 839 | 18.86 | 51.59 |
| 1703.03906v2 | 9 | 20 | 78 | 196 | 4,476 | 1,030 | 19.74 | 49.60 |
| AttentionYouNeed | 15 | 25 | 85 | 233 | 4,895 | 1,075 | 18.08 | 49.56 |
| N16-1024 | 11 | 22 | 127 | 301 | 6,152 | 1,120 | 16.72 | 39.62 |
| **TOTAL** | **107** | **192** | **928** | **2,285** | **48,068** | — | — | — |

*Notes:* Tokens include punctuation. Unique tokens are case-folded surface forms excluding
punctuation. Average lengths count non-punctuation tokens. Sections are detector
candidates, not manually verified headings.

## 10. JSON Output

The final output is one nested JSON file per paper:

```
Paper
  → Section (section_id, title)
    → Paragraph (paragraph_id, page, text)
      → Sentence (sentence_id, text)
        → Token (text, token_index, lemma, pos, dependency, head)
```

The nine JSON files retain 928 paragraphs, 2,285 sentences, and 48,068 tokens.
The section detector found 192 candidates, while 157 section groups contain at
least one paragraph. These counts differ because heading candidates with no
assigned body paragraphs are not emitted as empty sections.

## 11. Problems and Limitations

The pipeline has several known limitations that propagate through stages:

- **Extraction errors:** Incorrect reading order on two-column pages can split
  or merge paragraphs incorrectly.
- **Heading detection:** Without a ground-truth heading list, false positives
  and missed headings affect section labels for downstream paragraphs.
- **Paragraph boundaries:** Borderless tables, figure labels, and equations
  adjacent to prose can be retained as paragraph candidates.
- **Cross-page paragraphs:** Paragraphs that continue across page breaks
  remain split into separate records.
- **Sentence segmentation:** The abbreviation repair is narrow and may miss
  other false splits; a legitimate parenthetical sentence after an abbreviation
  could be incorrectly merged.
- **Tokenization:** Mathematical symbols receive English POS and dependency
  labels that are not linguistically meaningful.
- **Model limitations:** All linguistic annotations are from `en_core_web_sm`,
  a small model. No manual gold-standard annotations were prepared, so accuracy
  cannot be measured precisely.

Despite these limitations, the pipeline produces a working, reproducible
transformation from PDF to structured linguistic data for all nine supplied
papers.

## 12. Conclusion

The pipeline processes all nine supplied PDFs with the same code and produces
page-based text, structural records, spaCy annotations, statistics, and nested
JSON files. Comparing methods on actual pages helped identify cases where simple
rules were insufficient, especially for columns, headings, citations, and
inline notation. The manual checks support the specific reviewed examples, while
broader accuracy remains uncertain. The experiment log preserves these decisions
so the results can be reviewed and improved in future work.
