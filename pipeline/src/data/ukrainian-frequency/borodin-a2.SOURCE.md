# borodin-a2.raw.json + borodin-a2.json : source and reproduction

## What this is

The **"1000 i 1 slovo" A2 lexical minimum for Ukrainian as a foreign language**
(Borodin, K. and Lazarenko, O., Europa-Universitat Viadrina Frankfurt (Oder),
2026), the A2 volume of the series whose A1 volume thread 02 already carries.

- `borodin-a2.raw.json` is the committed source snapshot: the 1,000 entries of
  the published alphabetical register in the authors' order, plus their grammar
  notes, plus the book's own thematic dictionary (51 topic headings, 1,124
  units). Entries are the published entry text: a single word, an aspect pair,
  a masculine/feminine pair, a spelling variant set, or a phrase, with the
  authors' stress marks kept.
- `borodin-a2.json` is the extractor's committed full table: every entry parsed
  into candidate headwords and joined against the thread-01 top-12,000 frequency
  list, plus the per-theme joins and the aggregates the page renders.

## Provenance (why we can republish this)

Published **open access under CC-BY-4.0** on 2026-05-08, so the factual word
list may be extracted and republished with attribution. No permission was needed
and none was sought; this is what the license is for.

- Publication DOI: https://doi.org/10.11584/opus4-1448
- URN: `urn:nbn:de:kobv:521-opus4-14485`
- License: CC-BY-4.0 (the publication's own license; attribution required)
- Pointed at by co-author K. Borodin, 2026-07-28, in the same correspondence
  that produced the A1 snapshot
- 108 pages; the OPUS metadata record is quoted in `borodin_2026` in
  `src/lib/ukrainian-frequency/dataset.mjs`

The A1 snapshot's provenance note recorded the open seam plainly: *"The A2
volume exists but has not been shared machine-readable."* This closes it, and
that note has been corrected.

The authors' **methodology** for both volumes is published separately (Borodin
and Lazarenko, in *New Directions in Slavic Studies*, Editorial Universidad de
Granada, 2026, pp. 41-52) and is cited as `borodin_granaslavic_2026`. That
volume is all rights reserved, so it is cited and never redistributed here. It
is the source behind the `validated: false` flag the census puts on both Borodin
rows: selection mixes GRAK and Ukrainian Web 2022 corpus frequency with
usefulness at the learning stage, which is a documented expert method, not a
corpus-validated CEFR profile.

## Reproduce

The A1 volume reached us as a spreadsheet, so its snapshot is that column
verbatim. The A2 volume is a typeset book, so the machine-readable list has to be
recovered from the typesetting. That is a real step and it is scripted, not
asserted:

```
# 1. fetch the PDF from the DOI above (2.3 MB, not vendored in this repo)
python3 -m pip install pdfminer.six
python3 scripts/ukrainian-frequency/parse-borodin-a2-pdf.py Borodin_Lazarenko.pdf

# 2. join it onto thread 01 and write the browser tier + downloads
python3 scripts/ukrainian-frequency/extract-borodin-a2.py
```

Step 1 writes `borodin-a2.raw.json`. Step 2 reads it plus
`ubertext-lemmas-top12k.json` + `puls-cefr.json` + `cefr-overlay.json` +
`borodin-a1.raw.json` and rewrites `borodin-a2.json`,
`src/lib/ukrainian-frequency/borodin-a2.data.mjs`, and
`public/downloads/ukrainian-frequency/borodin-a2/` (lemmas.csv + themes.csv +
README.md). Both are deterministic; documented, not run in the build or CI (same
posture as the other thread-02 extractors).

### What the PDF step had to decide, and how it was checked

The book sets the register in two columns (headword and grammar left, usage
example right) and marks stress with combining acutes that the fonts sometimes
advance across. Three decisions carry the extraction, each verifiable:

1. **Lines are rebuilt from glyph geometry**, not from pdfminer's word-margin
   output, which inserts phantom spaces inside stressed words
   (`безлакто зний`). Gaps are measured only between glyphs that have width.
2. **Entry boundaries are vertical.** Measured across the whole register the
   leading is cleanly bimodal: lines that continue an entry sit at dy <= 14,
   entries open at dy >= 20, and nothing at all lands between. The threshold is
   17, the middle of that empty band.
3. **Only the left column is read.** The usage examples are the authors' prose
   and stay in the book.

The result is **exactly 1,000 register entries**, which is the size the book's
own title claims, and that is asserted as a live check on the page rather than
left as a coincidence.

As a second, independent check, every unit of the thematic dictionary is matched
back against the register's headwords: **1,122 of 1,124 resolve**, and both
residuals are the same explainable phenomenon, not an extraction fault. The
thematic index sometimes prints a different aspect or reflexive form than the
register does:

| Thematic index | Register |
|---|---|
| `умити(ся)` | `вмивати(ся), умивати(ся) – вмитися, умитися` |
| `голитися – поголитися` | `голити(ся) – поголити(ся)` |

That check is a guard in `cefr.test.js`, and it is deliberately STRICTER than the
extractor's own candidate matching: it must resolve the whole unit, where the
extractor would also accept a bare parenthetical fragment such as `ся`. A looser
check finds only one residual, by accepting that fragment.

Two further guards ride alongside it, both for artifact classes that would turn a
real word into a false "off-list" finding rather than into a visible error: no
register entry may mix Latin and Cyrillic inside one token, and a theme with
nothing on the frequency list must report NO median rank rather than rank 0.

## What is normalized, and what is not

- Headword text is **verbatim**, stress marks included.
- A perfective partner printed on its own `→` line is folded into the entry with
  the en dash the A1 snapshot and the book's own thematic section both use for
  aspect pairs. This is the one structural change made to the printed text.
- Grammar notes are captured per entry but kept **out** of the entry string.
- **Apostrophe variants are folded for matching only** (the book sets the
  Ukrainian apostrophe as U+02BC in some entries and U+2019 in others; the
  frequency list uses U+2019). Without this the join would report 13 entries as
  off-list that are not. Display text stays verbatim.
- **Latin lookalikes are folded for matching only.** The published PDF sets a few
  words with a Latin character standing in for the Cyrillic one: `cонцезахисний`
  and `cвятковий` both open with U+0063 LATIN SMALL LETTER C rather than U+0441,
  verified at the glyph level. The word is correct on the page and wrong only in
  the character stream, so the fold applies inside already-Cyrillic tokens only
  (`ID-картка` must stay as printed). The register itself carries no such token;
  both known cases are in the thematic index, and folding them costs one false
  off-list unit. `cонцезахисний` stays off-list after folding, correctly: it is
  genuinely absent from the top-12,000. Display text stays verbatim.

## What is redistributed

The factual entry list, the factual thematic groupings, and the factual
entry-to-frequency-rank / entry-to-CEFR-level joins computed here. No usage
examples, grammatical prose, definitions, or any other content of the published
guide is reproduced, and the PDF itself is not vendored. Attribution rides the
download README, the page, and the SOURCES ledger (`borodin_2026`).
