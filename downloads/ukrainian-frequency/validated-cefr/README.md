# Ukrainian Frequency: validated CEFR overlay (PULS)

`lemmas.csv` maps lemmas from the [Ukrainian Frequency](https://uavocab.org/research)
top-12,000 list to a validated CEFR level (columns: `rank,lemma,pos,level,confidence,join`).
6,403 of the 12,000 lemmas carry a level; levels reach A1 to C1. `join` says how
the row matched the profile: `pos-family` (the parts of speech agree; 6,284
rows), or `cross-tag:<UD tag>-><PULS label>` (107 rows, the same lexeme under
the two tag conventions, for instance UD determiners the profile calls
pronouns, ordinals it calls numerals, and its indeclinable-word class); filter
on the column to keep only the strict join.

`rank-distribution.csv` is the same table aggregated: one row per (level,
thousand-rank band) with columns `level,band,rank_from,rank_to,count`. It is the
finding behind the B1 extension: every validated level has lemmas in every one
of the twelve bands, and a 2,000 to 4,500 rank band would keep under a third of
validated B1 while admitting more B2 than B1, so a rank band is not a level.

## This is the corpus-validated profile, redistributed with permission

The levels come from the [Ukrainian Vocabulary Profile (PULS)](https://puls.peremova.org/)
by Synchak, Starko, Burak and Svystun ([eLex 2025](https://elex.link/elex2025/wp-content/uploads/eLex2025-29-Synchak_etal.pdf)),
the only corpus-based, expert-validated CEFR vocabulary profile for Ukrainian. A
co-author, Vasyl Starko, granted explicit permission to redistribute the per-lemma
A1 to C1 levels. Each lemma's level is its onset level (the lowest across its
senses); the join onto our list is POS-aware, so unrelated homographs are
dropped rather than mislabeled, and ten explicit cross-tag rules (recorded per
row in `join`) recover the words the two tag sets merely label differently.
A spelling can appear at two ranks where the corpus tagger split one word
into two readings; each row keeps its own rank and part of speech.

**A dated snapshot, not the final map.** The profile is still being extended;
this snapshot was taken on 2026-07-23 and the published map already lists more
B2/C1 lemmas than the eLex 2025 tables report. Treat the levels as validated but
provisional.

## License and attribution

The per-lemma levels are the work of the PULS authors, redistributed here **with
their permission**, licensed **CC-BY-NC-SA 4.0** (the authors' decision of
2026-09-24; NonCommercial, share-alike, attribution required). Attribution:
Ukrainian Vocabulary Profile (PULS), Synchak, O., Starko, V., Burak, M., Svystun, M.,
https://puls.peremova.org/. Cite as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026. Only
the lemma-to-level assignment for lemmas already on the frequency list is
redistributed; no definitions, examples, or other platform content are included.

## Where it fits

This is the level column the rest of the series trusts. Join it to the list
(`../v0.1.0/lemmas.csv`) on `rank`; a spelling at two ranks keeps two rows, so
join on `rank`, not on `lemma`.

- Its complement is `../predicted-cefr/`: model output for the 5,597 list
  lemmas this file does not label. Validated and predicted levels are never
  merged; together they account for all 12,000 lemmas.
- `../cefr-overlay/` is an older, unvalidated course overlay, kept as a
  cross-check against this file (45.5 percent exact, 86.6 percent within one
  level, on the 1,976 lemmas both label).
- `../minimums-crosswalk/` compares the two Borodin lexical minimums with the
  whole profile, not only this top-12,000 slice.
- `../b1-extension/` starts from the 1,604 lemmas labeled B1 here.

Used by the CEFR thread of the research page, the text profiler (its "known
words at level X" sets), the gap-fill model (as training labels), and the
`ukvocab` Python package (`levels()`).
