# uavocab

The open Ukrainian vocabulary data behind [uavocab.org](https://uavocab.org),
installable and offline: the top-12,000 lemma frequency list over UberText 2.0,
the validated PULS CEFR overlay (A1 to C1), the Borodin A1 and A2 lexical
minimums, the crosswalk between the minimums and the profile, the B1
enrichment tables (aspect relations, case government, collocations), and a
per-lemma word-stress column. The study the data comes from, with its methods,
findings and tools, is [uavocab.org/research](https://uavocab.org/research).

```
pip install uavocab
```

```python
import uavocab
uavocab.lookup("п'ять")["level"]                       # 'A1', with rank, source and enrichment beside it
uavocab.lookup("орган")["stress"]                       # {'stress': 'о́рган', 'variants': ['о́рган', 'орга́н'], 'status': 'homograph', ...}
uavocab.coverage(["в", "школа", "йти"], "A2")["coverage"]  # share of tokens a validated-A2 learner knows
```

This package was published as `ukvocab` up to 0.4.1. It was renamed to match
the site it belongs to; `pip install ukvocab` still works and now installs
this package, and `import ukvocab` keeps working with a warning that names
the new import.

## Where everything is

| | |
|---|---|
| The study (methods, findings, tools) | https://uavocab.org/research |
| Every dataset, its license and how to cite it | https://uavocab.org/data |
| The release files (CSV, JSON, Anki, with SHA-256 sums) | https://uavocab.org/research#release |
| Every release file, the datasheets, and this package's source (fork it) | https://github.com/jake0lawrence/UA-Vocab |
| Archived copies with DOIs (Zenodo) | frequency list [10.5281/zenodo.22823134](https://doi.org/10.5281/zenodo.22823134), word stress [10.5281/zenodo.23092388](https://doi.org/10.5281/zenodo.23092388) |
| The lemmatizer matched to this list | https://uavocab.org/research/lemmatizer |
| PyPI | https://pypi.org/project/uavocab/ |

## What you get

| function | returns |
|---|---|
| `lookup(lemma, pos=None)` | one lemma: `level`, `level_source`, `rank`, the frequency figures, the `stress` (primary stressed form, accepted variants, resolution status and note), every other reading of the spelling, minimum membership, the crosswalk class, and the B1 `enrichment` (aspect partners, government, collocations); `None` when no table knows the string |
| `levels(lemmas)` | batch: input string to `{level, level_source, rank, pos, source}` |
| `coverage(lemmas, known_set)` | token coverage of a lemmatized text against a known set: a level (`"A2"` means every validated lemma at or below A2), `"borodin-a1"` / `"borodin-a2"`, an int N (top N of the list), or your own set of lemmas; reports the unknowns by frequency |
| `sources()` | version, snapshot date, license, attribution, citation and SHA-256 per dataset, the combined license and why, and what is deliberately not shipped |

Every return value carries the dataset, version and snapshot it came from.
Data is Parquet, loaded lazily on first use, never on import. The only
dependency is `pyarrow`.

Two things the package does not do, on purpose. It does not lemmatize: pass
lemmas in the UberText / VESUM convention (infinitive for verbs, nominative
singular for nouns); the site's `POST /api/lemmatize` is the hosted lemmatizer
matched to this list ([its contract](https://uavocab.org/research/lemmatizer)).
And it ships no predicted CEFR levels: only the profile's
validated levels are here, and a lemma the profile does not cover gets
`level: None` rather than a guess.

## Provenance and honesty

The data tier is generated from the site's published release files by
`scripts/build-package.py` in [the open repository](https://github.com/jake0lawrence/UA-Vocab),
which holds every release file too, and is never edited by hand; the tests assert that every table's row count and hash
match the published file exactly. `sources()` is the manifest that build
wrote. The PULS overlay is a dated snapshot (2026-07-23) of a profile that is
still being extended, redistributed with its authors' permission. The join
onto the frequency list is part-of-speech aware; ten declared cross-tag rules
recover the words the two tag conventions merely label differently, and each
row's `join` field says how it matched, so the strict join is one filter away.

## License

The combined package is **CC-BY-NC-SA 4.0**, because the PULS levels are
NonCommercial and share-alike at the authors' decision (2026-09-24) and they run
through most tables. The frequency list and the two Borodin minimums are CC-BY
4.0 on their own, and the government, collocation and stress tables CC-BY-SA
4.0; drop the PULS level columns and NonCommercial does not apply. `LICENSES.md` has the
per-dataset terms and every attribution.

## Citation

```
Lawrence, J. (2026). uavocab: the Ukrainian Frequency datasets (top-12,000 lemma
list, validated PULS CEFR overlay, Borodin A1/A2 minimums, crosswalk, B1
enrichment tables, word stress), version 0.5.0. https://uavocab.org/research

Upstream: Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern
Ukrainian at Scale. Proc. 2nd UNLP, ACL. | Synchak, O., Starko, V., Burak, M.,
Svystun, M. (2025). Corpus-Based Vocabulary Profiling for Ukrainian: From
Lexical Analysis to CEFR. eLex 2025; PULS, puls.peremova.org. | Borodin, K. and
Turkevych, O. 1000 i 1 slovo, A1. https://doi.org/10.18452/28236 | Borodin, K.
and Lazarenko, O. (2026). 1000 i 1 slovo, A2. https://doi.org/10.11584/opus4-1448
| Syvokon, O. and Chaplynskyi, D. (lang-uk). ukrainian-word-stress, MIT.
https://github.com/lang-uk/ukrainian-word-stress
```

Archived, DOI-minted copies of each dataset are listed in `sources()` under
`conceptDoi` once they exist (today the frequency list and the stress column;
the PULS-derived datasets wait on the profile's published license notice).
Cite the concept DOI for the dataset you used.
