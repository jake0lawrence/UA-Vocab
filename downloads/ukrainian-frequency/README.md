# Ukrainian Frequency: the open-data downloads

Every file published by the [Ukrainian Frequency](https://uavocab.org/research)
research series. One list sits at the center: the top 12,000 lemmas of modern
Ukrainian, ranked by corpus frequency (thread 01, `v0.2.0/`; the first release,
`v0.1.0/`, stays frozen beside it). Almost every other table here hangs off it
by `rank`, adding one kind of information per folder.

Each folder carries its own README with columns, method, limits and license.
This file is the map between them.

## The folders

| Folder | Question it answers | Main file | Rows | License |
|---|---|---|---|---|
| `v0.2.0/` | What should a learner meet first? (`v0.1.0/` is the frozen first release) | `lemmas.csv` | 12,000 | CC-BY-4.0 |
| `stress/` | Where does the stress fall in each of those lemmas? | `v1.0.2/stress.csv` | 12,000 | CC-BY-SA-4.0 |
| `validated-cefr/` | What CEFR level is this word, according to the one corpus-validated profile? | `lemmas.csv` | 6,403 | CC-BY-NC-SA-4.0 (by permission) |
| `predicted-cefr/` | A model's best guess for the words the profile does not label | `predictions.csv` | 5,597 | CC-BY-NC-SA-4.0 |
| `cefr-overlay/` | When does one open course teach the word? (experimental, a cross-check only) | `lemmas.csv` | 2,326 | CC-BY-SA-4.0 |
| `borodin-a1/` | How does the published A1 lexical minimum compare with the list? | `lemmas.csv` | 929 | CC-BY-4.0 |
| `borodin-a2/` | The same for the A2 minimum, plus which topics the list misses | `lemmas.csv`, `themes.csv` | 1,000 | CC-BY-4.0 |
| `minimums-crosswalk/` | Where do the two minimums and the validated profile agree or disagree? | `v1.2.0/crosswalk.csv` | 10,366 | CC-BY-NC-SA-4.0 |
| `genre-split/` | Is an A2 word missing because it is rare, or because the corpus is news? | `entries.csv`, `themes.csv` | 936 | CC-BY-4.0 inputs |
| `derussification/` | Which common words would an open style checker replace, and with what? | `lemmas.csv` | 87 | LGPL-2.1 |
| `paradigms/` | How does the word sound, and what forms will a reader actually meet? | `lemmas.csv`, `forms.csv.gz` | 9,269 | CC-BY-SA-3.0 |
| `wiktionary-families/` | Which list words are derivational kin? | `families.csv`, `edges.csv` | 11,056 / 14,975 | CC-BY-NC-SA-4.0 (CC-BY-SA without the level column) |
| `b1-extension/` | Aspect, motion verbs, government, collocations, examples and multiword expressions for validated B1 | seven CSVs | | CC-BY-NC-SA-4.0 where a level column is present; CC-BY-SA-4.0 for the rest |
| `profiler/` | The text profiler's lexicon and form index (JSON, fetched by the page) | `v1.2.0/lexicon.json` | | CC-BY-NC-SA-4.0 (see its manifest) |
| `vocab-test/` | The vocabulary-size test's item bank: 60 real lemmas and 60 pseudowords across the 12 frequency bands (JSON) | `v1.2.0/items.json` | | CC-BY-4.0 (see its manifest) |

**The PULS levels are CC BY-NC-SA 4.0.** Every file that carries a level from the
Ukrainian Vocabulary Profile (PULS) is licensed CC-BY-NC-SA-4.0 as a whole, the
terms its authors decided on (O. Synchak, 2026-09-24); columns from other sources
keep their own licenses, so a file with its level column dropped owes only what
those columns owe. Frozen bundles from before that date (`minimums-crosswalk/v1.0.0`
and `v1.1.0`, `profiler/v1.0.0` to `v1.1.0`) are kept byte-identical and still
read CC-BY-SA in their own manifests; that marking is superseded and the levels
in them are under the same NonCommercial terms. Cite the profile as its authors
ask: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.

Row counts are for the snapshot in this commit; each folder's README or
manifest is authoritative.

## v0.2.0: the list itself

`v0.2.0/` is a frozen, hashed release (`manifest.json`, `SHA256SUMS`);
`latest.json` points at it. `lemmas.csv` has the columns
`rank,lemma,pos,count,permille,cumulativeCoverage,freqBand`:

- `rank`: 1 is the most frequent lemma.
- `lemma`, `pos`: the dictionary form and its Universal Dependencies part of
  speech. The list is POS-aware, so a homograph with two roles gets two rows
  (що is rank 8 as a conjunction and rank 39 as a pronoun).
- `count`: occurrences in the source corpus.
- `permille`: occurrences per 1,000 running words.
- `cumulativeCoverage`: the share of running words covered by this lemma and
  every lemma above it (the top 1,000 cover 60.8 percent, the top 5,000 82.1).
- `freqBand`: the block of 1,000 the rank falls in.

The same rows ship as `lemmas.json` and as an Anki seed (`lemmas.anki.tsv`);
`coverage.csv` holds the coverage curve at its checkpoints, and `cleanup.json`
is the reviewed ledger that made v0.2.0 from the source (Russian words dropped,
case forms merged into their lemmas, mislabeled names rejoined), with
`crosswalk.csv` mapping every v0.1.0 rank to its v0.2.0 rank. The source is the
UberText 2.0 lemma frequency dictionary (lang-uk), whose largest component is
news, so civic and geographic words rank higher than they would in speech.

Every `rank` in this directory is a v0.2.0 rank unless a folder's README says
otherwise. `v0.1.0/` stays published and frozen, with the `docs` column v0.2.0
dropped, for anyone citing a figure from before the cleanup; join it only to
itself, or go through `v0.2.0/crosswalk.csv`.

## How the files join

- **Join on `rank`.** It is the one key every rank-bearing table shares with
  `v0.2.0/lemmas.csv`. `(lemma, pos)` is not safe everywhere: `paradigms/`
  records the part of speech of the Wiktionary entry it matched, which differs
  from the list's tag on some rows.
- **Three tables join by spelling, not part of speech:** `borodin-a1/`,
  `borodin-a2/` and the parts in `b1-extension/multiword-parts.csv`. Their
  level column is the easiest level of any reading of the spelling. For a
  level that belongs to one reading, join `rank` to `validated-cefr/lemmas.csv`.
- **`genre-split/` has its own ranks.** They come from two separate
  fiction and news lists built with a different lemmatizer, and are comparable
  only to each other, never to `v0.2.0/`.
- **Validated and predicted levels never mix.** `validated-cefr/` holds the
  expert levels; `predicted-cefr/` holds model output for the remaining lemmas.
  Together they account for all 12,000 lemmas.

## Where else to get them

- **This folder, on the web:** https://uavocab.org/downloads/ukrainian-frequency/
  (the study that explains every file: https://uavocab.org/research).
- **On GitHub, to clone or fork:** https://github.com/jake0lawrence/UA-Vocab
  keeps these files at this same path, `downloads/ukrainian-frequency/`, with
  the Zenodo datasheets and the Python package.
- **In Python:** `pip install uavocab` (https://pypi.org/project/uavocab/)
  ships the list, the validated levels, the two Borodin minimums, the
  crosswalk, the B1 aspect, government and collocation tables and the stress
  column as Parquet, generated from the files here. It ships no predicted level.
- **Archived with a DOI (Zenodo):** the list, https://doi.org/10.5281/zenodo.22823134,
  and the stress column, https://doi.org/10.5281/zenodo.23092388. The
  PULS-derived folders wait on the profile's published license notice.

## Where the files are used

- **The study**, https://uavocab.org/research (and the `/ua` twin), renders
  every thread from these tables, re-derives the headline figures live, and
  links each folder as a download.
- **The Lightning Course** (https://uavocab.org/lightning) builds its flashcard
  deck in `v0.1.0` rank order, annotates calques from `derussification/`, and
  opens a forms and audio panel from `paradigms/`.
- **The text profiler** (https://uavocab.org/research/profiler) reads the list,
  the validated levels, the Borodin known-word sets and the paradigm forms (to
  map an inflected word back to its lemma), shipped as `profiler/`.
- **The vocabulary-size test** (https://uavocab.org/research/vocab-test) draws
  real lemmas from each of the list's twelve frequency bands and mixes in
  constructed pseudowords, shipped as `vocab-test/`.
- **The word pages** on https://uavocab.org/words carry the stress, the
  validated level and the rank from these tables.

## Integrity

Versioned folders (`v0.1.0/`, `v0.2.0/`, `stress/`, `minimums-crosswalk/`,
`profiler/`, `vocab-test/`) carry `manifest.json` and `SHA256SUMS`; check a
folder with `sha256sum -c SHA256SUMS` from inside it, or every folder at once
with `python3 scripts/verify.py` in the GitHub repository. A released version is
never edited: a correction is a new version folder, and `latest.json` moves.
Every table is read in the study's CI with a strict CSV parser, checked against
the thread-01 rank, lemma and validated level, and failed if a README quotes a
column list that is not its file's header.
