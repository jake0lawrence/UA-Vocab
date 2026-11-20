# A crosswalk of the Ukrainian lexical minimums against the validated CEFR profile

Ukrainian has two independent published answers to "which words come first",
built by different methods. This joins them, lemma by lemma, on a corpus
frequency spine, and classifies every place they disagree.

## This version

v1.3.0 (2026-11-20) changes one column. The `relative` of an absent row is
partly drawn from the Wiktionary derived-term family graph, and that graph was
rebuilt on 2026-11-20 from the 2026-10-30 Wiktionary extraction with a fuller
reading of its etymologies (see `../../wiktionary-families/README.md`), so
129 absent rows name a different relative or gain one where they had none.
No row was added or removed, no class and no level changed. v1.2.0 and the
versions before it stay frozen beside this one.

## The two sides

**The minimums.** "1000 i 1 slovo", the corpus-informed expert lexical minimums
for Ukrainian as a foreign language, in two volumes:

- A1: Kseniia Borodin and Oksana Turkevych, Slavic Language Education 3,
  LANGUAGE-LAB, Humboldt-Universitat zu Berlin. https://doi.org/10.18452/28236
- A2: Kseniia Borodin and Olesia Lazarenko, Europa-Universitat Viadrina
  Frankfurt (Oder), 2026. https://doi.org/10.11584/opus4-1448

Both CC-BY-4.0. Selection mixes GRAK and Ukrainian Web 2022 corpus frequency
with usefulness at the learning stage (method published separately: Borodin and
Lazarenko, New Directions in Slavic Studies, Editorial Universidad de Granada,
2026, 41-52). A teaching syllabus, about 2,000 words.

**The profile.** The Ukrainian Vocabulary Profile on PULS (O. Synchak,
V. Starko, M. Burak, M. Svystun; eLex 2025), the one corpus-VALIDATED
CEFR profile for Ukrainian. 10,194 lemma strings, A1 to C1. Redistributed
here by permission of the authors. A descriptive map, not a syllabus.

**The spine.** Frequency ranks are the top-12,000 lemma list at
jakelawrence.xyz/research/ukrainian-frequency, derived from UberText 2.0
(Chaplynskyi 2023, lang-uk), CC-BY-4.0.

## What one row is

One row per lemma string in the union of the two sides:
10,366 rows.

| column | meaning |
|---|---|
| `lemma` | the lemma string, stress accent stripped, apostrophe folded to U+2019 |
| `rank` | frequency rank on the top-12,000 list, blank if the corpus never reached it |
| `pos` | UD part of speech from the frequency list, blank if off-list |
| `volume` | `A1` or `A2` if a minimum carries it, blank otherwise (a word in both counts as A1) |
| `entry` | the published entry line it came from, verbatim |
| `validatedLevel` | the profile's level, blank where the profile does not cover it |
| `class` | see below |
| `relative` | for an absent row, where a minimum does reach the word after all |
| `relativeVia` | `phrase` (it appears inside a multi-word entry), or `family`, `contains`, `stem` (a headword plausibly on the same root) |

Classes:

- `agree` (1,200): the volume and the validated level are the same
- `earlier` (583): the minimum teaches it earlier than the profile validates it
- `later` (174): the minimum teaches it later than the profile validates it
- `absent` (776): validated A1 or A2, and neither volume carries it
- `beyond` (7,461): validated B1 or higher and outside the minimums, as expected
- `unprofiled` (172): in a volume, and the profile does not cover it

## How a row is matched, and what that costs

Both sides join by lemma string. The stress accent (U+0301) is pedagogical, not
lexical, so it is stripped; the apostrophe is folded across all four glyphs the
sources use and the one HTML entity the PULS harvest preserved. Two limits
follow, and no claim here survives ignoring them:

- **No part of speech on the minimum side.** The published lists carry none, so
  homographs collapse into one row.
- **Onset, not sense.** A profile level is the level of the lexeme's earliest
  sense. A word can be validated A1 for a basic sense while a minimum teaches a
  different sense of it. A string crosswalk cannot see that.
