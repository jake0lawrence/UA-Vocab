# Ukrainian Frequency, thread 07: word stress

A stressed form for every one of the 12,000 lemmas of the thread-01 frequency
list (v0.2.0). Ukrainian stress is free and mobile, so it cannot be read off the
spelling, and it is the gap learners ask about most. Where the sources agree
there is one stress; where they do not, the row says so instead of guessing.

Join on `rank` to `../../v0.2.0/lemmas.csv`. The `lemma` and `pos` columns are
the list's own and a test holds them to it.

## The numbers

| | count |
|---|---|
| lemmas | 12,000 |
| proper nouns, out of scope (kept, not counted) | 1,348 |
| polysyllabic common words (the denominator) | 9,920 |
| one confident stress | 9,673 (97.5% of polysyllabic) |
| labeled: variant, homograph, name, dictionary-only doublet | 226 (confident or labeled: 99.8%) |
| monosyllabic, no mark needed | 732 |
| still missing | 21 (12 NOUN, 6 ADJ, 2 ADV, 1 VERB) |

Proper nouns are **out of scope** by owner decision (2026-10-01), as most learner
lists leave names out: every PROPN row keeps the stress the pipeline found and
the pipeline's own status in `note`, carries `stress_status` `proper_noun`,
and is counted in none of the shares above. Filter on `pos != PROPN` for the
column as claimed.

## `stress.csv` (one row per lemma)

| column | meaning |
|---|---|
| `rank` | the lemma's rank on the thread-01 list (1 = most frequent) |
| `lemma` | the dictionary form, the list's own spelling |
| `pos` | Universal Dependencies part of speech, the list's own tag |
| `stress` | the primary stressed form; the stress mark is the combining acute U+0301; empty when `stress_status` is `missing` |
| `stress_variants` | pipe-separated, primary first; set when more than one stress is valid or possible |
| `stress_status` | how the row was resolved (table below) |
| `note` | glosses for a homograph, the secondary stress of a compound, the standard spelling of a nonstandard lemma, or the other source's reading |
| `source` | provenance of the chosen stress: the dictionary, the Wiktionary that resolved it, the vote, the rule, the goroh tiebreak, or the uk.wikipedia article title |

`stress.json` is the same table with the counts and this status table in the
header. `stress.anki.tsv` is an Anki-importable seed: stressed form, part of
speech, rank, variants, status, one note per lemma, most frequent first.

### `stress_status`

