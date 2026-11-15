# borodin-a1.raw.json + borodin-a1.json : source and reproduction

## What this is

The **"1000 i 1 slovo" A1 lexical minimum for Ukrainian as a foreign language**
(Borodin, K. and Turkevych, O., Slavic Language Education 3, LANGUAGE-LAB,
Humboldt-Universitat zu Berlin), the corpus-based A1 vocabulary minimum that
thread 02's field census lists as the one independent, empirically grounded A1
guideline for Ukrainian.

- `borodin-a1.raw.json` is the committed source snapshot: the 944 entry lines of
  the authors' own machine-readable list, verbatim and in the authors' order
  (including 15 exact duplicate lines present in the file as received; the
  extractor deduplicates and counts them). Entries are the published entry text:
  a single word, an aspect pair ("розуміти – зрозуміти"), a masculine/feminine
  pair ("лікар / лікарка"), a spelling variant set ("вчора, учора"), or a phrase
  ("день народження"), sometimes with parenthetical forms or notes.
- `borodin-a1.json` is the extractor's committed full table: every unique entry,
  parsed into candidate headwords and joined against the thread-01 top-12,000
  frequency list, plus the aggregates the page renders.

## Provenance (why we can republish this)

The published guide is licensed **CC-BY-4.0** but was available only as a prose
PDF behind an anti-bot wall, so this list was "walled" in the field census and
could not be joined. On 2026-07-22 the site owner emailed the authors asking for
a machine-readable table for attributed open republication; on 2026-07-27
co-author **Kseniia Borodin** (School of Ukrainian Language and Culture,
Ukrainian Catholic University) replied with the word list as a spreadsheet
(A1.xlsx, one column, 944 lines). The snapshot is that column, verbatim.

- Publication DOI: https://doi.org/10.18452/28236
- License: CC-BY-4.0 (the publication's own license; attribution required)
- Received: 2026-07-27, by email from K. Borodin
- This snapshot is A1 only. The A2 volume ("1000 i 1 slovo. A2") was referenced
  in the same correspondence and has since been published open access under
  CC-BY-4.0 (DOI 10.11584/opus4-1448); it is extracted and joined separately.
  See `borodin-a2.SOURCE.md`.

## Reproduce

```
python3 scripts/ukrainian-frequency/extract-borodin-a1.py
```

Reads `borodin-a1.raw.json` + `ubertext-lemmas-top12k.json` + `puls-cefr.json`
+ `cefr-overlay.json` and rewrites `borodin-a1.json`,
`src/lib/ukrainian-frequency/borodin-a1.data.mjs`, and
`public/downloads/ukrainian-frequency/borodin-a1/` (lemmas.csv + README.md).
Deterministic; documented, not run in build or CI (same posture as the other
thread-02 extractors). The one-time xlsx-to-JSON step is described above (column
A of the authors' spreadsheet, stripped of blank lines, order preserved).

## What is redistributed

The factual entry list (the authors' A1 lexical minimum) and the factual
entry-to-frequency-rank / entry-to-CEFR-level joins computed here. No prose,
definitions, examples, or any other content of the published guide is
reproduced. Attribution rides the download README, the page, and the SOURCES
ledger (`borodin_2023`).
