# Ukrainian Frequency: the top-12,000 lemma list (datasheet)

A lemma-based, coverage-graded open frequency list for modern Ukrainian: the 12,000 most frequent lemma-and-part-of-speech rows over the UberText 2.0 lemma frequency dictionary (lang-uk), each with its raw occurrence count, its per-mille share of the word-token universe, its cumulative running-text coverage and its thousand-rank band. Current release v0.2.0, CC-BY 4.0; v0.1.0 stays published byte-identical as the predecessor version under the same concept DOI. It re-publishes derived aggregate counts, never corpus text.

## What it is

- `lemmas.csv` / `lemmas.json`: one row per (lemma, UD part of speech), rank order. Columns `rank, lemma, pos, count, permille, cumulativeCoverage, freqBand` (v0.1.0 also carries an undefined `docs` column, dropped from v0.2.0 onward).
- `lemmas.anki.tsv`: the same rows as an Anki deck seed.
- `coverage.csv` / `coverage.json`: the coverage curve, per rank checkpoint, over the filtered word-token universe of 1,495,772,089 tokens.
- `crosswalk.csv` / `crosswalk.json` (v0.2.0 onward): every v0.1.0 row once, with its fate (kept, merged or dropped) and the v0.2.0 rank it now counts toward, plus the rows that entered from below the old cut.
- `cleanup.json` (v0.2.0 onward): the reviewed ledger (111 rows plus two general rules) applied to every source row to build v0.2.0 from v0.1.0.
- `manifest.json`, `SHA256SUMS`: the release's own hashes as published on the site.
- `DATASHEET.md` (this file) and the deposit's `manifest.json` with SHA-256 per file.

## How it was built

`scripts/ukrainian-frequency/extract-source.py` in the source repository reads `ubertext_freq.csv.xz` (the lemma / POS / count dictionary built over the combined UberText 2.0 subcorpora; accessed 2026-07-14), keeps rows whose lemma is Ukrainian-Cyrillic-alphabetic and whose POS is a linguistic UD tag (X, SYM, PUNCT, numerals as digits and single-character proper nouns are excluded), recomputes coverage from the raw counts over that filtered universe, and takes the top 12,000 rows by count, ties broken by lemma then POS: that is v0.1.0. `scripts/ukrainian-frequency/build-list-v2.py` applies the reviewed cleanup ledger over every one of those source rows (case forms and tag-split compounds folded into their lemmas, mislabeled names rejoined, non-words and Russian words dropped, apostrophes normalized to U+2019) and refills the list from below the old cut: that is v0.2.0, documented in `docs/ukrainian-frequency/list-v0.2.0.md`. `scripts/ukrainian-frequency/build-release.mjs` freezes both releases with hashes; CI re-derives each byte for byte from its committed source slice, and a dedicated test holds the crosswalk to the source rows it accounts for.

## What it excludes

- Corpus text. Only counts are published.
- Lemmas with a non-linguistic tag, non-Cyrillic lemmas, numerals written as digits.
- Any level, rating or pedagogical judgment. This list is frequency only; the CEFR overlay is a separate deposit with a different license.

## Known defects

- Lemmatization is automatic (the dictionary's own) and still carries errors the v0.2.0 cleanup ledger did not reach: `рок` at rank 97 absorbs tokens of `рік` (year, rank 13); a spelling can still appear at two ranks because the tagger split it by part of speech. v0.2.0's ledger merged 111 rows the audit flagged (case forms folded into their lemmas, mislabeled names rejoined, non-words and Russian words dropped) but is not exhaustive, and names doubled as NOUN and PROPN (Янукович, Нью-Йорк) are deferred to a future v0.3.0.
- Proper nouns are included and tagged PROPN (1,348 of 12,000 in v0.2.0) so a user can filter them; they are not removed.
- The corpus is news-heavy: everyday domestic words (снідати, сметана) rank low or are absent, and the fiction/news genre split on the site shows where this matters.
- Register and dispersion beyond raw counts are not carried; a Gries-style dispersion over subcorpora needs per-subcorpus counts the dictionary does not publish.

## Intended uses

Vocabulary selection and sequencing for learners and course writers; a frequency spine for joining other lexical resources (the site joins a CEFR profile, two lexical minimums and a Wiktionary paradigm table onto it); coverage estimates for graded reading; a baseline for NLP work that needs a modern-Ukrainian lemma list with counts.

## Unintended uses

Treating rank as a proficiency level (the site's own finding is that a validated CEFR level tracks frequency only weakly, Spearman about 0.38); treating the list as a dictionary of what is correct Ukrainian (it counts what a news-heavy corpus uses, russianisms included; the derussification pass on the site flags them separately); reconstructing corpus text (not possible from counts, and not intended).

## Attribution

- UberText 2.0 lemma frequency dictionary, lang-uk. Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern Ukrainian at Scale. Proceedings of the 2nd Ukrainian NLP Workshop (UNLP), ACL. https://lang.org.ua/en/ubertext/ CC-BY 4.0.
- Universal Dependencies part-of-speech scheme. https://universaldependencies.org/u/pos/

## Cite this deposit

Lawrence, J. (2026). Ukrainian Frequency: a lemma-based, coverage-graded open frequency list (v0.2.0). Zenodo. Concept DOI: see the deposit record. Derived from UberText 2.0 (Chaplynskyi, 2023). Live page: https://uavocab.org/research. Python: `pip install uavocab` (https://pypi.org/project/uavocab/). Cite the version DOI of the release you actually used; v0.1.0 stays published for anyone citing figures taken before the v0.2.0 cleanup.

## Maintenance

Refreshed when UberText publishes a new edition, or when a reviewed cleanup pass changes the list (as v0.2.0 did, over the same 2023-04-03 source file); each refresh is a new version under the same concept DOI, and every prior version stays published rather than being replaced. The version DOI is the one to cite for a reproducible figure.
