# UA Vocab: open data for learning Ukrainian

The open data behind [uavocab.org](https://uavocab.org): a lemma-based frequency list of
modern Ukrainian (the 12,000 most frequent lemmas, ranked over the UberText 2.0
corpus), the stress of every one of those words, CEFR levels from the validated
PULS profile, the two published A1 and A2 lexical minimums and how they line up
with that profile, B1 tables for aspect, case government, collocations and
multiword expressions, and the rest of the Ukrainian Frequency study's
releases. Every file is here exactly as it was published, with its checksums,
its license and a README that says how it was made.

| | |
|---|---|
| The study: methods, findings, tools | https://uavocab.org/research |
| Look up any word | https://uavocab.org/words |
| Every dataset, its license and how to cite it | https://uavocab.org/data |
| Python: `pip install uavocab` | https://pypi.org/project/uavocab/ |
| Archived with a DOI (Zenodo) | the frequency list [10.5281/zenodo.22823134](https://doi.org/10.5281/zenodo.22823134), the validated CEFR levels [10.5281/zenodo.24388000](https://doi.org/10.5281/zenodo.24388000), the B1 tables [10.5281/zenodo.24388339](https://doi.org/10.5281/zenodo.24388339), the word-stress column [10.5281/zenodo.23092388](https://doi.org/10.5281/zenodo.23092388) |

## Get the data

- **Clone or download this repository.** Everything is in
  [`downloads/ukrainian-frequency/`](downloads/ukrainian-frequency), the same
  path uavocab.org serves it at
  (https://uavocab.org/downloads/ukrainian-frequency/README.md). Plain CSV and JSON, UTF-8,
  plus Anki seeds. Start with [the map](downloads/ukrainian-frequency/README.md):
  what each folder answers, and how the tables join (on `rank`).
- **In Python.** `pip install uavocab`, then `uavocab.lookup("мова")` for one
  word's rank, level, stress and B1 enrichment, or `uavocab.coverage(...)` for
  how much of a text a learner at a level knows. The package is
  [`python/uavocab/`](python/uavocab); its data is generated from the release
  files here and checked byte for byte.
- **A fixed version to cite.** Each released folder is frozen. The list and the
  stress column are also archived on Zenodo with a DOI per version.

## What is here

| Folder | Question it answers | Main file | Rows | License |
|---|---|---|---|---|
| [`v0.2.0/`](downloads/ukrainian-frequency/v0.2.0) | What should a learner meet first? (`v0.1.0/` is the frozen first release) | `lemmas.csv` | 12,000 | CC-BY-4.0 |
| [`stress/`](downloads/ukrainian-frequency/stress) | Where does the stress fall in each of those lemmas? | `v1.0.2/stress.csv` | 12,000 | CC-BY-SA-4.0 |
| [`validated-cefr/`](downloads/ukrainian-frequency/validated-cefr) | What CEFR level is this word, according to the one corpus-validated profile? | `lemmas.csv` | 6,403 | CC-BY-NC-SA-4.0 (by permission) |
| [`predicted-cefr/`](downloads/ukrainian-frequency/predicted-cefr) | A model's best guess for the words the profile does not label | `predictions.csv` | 5,597 | CC-BY-NC-SA-4.0 |
| [`cefr-overlay/`](downloads/ukrainian-frequency/cefr-overlay) | When does one open course teach the word? (experimental, a cross-check only) | `lemmas.csv` | 2,326 | CC-BY-SA-4.0 |
| [`borodin-a1/`](downloads/ukrainian-frequency/borodin-a1) | How does the published A1 lexical minimum compare with the list? | `lemmas.csv` | 929 | CC-BY-4.0 |
| [`borodin-a2/`](downloads/ukrainian-frequency/borodin-a2) | The same for the A2 minimum, plus which topics the list misses | `lemmas.csv`, `themes.csv` | 1,000 | CC-BY-4.0 |
| [`minimums-crosswalk/`](downloads/ukrainian-frequency/minimums-crosswalk) | Where do the two minimums and the validated profile agree or disagree? | `v1.2.0/crosswalk.csv` | 10,366 | CC-BY-NC-SA-4.0 |
| [`genre-split/`](downloads/ukrainian-frequency/genre-split) | Is an A2 word missing because it is rare, or because the corpus is news? | `entries.csv`, `themes.csv` | 936 | CC-BY-4.0 inputs |
| [`derussification/`](downloads/ukrainian-frequency/derussification) | Which common words would an open style checker replace, and with what? | `lemmas.csv` | 87 | LGPL-2.1 |
| [`paradigms/`](downloads/ukrainian-frequency/paradigms) | How does the word sound, and what forms will a reader actually meet? | `lemmas.csv`, `forms.csv.gz` | 9,269 | CC-BY-SA-3.0 |
| [`wiktionary-families/`](downloads/ukrainian-frequency/wiktionary-families) | Which list words are derivational kin? | `families.csv`, `edges.csv` | 11,056 / 14,975 | CC-BY-NC-SA-4.0 (CC-BY-SA without the level column) |
| [`b1-extension/`](downloads/ukrainian-frequency/b1-extension) | Aspect, motion verbs, government, collocations, examples and multiword expressions for validated B1 | seven CSVs |  | CC-BY-NC-SA-4.0 where a level column is present; CC-BY-SA-4.0 for the rest |
| [`profiler/`](downloads/ukrainian-frequency/profiler) | The text profiler's lexicon and form index (JSON, fetched by the page) | `v1.2.0/lexicon.json` |  | CC-BY-NC-SA-4.0 (see its manifest) |
| [`vocab-test/`](downloads/ukrainian-frequency/vocab-test) | The vocabulary-size test's item bank: 60 real lemmas and 60 pseudowords across the 12 frequency bands (JSON) | `v1.2.0/items.json` |  | CC-BY-4.0 (see its manifest) |
| [`descriptors/`](downloads/ukrainian-frequency/descriptors) | How was each archived dataset built, and how should it be cited? A typeset data descriptor (PDF) per dataset with a Zenodo DOI | `frequency-v0.2.0.pdf`, `stress-v1.0.2.pdf` |  | Each under the license of the dataset it describes |

Versioned folders keep every release (`v0.1.0/` and `v0.2.0/` for the list,
`stress/v1.0.0/` to `stress/v1.0.2/` and so on), and each has a
`latest.json` naming the current one. The list's current release is
`v0.2.0`, and almost every table joins it on `rank`; the map names
the few that join by spelling or carry ranks of their own.

```
downloads/ukrainian-frequency/   every release, as published
python/uavocab/                  the Python package (PyPI: uavocab)
python/ukvocab/                  its old name, kept installable
datasheets/                      the Zenodo datasheet of each dataset
registry/zenodo.json             the DOIs minted so far
scripts/verify.py                check every release against its checksums
scripts/build-package.py         rebuild the package's data from the releases
pipeline/                        how the releases are made: builders, extractors,
                                 the open source snapshots, rebuild.mjs
```

## Check it

```
python3 scripts/verify.py
```

checks every file in every versioned folder against its `SHA256SUMS` and
`manifest.json`, with nothing but the Python standard library.

```
node pipeline/rebuild.mjs --check
```

re-derives 4 releases (the frequency list, the stress column, the
dictionary tier, the stress audit sample) from the source snapshots in
[`pipeline/`](pipeline/README.md) and compares them byte for byte with what
is here. Both checks, the package rebuild and the package tests run on every
push ([.github/workflows/verify.yml](.github/workflows/verify.yml)).

## Releases

The Python packages are published to PyPI from this repository, by hand, with
[.github/workflows/publish.yml](.github/workflows/publish.yml). It refuses to
upload until every release matches its checksums, the package data rebuilds
byte for byte from `downloads/`, and the package's tests pass against the
installed wheel. PyPI's trusted publishing ties each release on
https://pypi.org/project/uavocab/ to the run here that built it, so anyone can see exactly which commit
and checks produced it.

## Licenses

The data carries several licenses, because its tables are built over sources
with different terms; each folder's README is authoritative for its files and
[LICENSE.md](LICENSE.md) is the summary. In short: the frequency list, the
Borodin minimums and the vocabulary test are CC BY 4.0; the stress column and
the Wiktionary-derived tables CC BY-SA; anything that carries a CEFR level from
the PULS profile is CC BY-NC-SA 4.0, the terms its authors chose, so drop those
columns and NonCommercial no longer applies. The derussification table carries
LanguageTool's LGPL-2.1.

## Cite

Cite the dataset you used by its Zenodo DOI (the frequency list [10.5281/zenodo.22823134](https://doi.org/10.5281/zenodo.22823134), the validated CEFR levels [10.5281/zenodo.24388000](https://doi.org/10.5281/zenodo.24388000), the B1 tables [10.5281/zenodo.24388339](https://doi.org/10.5281/zenodo.24388339), the word-stress column [10.5281/zenodo.23092388](https://doi.org/10.5281/zenodo.23092388)), or the study:

```
Lawrence, J. (2026). Ukrainian Frequency: a lemma-based, coverage-graded open frequency list (v0.2.0). uavocab.org/research. Derived from UberText 2.0 (Chaplynskyi, 2023).
```

[CITATION.cff](CITATION.cff) has the same in machine-readable form (GitHub's
"Cite this repository" button reads it), and each folder's README names the
upstream sources it owes credit to: lang-uk's UberText 2.0 and
ukrainian-word-stress, the PULS profile (Synchak, Starko, Burak, Svystun and
others), the Borodin A1 and A2 minimums, Wiktionary, LanguageTool.

## Corrections, forks and how this repository is made

Corrections are welcome as issues; see [CONTRIBUTING.md](CONTRIBUTING.md).
Fork freely within each file's license.

This repository is generated from the study's source repository on each
release: the data files are copied byte for byte from the releases (only the
HTML browse pages are left out), and the packages are published to PyPI from
here. The pipeline that builds the releases is in
[`pipeline/`](pipeline/README.md) as far as it can be open: every builder
and extractor, and every source snapshot whose license lets it travel. What
stays behind is named there with the reason, file by file: the raw PULS
harvest, anything derived from the VESUM dictionary, the PARSEME read, and the
operations around the study (its production review, its Zenodo tooling).

Edited by Jake Lawrence. Published by [UA Vocab](https://uavocab.org).
