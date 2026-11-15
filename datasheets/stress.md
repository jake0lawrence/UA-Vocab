# Ukrainian Frequency: word stress for every lemma of the top-12,000 list (datasheet)

A stressed form for each of the 12,000 lemma-and-part-of-speech rows of the Ukrainian Frequency list (v0.2.0, over UberText 2.0), keyed on the list's ranks: one confident stress where the open sources agree (9,673 of the 9,920 polysyllabic common words, 97.5 percent), a labeled free variant, homograph or dictionary-only doublet where they do not (226), and an honest `missing` for the 21 rows no source resolved. The 1,348 proper nouns are out of scope by owner decision: kept on their rows with the stress the pipeline found and the pipeline's status in the note, counted in no share. Every row carries the provenance of its stress; every manual decision is a ledgered override. Current release v1.0.2, CC-BY-SA 4.0 because of the Wiktionary-derived rows; kept as its own file rather than a column on the CC-BY list so the list is not relicensed.

## What it is

- `stress.csv`: one row per lemma, rank order. Columns `rank, lemma, pos, stress, stress_variants, stress_status, note, source`. `stress` is the primary stressed form with the combining acute (U+0301), empty when the status is `missing`; `stress_variants` is pipe-separated, primary first; `stress_status` is one of the values documented in the README, `proper_noun` marking the out-of-scope names; `note` carries homograph glosses, a compound's secondary stress or the standard spelling of a nonstandard lemma; `source` is where the stress came from.
- `stress.json`: the same rows with the counts and the status table in the header.
- `stress.anki.tsv`: an Anki-importable seed (stressed form, part of speech, rank, variants, status), one note per lemma, most frequent first.
- `adjudication.csv`: every lemma the sources disagreed on (199 rows) with each source's vote and the decision taken.
- `paradigm-disagreements.csv`: this column read against the headwords of the site's Wiktionary paradigms file over the in-scope rows, with a verdict per row (corrections backed by goroh or the dictionary, and open rows).
- `doublets.csv`: the in-scope dictionary-only doublets still open (the dictionary lists two stresses and no open source covers the word), the worklist for the printed-source pass (Pohribnyi's orthoepic dictionary); it shrinks as lookups enter the override ledger.
- `README.md`: columns, the status taxonomy with counts, method, sources and attribution.
- `manifest.json`, `SHA256SUMS`: the release's own hashes as published on the site.
- `DATASHEET.md` (this file) and the deposit's `manifest.json` with SHA-256 per file.

## How it was built

Nine stages, applied in order over the committed v0.2.0 list, consolidated in `scripts/ukrainian-frequency/extract-stress.py` in the source repository: monosyllables need no mark; the lang-uk `ukrainian-word-stress` 2.1.0 dictionary is read directly from its trie and filtered by the list's own Universal Dependencies part of speech and lemma features, because the library's tagger guesses the part of speech of a bare lemma and gets homographs wrong (брати́ "brothers" for the verb бра́ти; 18 such errors caught); en.wiktionary (the kaikki.org extraction) separates a true free variant from a homograph from a minor variant and fills some gaps; uk.wiktionary (the dump) is a second, independent Wiktionary voice; where the three disagree, two of three decide; rules dissolve conflicts that are only apparent (en.wiktionary marks every part of a compound, the dictionary only the main stress); goroh.pp.ua settles 19 leftover conflicts, one reference lookup per word, only the attested stress recorded; rules cover lemmas no source has (standard spelling, compounds, acronyms, -енко surnames); uk.wikipedia lead sentences stress 116 names, the article title kept per row and a mark that does not sit on a vowel refused. The 27 manual decisions live in `stress-overrides.json` and are applied last by the pure builder (`src/lib/ukrainian-frequency/stress.mjs`); `scripts/ukrainian-frequency/build-stress.mjs` freezes the release with hashes, and CI re-derives it byte for byte from the committed snapshot, holds every row to the list, and refuses a goroh-backed row that changes without a ledger entry.

## What it excludes

- Corpus text. Only a stressed headword per lemma is published.
- Any content from goroh.pp.ua beyond the attested stress position for 19 words.
- Inflected forms: the stress of a declined or conjugated form is not carried (the site's paradigms file has Wiktionary's forms, verbatim).
- A corpus-verified primary stress for the homographs whose readings are spelled alike in every form (о́рган / орга́н): the primary is the first en.wiktionary entry, and the row says so. Homographs whose readings differ in spelling somewhere in the paradigm are counted in UberText 2.0 (every distinguishing form that is also another word's struck first by the VESUM lemmatizer) and the primary is the reading whose forms occur more.
- Any claim about proper nouns.

## Known defects

- Most homographs still carry the first en.wiktionary entry as primary: only the pairs whose readings differ in spelling somewhere in the paradigm could be counted in UberText 2.0 (`homograph_corpus`, counts in `source`); the pairs spelled alike in every cell cannot be settled by a surface count and say in `note` that the primary is unverified.
- 49 in-scope rows are dictionary-only doublets (the dictionary lists two stresses and no other source covers the word); the primary is the first listed until the printed-source lookup lands in the ledger.
- 21 in-scope rows are missing. Proper nouns are out of scope (owner decision 2026-10-01); their rows carry the pipeline's stress but the column makes no claim about them.
- 22 rows (`library_context`) are not reproducible from the trie alone: the dictionary is ambiguous for the lemma's part of speech and the library's context model chose.
- Two data errors found in the upstream dictionary (йо́го for його́ at rank 40; підозрюва́тися for підо́зрюватися) are corrected here by override and queued upstream; hyphenated compounds in that dictionary list the main and secondary stress as alternative readings.
- A uk.wikipedia search can return a different bearer of a name; the article title is recorded per row so a wrong bearer can be audited.

## Intended uses

Pronunciation for learners and course writers working from the frequency list (the Anki seed teaches each word with its stress); a per-lemma stress lexicon for text-to-speech, readers and dictionaries that need an open, provenance-labeled source; a cross-check for other stress resources (the adjudication log and the paradigm disagreements name exactly where the open sources differ).

## Unintended uses

Treating the primary stress of a `homograph` row as the most frequent sense (only a `homograph_corpus` row is corpus-verified, and only by the forms that differ in spelling); treating a `doublet_dictionary_only` or `name_variable` primary as the standard (both stresses are accepted or vary by bearer, and the row says so); reading the 19 goroh rows as a redistribution of that reference (only the stress position is recorded); using this file for inflected forms.

## Attribution

- ukrainian-word-stress 2.1.0, lang-uk (Oleksiy Syvokon; maintained by Dmytro Chaplynskyi). https://github.com/lang-uk/ukrainian-word-stress MIT.
- en.wiktionary via kaikki.org (Tatu Ylonen's wiktextract) and uk.wiktionary (the pages-articles dump). Wiktionary content CC-BY-SA 3.0.
- uk.wikipedia lead sentences, CC-BY-SA 4.0, for 116 proper nouns.
- goroh.pp.ua, consulted for 19 tiebreaks; no content copied.
- Ranks, lemmas and tags: UberText 2.0 lemma frequency dictionary, lang-uk. Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern Ukrainian at Scale. Proc. 2nd UNLP, ACL. CC-BY 4.0.

## Cite this deposit

Lawrence, J. (2026). Ukrainian Frequency: a per-lemma word-stress column for the top-12,000 list (v1.0.2). Zenodo. Concept DOI: see the deposit record. Over ukrainian-word-stress (lang-uk), en.wiktionary and uk.wiktionary. Live page: https://uavocab.org/research#stress. Python: `pip install uavocab` (https://pypi.org/project/uavocab/). Cite the version DOI of the release you actually used.

## Maintenance

Refreshed when the frequency list publishes a new version (the column is keyed on its ranks), when the upstream dictionary or the Wiktionary extraction change a reading the vote depends on, or when an open task closes (the corpus count for homographs, the proper-noun scope decision, the dictionary-only doublets); each refresh is a new version under the same concept DOI, and every prior version stays published. The version DOI is the one to cite for a reproducible figure. v1.0.1 (2026-10-07) corrected the credit for ukrainian-word-stress with the data byte-identical to v1.0.0; v1.0.2 (2026-10-09) changes one row, тризуб (rank 11,982), from the dictionary's тризу́б to a free variant with три́зуб first, on a native-speaker reader's report checked against the open recording and e2u.org.ua (one confident row becomes one labeled row).
