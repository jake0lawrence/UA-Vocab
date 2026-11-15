# The PULS CEFR overlay on the Ukrainian Frequency list (datasheet)

The per-lemma validated CEFR levels (A1 to C1) of the Ukrainian Vocabulary Profile (PULS; Synchak, Starko, Burak, Svystun, eLex 2025), joined part-of-speech-aware onto the top-12,000 Ukrainian Frequency lemma list: 6,403 of the 12,000 lemmas carry a validated level, with a per-row record of how the join matched, and the rank distribution of every level per thousand-rank band. Redistributed with the authors' permission under CC-BY-SA 4.0 as a dated snapshot of a profile that is still being extended.

## What it is

- `lemmas.csv`: columns `rank, lemma, pos, level, confidence, join`. `level` is the profile's onset level for the lexeme (the lowest across its senses); `confidence` is always `validated` (nothing here is guessed); `join` says how the row matched: `pos-family` (parts of speech agree, 6,284 rows) or `cross-tag:<UD tag>-><PULS label>` (107 rows, the same lexeme under the two tag conventions).
- `rank-distribution.csv`: one row per (level, thousand-rank band) with the count, the finding behind the site's B1 extension (every level has lemmas in every band).
- `README.md`: the site's download README.
- `DATASHEET.md` (this file) and `manifest.json` with SHA-256 per file.

## How it was built

The full published PULS list was harvested from the public browse interface (`scripts/ukrainian-frequency/scrape-puls-cefr.py`; robots.txt allows `/entries`; one 50-entry page at a time with a polite delay; 10,298 entries across all 208 pages on 2026-07-23). `extract-puls-cefr-overlay.py` decodes the apostrophe entity the platform renders, folds the apostrophe glyphs to one key, collapses each lemma to its onset level, and joins onto the frequency list where the parts of speech agree (Ukrainian POS labels mapped to the same coarse family as the seed's UD tag). Ten declared cross-tag rules in six groups recover the words the two tag conventions merely label differently (UD determiners the profile calls pronouns, ordinals it calls numerals, its indeclinable-word class, preposition-adverb and particle-adverb words, substantivized adjectives); 47 unrelated homographs are dropped, never mislabeled. CI re-derives every published aggregate from the row table.

## What it excludes

- Definitions, examples, guidewords, thematic groups, word families, or any other platform content. Only the factual lemma-to-level assignment for lemmas already on the frequency list is redistributed.
- Predicted levels. The site's gap-fill model predicts levels for the uncovered lemmas in a separate file; none of it is here, and none of it is ever merged into this table.
- The 3,803 PULS lemma strings that are not on the top-12,000 list (they appear in the crosswalk deposit, by lemma string).

## Known defects

- A dated snapshot. The profile's authors say it is not the final version; the published map already lists more B2 and C1 lemmas than the eLex 2025 tables report. The snapshot date is 2026-07-23.
- Onset, not sense. A polysemous lemma carries the level of its earliest sense; a learner meeting a later sense is not served by this number.
- The join is only as good as the corpus tagger. 132 spellings appear at two ranks because the tagger split one word into two readings; each row keeps its own rank and part of speech and the `join` column makes the recovered rows filterable.
- Coverage is about half the list (53.3 percent); the rest carries no validated level and no guess.

## Intended uses

Grading vocabulary by an expert-validated CEFR level; building level-aware known-word sets for coverage profiling; measuring how a syllabus or word list sits against a validated profile (the crosswalk deposit does this for the two Ukrainian lexical minimums); a validated label set for research on level prediction, with the caveats above.

## Unintended uses

Treating the overlay as the final PULS profile or as the authors' own publication; treating a missing level as evidence a word is advanced (it usually means the profile does not cover it yet); reading a level as a statement about a specific sense.

## Attribution

- Ukrainian Vocabulary Profile (PULS): Synchak, O., Starko, V., Burak, M., Svystun, M. https://puls.peremova.org/. Paper: Corpus-Based Vocabulary Profiling for Ukrainian: From Lexical Analysis to CEFR, eLex 2025, https://elex.link/elex2025/wp-content/uploads/eLex2025-29-Synchak_etal.pdf. Per-lemma levels redistributed with the authors' explicit permission (V. Starko, July 2026); licensed CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24), attribution required. The authors' own citation form: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.
- Frequency ranks: UberText 2.0 (lang-uk; Chaplynskyi 2023), CC-BY 4.0.

## Cite this deposit

Synchak, O., Starko, V., Burak, M. and Svystun, M. (2025), the Ukrainian Vocabulary Profile (PULS), snapshot 2026-07-23, joined onto the Ukrainian Frequency list by Lawrence, J. (2026). Zenodo. Concept DOI: see the deposit record. Live page: https://uavocab.org/research#cefr-validated

## Maintenance

The PULS snapshot is refreshed when the authors announce a revision, and at least quarterly checked against the live platform; each refresh is a new version under the same concept DOI.
