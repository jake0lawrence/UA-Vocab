# A crosswalk of the Ukrainian lexical minimums against the validated CEFR profile (datasheet)

Every lemma in the union of the two published Ukrainian A1 and A2 lexical minimums ("1000 i 1 slovo", Borodin and Turkevych; Borodin and Lazarenko) and the validated Ukrainian Vocabulary Profile (PULS), joined lemma by lemma on the Ukrainian Frequency corpus spine, with each agreement and disagreement classified: 10,366 rows, 1,200 agreements, 583 words the syllabus teaches earlier than the profile validates them, 174 later, 776 validated-A1 or A2 words in neither volume, 172 minimum words the profile does not cover, and 7,461 above a 2,000-word syllabus by arithmetic. Version v1.0.0, CC BY-NC-SA 4.0, the terms the profile publishes at https://puls.peremova.org/terms (the v1.0.0 files carry a superseded CC-BY-SA marking; see the README of the latest version).

## What it is

- `crosswalk.csv` / `crosswalk.json`: columns `lemma, rank, pos, volume, entry, validatedLevel, class, relative, relativeVia`. Classes: `agree`, `earlier`, `later`, `absent`, `beyond`, `unprofiled`.
- `manifest.json`, `SHA256SUMS`, `README.md`: the release's own hashes and column documentation as published on the site.
- `DATASHEET.md` (this file) and the deposit's `manifest.json`.

## How it was built

`scripts/ukrainian-frequency/build-minimums.mjs` over three committed snapshots: the A1 minimum as shared by its authors (2026-07-27), the A2 register extracted from the CC-BY-4.0 publication (2026-07-28), and the harvested PULS profile (2026-07-23, the whole published list, not only its top-12,000 slice, so a minimum word off the frequency list can still be compared). Both sides join by lemma string with the pedagogical stress accent stripped and the apostrophe folded across every glyph; membership is per headword, so every word an entry line names counts, and a word in both volumes counts as A1. Absent rows carry a deliberately over-matching relative flag (family, substring, shared stem, or a phrase entry) so the unflagged residue is conservative. Counts re-verify in CI from the rows.

## What it excludes

- Definitions, example sentences or any other content of the minimums; only the entry line text is reproduced, as the CC-BY license permits.
- Any judgment about which side is right. The classes describe where the two disagree, not who errs.

## Known defects

- No part of speech on the minimum side, so homographs collapse into one row.
- Onset, not sense: a word can be validated A1 for a basic sense while a minimum teaches a different sense.
- The frequency spine is lemmatized automatically and carries its errors (`рок` at rank 97 absorbs `рік`).
- The three sources do not agree on what counts as one lemma: `те` heads the absent list at rank 27 because the spine and the profile treat it as a lemma while the minimums treat it as the neuter of `той`. Read the absent list as candidates to check, never as omissions.

## Intended uses

Syllabus review against a validated profile; a worked example of comparing an expert selection with a corpus-validated map; a source of candidate additions and demotions for either side, with the relative flag as the first filter.

## Unintended uses

Scoring the minimums or the profile against each other as if one were ground truth; treating `absent` as a list of words the authors forgot.

## Attribution

- Borodin, K. and Turkevych, O. 1000 i 1 slovo. Leksychnyi minimum z ukrainskoi movy yak inozemnoi. Riven A1. Slavic Language Education 3, LANGUAGE-LAB, Humboldt-Universitat zu Berlin. https://doi.org/10.18452/28236. CC-BY 4.0. Machine-readable list provided by the authors, 2026-07-27.
- Borodin, K. and Lazarenko, O. (2026). 1000 i 1 slovo. Riven A2. Europa-Universitat Viadrina Frankfurt (Oder). https://doi.org/10.11584/opus4-1448. CC-BY 4.0.
- Ukrainian Vocabulary Profile (PULS): Synchak, O., Starko, V., Burak, M., Svystun, M. https://puls.peremova.org/ (eLex 2025). Redistributed with the authors' permission, CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24). Cite as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026. Snapshot 2026-07-23.
- Frequency ranks: UberText 2.0 (lang-uk; Chaplynskyi 2023), CC-BY 4.0.

## Cite this deposit

Lawrence, J. (2026). A crosswalk between the "1000 i 1 slovo" A1 and A2 lexical minimums and the validated Ukrainian Vocabulary Profile (v1.0.0). Zenodo. Concept DOI: see the deposit record. Live page: https://uavocab.org/research/crosswalk

## Maintenance

Rebuilt whenever any of the three inputs changes; each rebuild is a new version under the same concept DOI.
