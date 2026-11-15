# Ukrainian Frequency: experimental CEFR overlay

`lemmas.csv` maps lemmas from the [Ukrainian Frequency](https://uavocab.org/research)
top-12,000 list to a CEFR level (columns: `rank,lemma,pos,heuristic_level,level,confidence`).
2,325 of the 12,000 lemmas carry a label; levels reach A1 to B2 (plus one C1,
заявити, where a published validated level overrides the course's B1).

- `heuristic_level` is the course's own first-occurrence level, kept before any
  override so agreement with the validated levels can be measured honestly.
- `level` is the delivered label: the heuristic level, or, where Synchak et al.
  publish a validated level for the lemma, that level instead.
- `confidence` is `validated` (114 rows, the level above came from the
  validated profile), `typical`, or `frequency-outlier` (the lemma's rank falls
  outside the Tukey fence of its level's ranks).

## This is an experimental, UNVALIDATED overlay

The levels come from the [learn-ukrainian](https://github.com/learn-ukrainian/learn-ukrainian.github.io)
open course (Krisztian Koos): each lemma's level is the lowest CEFR course level
whose lessons introduce it (a first-occurrence heuristic). This is an expert
selection based on Ukraine's 2024 State Standard, **not** a corpus-frequency
validated CEFR profile. Treat it as a rough teaching-order signal, not a
proficiency label. For the one corpus-validated (but browse-only) profile, see
Synchak et al. 2025 on the PULS platform.

## License and attribution

Derived from learn-ukrainian curriculum content, licensed **CC-BY-SA 4.0**. This
overlay is redistributed under the same **CC-BY-SA 4.0** license. Attribution:
learn-ukrainian (Krisztian Koos), https://github.com/learn-ukrainian/learn-ukrainian.github.io.
Only the lemma-to-level assignment is redistributed; no course translations,
examples, or prose are included.

## Where it fits

This was the first CEFR signal the series published. It is now a cross-check,
not the level to use: for a word's level, use `../validated-cefr/lemmas.csv`
(6,403 lemmas, A1 to C1).

The `validated` confidence tier here is narrower than that folder: its 114
overrides came from the per-lemma levels printed in the eLex 2025 paper, before
the full profile was redistributed. Measured against the full validated
overlay, `heuristic_level` matches exactly on 45.5 percent and within one level
on 86.6 percent of the 1,976 lemmas both label. The `frequency-outlier` rows
are everyday A1 words (борщ, помідор, прокидатися) that the news-heavy corpus
ranks low, the same bias `../genre-split/` measures directly.

Used by the CEFR thread of the research page as its measured cross-check, and
read as a reference by several of the extraction scripts. Not used by the
profiler or the B1 extension.