- **The frequency spine is lemmatized automatically** and carries its own
  errors. `rok` at rank 97 is the clearest: it absorbs tokens of `rik` (year,
  rank 13). Ranks are a rough ordering, not evidence about a word.
- **The three sources do not agree on what counts as one lemma.** `te` heads the
  absent list at rank 27, and it is not a word the minimums forgot: the spine
  and the profile both treat it as a lemma, while the minimums treat it as the
  neuter of `toi`, which the A2 volume carries. Read the absent list as
  candidates to check, never as a list of omissions.

A word that appears only inside a multi-word entry is not a member (the volume
does not list it as a word) but its absent row names the phrase, so `takyi` reads
against `takyi samyi` and `zhal` against `Na zhal`. 19 rows are of that kind.

An entry line can name several words (an aspect pair, a gender pair, a spelling
variant set), and every one of them counts as carried. Inside a parenthesis the
authors separate alternatives with a semicolon and paradigm forms with a comma,
and a parenthesis with no space in front of it continues the word it touches
(`vmyvaty(sia)` gives both `vmyvaty` and `vmyvatysia`); the parser follows
that.

## Reading the `unprofiled` class fairly

172 minimum words carry no validated level. They are mostly proper nouns and
the adjectives built on them (Ukraine, Kyiv, Poland, Ukrainian, German), which a
vocabulary profile does not set out to cover. This is a note about scope, not a
gap in the profile.

## Where it fits

The per-volume joins are `../../borodin-a1/` and `../../borodin-a2/`, which
compare each minimum with the frequency list only. This file reads both volumes
against the whole validated profile; `../../validated-cefr/` is the same
profile cut to the top-12,000 list. To attach any other list column, join
`rank` to `../../v0.2.0/lemmas.csv` (a blank rank is a word the list never
reached).

The research page renders the classes as a contingency grid at
/research/ukrainian-frequency/crosswalk, where every cell is a selectable word
set, with the method at /research/ukrainian-frequency/crosswalk/method. The
`ukvocab` Python package ships this table, and it is a Zenodo deposit. The
same entry-reading fix was applied to the text profiler's Borodin known-word
sets.

## Reproduce

```
node scripts/ukrainian-frequency/build-minimums.mjs
node scripts/ukrainian-frequency/build-minimums.mjs --check
```

Deterministic, offline, from committed snapshots only. `--check` verifies the
committed bundle re-derives byte for byte. CI enforces the same thing through
the test suite, which rebuilds the crosswalk from the snapshots and compares it
to the frozen files and their hashes.

## License and attribution

**This crosswalk: CC-BY-NC-SA-4.0.** Every row carries a PULS level, and the
PULS levels are CC BY-NC-SA 4.0 at the authors' decision (2026-09-24), so the
NonCommercial and share-alike terms propagate to the combined table. The
Borodin volumes stay CC-BY-4.0 in their own right; the profile's terms apply to
this joined file, not to its sources. Versions before v1.2.0 carry a superseded
CC-BY-SA marking; the levels in them are under these same terms.

It is a derived, factual join. Attribute the sources it joins, not only this
file:

- Minimums: Borodin and Turkevych (A1, DOI 10.18452/28236); Borodin and
  Lazarenko (A2, DOI 10.11584/opus4-1448). Both CC-BY-4.0.
- Validated levels: Synchak, O., Starko, V., Burak, M., Svystun, M., Ukrainian Vocabulary
  Profile / PULS. CC-BY-NC-SA-4.0, redistributed by the authors' permission.
  Cite as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.
- Frequency ranks: UberText 2.0 (Chaplynskyi 2023, lang-uk), CC-BY-4.0.

Cite as: Lawrence, J. (2026). A crosswalk between the "1000 i 1 slovo" A1 and A2 lexical minimums and the validated Ukrainian Vocabulary Profile (v1.3.0). jakelawrence.xyz/research/ukrainian-frequency.

Snapshot: 2026-11-20