| status | count | meaning |
|---|---|---|
| `dictionary` | 9,388 | the ukrainian-word-stress dictionary (lang-uk), one reading for this lemma, reproducible from the trie alone |
| `dictionary_pos` | 12 | the dictionary lists several readings; filtered to one by the list's own UD part of speech and lemma features |
| `library_context` | 16 | the dictionary is ambiguous for this part of speech and the library's context model chose; not reproducible from the trie alone |
| `wiktionary` | 125 | a dictionary doublet resolved by en.wiktionary (the other stress is a minor, dated or dialectal variant) |
| `wiktionary_filled` | 23 | absent from the dictionary, filled from en.wiktionary |
| `adjudicated` | 37 | sources disagreed and a two-of-three vote, a rule or a goroh.pp.ua tiebreak decided; see source |
| `compound` | 21 | a hyphenated compound the library stressed as a whole; the main stress is kept, any secondary stress is in the note |
| `compound_rule` | 31 | a hyphenated or stump compound: stress on the last component |
| `compound_main_stress` | 10 | the dictionary listed the main and the secondary stress as alternatives; the main (last component) is kept, the secondary is in the note |
| `abbreviation_rule` | 3 | an acronym read letter by letter: final syllable |
| `spelling_variant` | 6 | looked up under the standard spelling (the list's spelling is nonstandard); the standard spelling is in the note |
| `wikipedia_lead` | 1 | a proper noun stressed from the uk.wikipedia lead sentence; the article title is in source |
| `free_variant` | 89 | both stresses are accepted (та́кож / тако́ж); the primary is listed first |
| `homograph` | 57 | different words with different stress (о́рган body / орга́н instrument) whose forms are spelled alike in every cell, so the corpus cannot tell them apart; the primary is the first en.wiktionary entry, not corpus-verified |
| `homograph_corpus` | 31 | different words with different stress whose paradigms differ in spelling somewhere (прохо́дити / проходи́ти); the primary is the reading whose distinguishing forms occur more in UberText 2.0, with the counts in source |
| `doublet_dictionary_only` | 49 | the dictionary lists two stresses and no other source covers the word; the primary is the first listed |
| `monosyllabic` | 732 | one syllable; no mark needed |
| `missing` | 21 | no source resolved it |
| `proper_noun` | 1,348 | a proper noun: out of scope by owner decision (2026-10-01), as most learner lists leave names out; the stress the pipeline found is kept for reference and the pipeline's own status is in the note, but the row is not counted |

## `adjudication.csv`

Every lemma the sources disagreed on (199 rows), with each
source's vote and the decision taken: the show-your-work layer. The
28 manual decisions, including the 19 rows that cite a goroh.pp.ua
tiebreak, are in the repository's `stress-overrides.json` and are applied last
by the builder, so a rebuilt pipeline reproduces them and a test fails if a
goroh-backed row changes without an entry there.

## `doublets.csv`

The 49 in-scope rows where the dictionary lists two stresses and no open
source covers the word (`stress_status` `doublet_dictionary_only`; the primary
is the first listed). By owner decision (2026-10-01) these are settled from a
printed orthoepic dictionary (Pohribnyi, Orfoepichnyi slovnyk) rather than from
goroh.pp.ua, which would otherwise become a pillar of the data: each lookup
enters `stress-overrides.json` with the page as evidence, and the same test
that holds goroh refuses a row citing the printed source without a ledger entry.
This file is the worklist; it shrinks as the ledger grows.

## `paradigm-disagreements.csv`

This column read against the headwords of the thread-04 paradigms file
(`../../paradigms/`, Wiktionary's forms, verbatim): 13 rows where the
paradigm's headword stress is not one this column accepts. `verdict`
`stress_column` (11 rows) means the paradigm headword is the one to
correct and the `evidence` column says why (goroh and the dictionary agree
against en.wiktionary; or the paradigm joined the other homograph, as музи́ка the
musician for му́зика the music). `open` means neither side is adjudicated:
a review queue, not a verdict. The paradigms file is not patched: it is a
verbatim mirror and the next dump would overwrite the patch; the corrections
are published here and queued upstream instead.

## Method

Nine stages, applied in order: the lang-uk ukrainian-word-stress dictionary read directly from its trie and filtered by the list's own UD part of speech and lemma features (no tagger guess on a bare lemma); en.wiktionary (kaikki.org), which separates free variants, homographs and minor variants; uk.wiktionary (the dump); a two-of-three vote where the three disagree; rules for conflicts that are only apparent (compound secondary stress, doubled-accent artifacts); goroh.pp.ua tiebreaks for what is left, one reference lookup per word, recorded as the attested stress only; rules for lemmas no source covers (standard spelling, compounds, acronyms, -енко surnames); uk.wikipedia lead sentences for names; and the manual-decision ledger applied last.

Two things the method does not do. It does not let any one source win by
default: en.wiktionary was wrong against goroh on по́каз, нульови́й, побажа́ння and
казко́вий, and the library dictionary was wrong twice (йо́го for його́ at rank 40,
підозрюва́тися for підо́зрюватися). And it does not guess a homograph's primary
where the corpus cannot tell the readings apart: 31 homographs whose two
readings differ in spelling somewhere in the paradigm (прохо́дити / проходи́ти)
take their primary from a count of those distinguishing forms across the five
UberText 2.0 subcorpora, after every form that is also another word's (заходи,
the imperative of заходи́ти and the plural of захід) is struck by the site's own
VESUM lemmatizer (`homograph_corpus`, counts in `source`;
4 of them flipped from the first en.wiktionary entry); the 57 whose
forms are spelled alike in every cell (о́рган / орга́н) keep the first
en.wiktionary entry as primary and say in `note` that it is unverified.

## Source and license

- **ukrainian-word-stress** 2.1.0 (lang-uk: Oleksiy Syvokon, maintained by Dmytro Chaplynskyi), MIT.
  https://github.com/lang-uk/ukrainian-word-stress. The dictionary baseline for
  9,486 rows. (v1.0.1, 2026-10-07, corrects this credit:
  the v1.0.0 README named a reader who pointed at the library as its
  maintainer. The data files are byte-identical to v1.0.0, which stays
  published under its own DOI.)
- **v1.0.2** (2026-10-09) changes one row: тризуб (rank 11,982) moves from the
  dictionary's тризу́б to `free_variant` with три́зуб first. A native-speaker
  reader reported три́зуб as the form in speech, the open recording carries it,
  and e2u.org.ua lists both; the decision is in the manual ledger.
- **en.wiktionary** via kaikki.org (wiktextract) and **uk.wiktionary** (the
  dump), CC-BY-SA 3.0. Resolve doublets, fill gaps, and vote.
- **uk.wikipedia** lead sentences, CC-BY-SA 4.0, for 1 proper nouns; the
  article title is in `source`.
- **goroh.pp.ua** for 19 tiebreaks: only the attested stress is recorded, no
  content is copied, and every such row is a ledgered manual decision.
- Ranks, lemmas and tags: UberText 2.0 (Chaplynskyi 2023, lang-uk), CC-BY 4.0.

**This file: CC-BY-SA 4.0**, because the Wiktionary-derived rows carry
share-alike. It is kept as its own file, joined on rank, rather than a column
on `lemmas.csv`, so the list itself stays CC-BY 4.0.

Cite as: Lawrence, J. (2026). Ukrainian Frequency: a per-lemma word-stress column for the top-12,000 list (v1.0.2). jakelawrence.xyz/research/ukrainian-frequency. Over ukrainian-word-stress (lang-uk), en.wiktionary and uk.wiktionary.

Snapshot: 2026-10-01
