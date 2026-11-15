# Validated CEFR overlay source (thread 02, PULS)

`puls-cefr.raw.csv` is the committed source snapshot; `puls-cefr.json` (and the
generated `src/lib/ukrainian-frequency/puls-cefr.data.mjs` plus the public
`public/downloads/ukrainian-frequency/validated-cefr/lemmas.csv`) is the DERIVED
join onto thread 01's frequency list. None of these is a source corpus.

## What it is

The **validated** per-lemma CEFR overlay on the thread-01 frequency list. For each
of the top-12,000 lemmas that also appears in the Ukrainian Vocabulary Profile
(the PULS platform), it records the validated CEFR level, A1 to C1. This is the
headline of thread 02: 6,391 of the 12,000 lemmas carry a validated level.

## Why it exists (and why it changed)

Thread 02 used to say the one corpus-validated CEFR profile for Ukrainian
(Synchak, Starko, Burak, Svystun; eLex 2025) was browse-only and could not be
joined onto our list, so it PROFILED that resource and fell back to an open but
UNVALIDATED course overlay (`cefr-overlay.json`) for the joinable signal. That
finding is now obsolete: **Vasyl Starko, a co-author, granted explicit permission
to redistribute the per-lemma A1 to C1 levels, attributed**, and pointed us at the
public browse interface. So the validated map is now the headline overlay, and the
open course overlay stays as a measured cross-check.

## How the snapshot was taken

`scripts/ukrainian-frequency/scrape-puls-cefr.py` paginated the public
`puls.peremova.org/entries` interface (robots.txt allows `/entries`; only
`/account/` is disallowed) with a polite delay and a self-identifying user agent,
one 50-entry results page at a time, and wrote every published entry verbatim to
`puls-cefr.raw.csv` (lexeme id, meaning id, lemma, CEFR level, Ukrainian POS,
entry type). 10,298 rows across all 208 pages, harvested 2026-07-23.

## The join

`scripts/ukrainian-frequency/extract-puls-cefr-overlay.py` collapses the raw
snapshot to a per-lemma level and joins it onto the seed:

- **Per-lemma onset level.** A lemma can carry several senses at several levels;
  its level is the LOWEST (earliest onset of use), matching how the profile is
  built. Every raw sense is kept in the snapshot; the collapse is explicit.
- **POS-aware.** A PULS entry only matches our lemma when their parts of speech
  agree (Ukrainian POS mapped to the same coarse family as the seed's UD tag), so
  an unrelated homograph is dropped (47 of them), never mislabeled.
- **Cross-tag rules (since 2026-09-13).** The seed's UD tagger and the profile's
  Ukrainian labels draw some lines in different places, and until this date the
  family match alone dropped 107 rows that are the same lexeme under two
  conventions, not homographs: UD determiners that PULS calls pronouns (який,
  цей, той, мій at ranks 12, 19, 35 and 185; 33 rows), ordinals and quantifiers
  that are adjectives or determiners in UD and numerals in PULS (перший, другий,
  один, кілька; 17), the profile's indeclinable-word class (можна, треба, варто,
  шкода; 8, matched whatever the corpus tagged them), preposition-adverb words
  (довкола, позаду; 10), particle-adverb and particle-conjunction words (ще,
  щоб, хоч, тобто; 16), and substantivized adjectives (військовий, дорослий,
  старий; 23). Ten rules in those six groups recover them; every row records
  how it joined in a `join` field (`pos-family`, `lemma-only`, or
  `cross-tag:<UD tag>-><PULS label>`), also a column of the public CSV, so a
  reader can filter the recovered rows back out. The family match always takes
  precedence. One consequence is stated as a number: the overlay carries 132
  spellings at two ranks, because the seed's tagger split one word into two
  readings (i as conjunction and particle, старий as adjective and noun); each
  row keeps its own rank and POS. The rules and their reasons are the
  `crossTag` block of `puls-cefr.json`.
- **Apostrophes are decoded and folded.** The platform renders the apostrophe
  as the HTML entity `&#39;` and the harvest kept that text verbatim
  (`ім&#39;я`, 125 rows), while the list writes U+2019. Until 2026-09-13 the
  join compared the raw strings, so no apostrophe lemma ever matched: 77 list
  lemmas with a validated level (сім'я, п'ять, здоров'я, з'явитися among them)
  sat in the unlabeled set and received model predictions instead. The join
  now decodes entities and folds U+2019 / U+02BC / U+0027 to one key. The raw
  snapshot is left as harvested; the decode is the join's.
