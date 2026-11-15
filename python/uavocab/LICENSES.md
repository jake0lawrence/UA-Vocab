# Licenses

## The combined work: CC-BY-NC-SA 4.0

This package as a whole is distributed under the Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 International license
(https://creativecommons.org/licenses/by-nc-sa/4.0/).

Why NonCommercial and share-alike: the per-lemma CEFR levels come from the
Ukrainian Vocabulary Profile (PULS), which its authors license CC BY-NC-SA 4.0
(decided 2026-09-24) and which is redistributed here with their permission.
Those levels are in the validated overlay, in every row of the crosswalk, in
the `puls_level` column of the two Borodin tables, and in the `related_level`
column of the aspect table. NonCommercial and share-alike propagate to a
combined work, so the package carries both. They are the one NonCommercial
component; nothing else NonCommercial is shipped. The frequency list and the
two Borodin minimums are CC-BY 4.0 on their own and remain so, and the
government and collocation tables and the stress column are CC-BY-SA 4.0; each
dataset's own license is recorded in `uavocab.sources()` and below, so a downstream user who drops
the PULS level columns owes attribution (and, for the corpus tables,
share-alike) and nothing more.

Cite the profile as its authors ask: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.

## Per dataset

| Dataset | License | Attribution |
|---|---|---|
| `frequency` (top-12,000 lemma list) | CC-BY 4.0 | Derived aggregate counts from the UberText 2.0 lemma frequency dictionary, lang-uk. Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern Ukrainian at Scale. Proc. 2nd UNLP, ACL. https://lang.org.ua/en/ubertext/ |
| `validated_cefr` (PULS CEFR overlay) | CC-BY-NC-SA 4.0 | Ukrainian Vocabulary Profile (PULS): Synchak, O., Starko, V., Burak, M., Svystun, M. https://puls.peremova.org/ (eLex 2025). Per-lemma levels redistributed with the authors' permission (V. Starko, July 2026); CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24), attribution required. Snapshot 2026-07-23; the profile is not final. |
| `borodin_a1` (A1 lexical minimum) | CC-BY 4.0 | Borodin, K. and Turkevych, O. 1000 i 1 slovo. Leksychnyi minimum z ukrainskoi movy yak inozemnoi. Riven A1. Slavic Language Education 3, LANGUAGE-LAB, Humboldt-Universitat zu Berlin. https://doi.org/10.18452/28236. Machine-readable list provided by the authors, 2026-07-27. The `puls_level` column is CC-BY-NC-SA (PULS). |
| `borodin_a2` (A2 lexical minimum) | CC-BY 4.0 | Borodin, K. and Lazarenko, O. (2026). 1000 i 1 slovo. Riven A2. Europa-Universitat Viadrina Frankfurt (Oder). https://doi.org/10.11584/opus4-1448. The `puls_level` column is CC-BY-NC-SA (PULS). |
| `crosswalk` (minimums against the profile) | CC-BY-NC-SA 4.0 | Lawrence, J. (2026), over the two Borodin volumes (CC-BY 4.0), the PULS profile (CC BY-NC-SA 4.0, by permission) and UberText 2.0 ranks (CC-BY 4.0). |
| `b1_aspect` (aspect relations) | CC-BY-NC-SA 4.0 | Levels: PULS, by permission, CC BY-NC-SA 4.0. Aspect partners: Wiktionary via kaikki.org, CC-BY-SA 3.0. Counts: UberText 2.0, CC-BY 4.0. |
| `b1_government` (case government) | CC-BY-SA 4.0 | Counts over the UberText 2.0 Wikipedia subcorpus (lang-uk, CC-BY 4.0); derived statistics CC-BY-SA 4.0. |
| `b1_collocations` (logDice collocations) | CC-BY-SA 4.0 | Same corpus and terms as `b1_government`. |
| `stress` (word stress per lemma) | CC-BY-SA 4.0 | ukrainian-word-stress 2.1.0 (lang-uk: Oleksiy Syvokon, maintained by Dmytro Chaplynskyi), MIT, https://github.com/lang-uk/ukrainian-word-stress; en.wiktionary via kaikki.org and uk.wiktionary, CC-BY-SA 3.0; uk.wikipedia lead sentences for a few names, CC-BY-SA 4.0; goroh.pp.ua consulted for 19 tiebreaks (attested stress only). Share-alike from the Wiktionary rows; its own table, joined on rank, so the list stays CC-BY. |

## Not in this package

Predicted CEFR levels (the site's gap-fill model; predictions are never merged
into the validated overlay), any VESUM-derived lexicon or wordform data
(CC BY-NC-SA), the UniMorph derivational families (CC BY-NC 4.0), the
Wikipedia example sentences, and the Wiktionary paradigm tables. If you need
any of them, they are on the site with their own terms.

## The code

The Python code in this package (`src/uavocab/*.py`) is released under the
same CC-BY-NC-SA 4.0 terms as the data, to keep one license on the wheel.
