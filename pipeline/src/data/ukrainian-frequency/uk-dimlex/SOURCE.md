# UK-DiMLex snapshot (WO-4, item 3)

`UK_DiMLex.xml` is the lexicon of Ukrainian discourse connectives by Tatjana
Scheffler, Veronika Solopova, Olha Zolotarenko and Mariia Razno (A
Computational Lexicon of Ukrainian Discourse Connectives, ICTERI 2021), copied
verbatim from https://github.com/TScheffler/UK_DiMLex (master, 2026-09-14).
MIT license (`LICENSE` beside it). The paper counts 129 entries; the file
carries every `<entry>` element the XML holds, which the attestation snapshot
counts rather than assumes.

`attestation.json` is derived by `scripts/ukrainian-frequency/contrib-fetch-evidence.mjs --dimlex`:
per connective its orthographic parts, and per distinct word the UberText 2.0
lemma-frequency count summed over every POS the dictionary lists (the same
`ubertext_freq.csv.xz` the frequency list was built from, not vendored). The
source spells the Cyrillic conjunction `і` with a Latin `i` in several
entries; the snapshot folds that for counting and records each fold.

Used only to draft `contrib/uk-dimlex/note.md`; nothing is submitted from the
repository.