- **No heuristic, no override.** Every level here IS the validated one, so every
  label's confidence is `validated`. The rigor layer is coverage, level-vs-
  frequency coherence, and a direct cross-check of the free open overlay against
  this validated map.

## The rank distribution (B1 extension, stage 2)

The same script also writes a `rankDistribution` block (into `puls-cefr.json`
and the browser tier) and the public `rank-distribution.csv`: per validated
level, the rank quantiles (p10 to p90, linear interpolation, rounded half-up)
and the per-thousand-band counts; what the draft B1 plan's hardcoded 2000 to
4500 rank band would have kept, per level; and the shallowest and deepest
validated-B1 content words (NOUN / VERB / ADJ / ADV only, so the reader sees
vocabulary rather than particles). This is stage 2 of the B1 extension
(`docs/ukrainian-frequency/b1-extension-pipeline.md`): it replaced the band
filter with a measurement. CI re-derives every figure from `rows`.

## Source, license, permission

- **Source:** the [Ukrainian Vocabulary Profile / PULS](https://puls.peremova.org/)
  (Synchak, Starko, Burak, Svystun), the only corpus-based, expert-validated CEFR
  vocabulary profile for Ukrainian. Paper:
  [eLex 2025](https://elex.link/elex2025/wp-content/uploads/eLex2025-29-Synchak_etal.pdf).
- **Permission:** the per-lemma levels are the authors' work, redistributed here
  **with their explicit permission** (V. Starko, 2026-07), attribution required.
  Only the factual lemma-to-level assignment for lemmas already on thread 01's
  list is redistributed; never definitions, examples, guidewords, or the browse
  interface's other content.
- **License:** these derived artifacts are licensed **CC-BY-NC-SA 4.0**, the
  license the authors decided on (O. Synchak, by email, 2026-09-24; the notice is
  to follow on puls.peremova.org). Until then they were marked CC-BY-SA 4.0 to
  match the paper, on the promise to change it if asked; every artifact that
  carries a PULS level was relabeled the same day (the record and the two
  decisions it forced are in `docs/ukrainian-frequency/puls-correspondence.md`).
  `META` in the extractor carries the license and the citation; the download
  README and the datasheets repeat them.
- **Citation:** the authors' own form, as puls.peremova.org posts it:
  "Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026".
- **Export:** machine-readable export is permitted for non-commercial use only;
  an access code is to follow, which retires the scrape for future snapshots.

## Honesty limits (all surfaced on the page)

- **A dated snapshot, not the final map.** Starko noted the profile "is not the
  final version; there will be changes." Everything carries `snapshot: 2026-07-23`
  and the page presents it as a snapshot, never as final.
- **Covers about half the list.** 6,391 of 12,000; the rest carry no validated
  level (the open overlay still labels some of them).
- **The published map exceeds the paper.** The platform now lists far more B2/C1
  lemmas than the eLex 2025 tables report (the profile has grown since), which is
  the reason to join the live list, not the paper's frozen counts.

## Reproduce

Not run in the build or CI. To refresh:

```bash
python3 scripts/ukrainian-frequency/scrape-puls-cefr.py          # re-harvest the snapshot
python3 scripts/ukrainian-frequency/extract-puls-cefr-overlay.py # re-join onto thread 01
```

Then rebuild everything that reads the overlay, in this order, each from its
committed snapshot (no dump or corpus needed unless noted):

```bash
python3 scripts/ukrainian-frequency/extract-borodin-a1.py
python3 scripts/ukrainian-frequency/extract-borodin-a2.py
python3 scripts/ukrainian-frequency/extract-wiktionary-families.py --relabel   # levels beside list members; the graph needs the kaikki dump
python3 scripts/ukrainian-frequency/extract-b1-aspect.py
python3 scripts/ukrainian-frequency/extract-b1-usage.py --recheck-lemmatizer   # pymorphy3; the corpus slice stays as cut, the convention check follows the B1 set
python3 scripts/ukrainian-frequency/gapfill-model.py                           # numpy; about six minutes
node scripts/ukrainian-frequency/build-profiler.mjs
node scripts/ukrainian-frequency/build-minimums.mjs
node scripts/ukrainian-frequency/build-release.mjs
```

Then commit the regenerated artifacts and prepend a `refreshLog` entry. CI
re-verifies them against each other and thread 01 (`__tests__/cefr.test.js`),
never against the live PULS platform.
