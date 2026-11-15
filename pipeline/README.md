# The pipeline

How the releases in [`downloads/ukrainian-frequency/`](../downloads/ukrainian-frequency)
are made, as far as it can be open: every builder and extractor, the source
snapshots whose licenses let them travel, and a runner that re-derives the
releases whose inputs are all here. The layout is the study's own
(`scripts/`, `src/lib/`, `src/data/`), so every path in the code reads as
written. Nothing here is edited by hand; it is generated from the study's
source repository with the rest of this one.

## Rebuild

```
node pipeline/rebuild.mjs --check
```

re-derives each release below from `src/data/` and compares it, byte for byte,
with what is in `downloads/` and the committed tier in `src/lib/`. Node 20 or
later, no `npm install`: the builders use only Node's standard library. Without
`--check` it writes, so a fork can change an input (a stress override, a list
decision) and rebuild the release from it; then `python3 scripts/verify.py`
checks the result against its own new checksums. The runner links
`pipeline/public/downloads/ukrainian-frequency` to `downloads/ukrainian-frequency`
first, since that is where the builders look. The same check runs on every
push ([verify.yml](../.github/workflows/verify.yml)).

| Builder | Re-derives |
|---|---|
| [`build-release.mjs`](scripts/ukrainian-frequency/build-release.mjs) | the frequency list, v0.1.0 and v0.2.0 (lemmas, coverage, Anki seed) |
| [`build-stress.mjs`](scripts/ukrainian-frequency/build-stress.mjs) | the word-stress column (stress/) |
| [`build-dictionary.mjs`](scripts/ukrainian-frequency/build-dictionary.mjs) | the dictionary's lookup tier, read against the stress column |
| [`build-stress-audit.mjs`](scripts/ukrainian-frequency/build-stress-audit.mjs) | the stress audit sample (348 items in 4 strata) |

## Code whose input cannot travel

These build released files too, and their code is here, but one input each is
withheld (see the last table), so they do not run from this repository.

| Script | Builds | Needs |
|---|---|---|
| [`build-minimums.mjs`](scripts/ukrainian-frequency/build-minimums.mjs) | the crosswalk of the Borodin minimums against the validated profile (minimums-crosswalk/) | `puls-cefr.raw.csv`, the full PULS harvest, made by permission and not redistributed; the profile is at puls.peremova.org |
| [`build-profiler.mjs`](scripts/ukrainian-frequency/build-profiler.mjs) | the text profiler's lexicon bundle (profiler/) | `b1-aspect.json`, whose verb rows carry the VESUM lexicon's aspect tag beside the PULS and Wiktionary ones |
| [`build-vocab-test.mjs`](scripts/ukrainian-frequency/build-vocab-test.mjs) | the vocabulary-size test's item bank (vocab-test/) | `uk-lexicon-dict_uk.txt.gz`, 333,097 headwords of the dict_uk project used to reject pseudowords that are real words; dict_uk is VESUM's source, so it is not redistributed here (extraction recipe in its SOURCE.md) |

## Extractors

One-time steps that made the committed snapshots in `src/data/` from upstream
dumps, which are large and are not vendored. Each script's header gives its
command line and its exact inputs; each snapshot's `*.SOURCE.md` says where it
came from, when, and under what license. They need Python 3 and, where named,
the packages it lists.

| Script | Makes | Needs |
|---|---|---|
| [`fetch-dmk-dictionary.mjs`](scripts/ukrainian-frequency/fetch-dmk-dictionary.mjs) | fetches the dmklinger/ukrainian dictionary and writes `dmk-dictionary.json` | network access to github.com/dmklinger/ukrainian |
| [`audit-list.py`](scripts/ukrainian-frequency/audit-list.py) | the v0.2.0 list audit (evidence pass) | UberText 2.0's lemma frequency dictionary (`ubertext_freq.csv.xz`, lang.org.ua) and pymorphy3 with pymorphy3-dicts-uk; its output `list-audit.json` carries VESUM classes and is withheld |
| [`build-genre-split.py`](scripts/ukrainian-frequency/build-genre-split.py) | the fiction against news genre split | the two per-genre lemma lists `genre-freq.py` writes (about 19 MB each, not committed) |
| [`build-list-v2.py`](scripts/ukrainian-frequency/build-list-v2.py) | the v0.2.0 seed and its crosswalk from v0.1.0 | `ubertext_freq.csv.xz` (lang.org.ua) and pymorphy3 with pymorphy3-dicts-uk for the name rule; the reviewed ledger `list-cleanup.json` is here |
| [`count-homographs.py`](scripts/ukrainian-frequency/count-homographs.py) | corpus counts for stress homographs (`stress-homographs.json`) | the kaikki.org Ukrainian dump, the five UberText 2.0 subcorpora, and optionally the hosted lemmatizer |
| [`extract-b1-aspect.py`](scripts/ukrainian-frequency/extract-b1-aspect.py) | the B1 aspect relation table | the kaikki.org verb entries, `ubertext_freq.csv.xz`, pymorphy3-dicts-uk, and `puls-cefr.raw.csv` (withheld) |
| [`extract-b1-multiword.py`](scripts/ukrainian-frequency/extract-b1-multiword.py) | the B1 multiword table | a UberText 2.0 Wikipedia slice, pymorphy3-dicts-uk, and the PARSEME 2.0 Ukrainian corpus (CC BY-NC-SA, read one way, never vendored) |
| [`extract-b1-usage.py`](scripts/ukrainian-frequency/extract-b1-usage.py) | case government, collocations and examples for the B1 set | `b1-usage.snapshot.json` (here), LanguageTool's Ukrainian replacement tables, and pymorphy3-dicts-uk |
| [`extract-borodin-a1.py`](scripts/ukrainian-frequency/extract-borodin-a1.py) | the Borodin A1 minimum joined onto the list | the snapshots here (`borodin-a1.raw.json`, `puls-cefr.json`, `cefr-overlay.json`) and the v0.1.0 lemmas |
| [`extract-borodin-a2.py`](scripts/ukrainian-frequency/extract-borodin-a2.py) | the Borodin and Lazarenko A2 minimum joined onto the list | the snapshots here (`borodin-a2.raw.json`, `borodin-a1.raw.json`, `puls-cefr.json`, `cefr-overlay.json`) and the v0.1.0 lemmas |
| [`extract-cefr-overlay.py`](scripts/ukrainian-frequency/extract-cefr-overlay.py) | the open, unvalidated CEFR overlay from the learn-ukrainian course | a clone of github.com/learn-ukrainian/learn-ukrainian.github.io |
| [`extract-derussification.py`](scripts/ukrainian-frequency/extract-derussification.py) | the derussification table | LanguageTool's Ukrainian replacement tables (LGPL-2.1, github.com/languagetool-org/languagetool) |
| [`extract-paradigms.py`](scripts/ukrainian-frequency/extract-paradigms.py) | paradigms, IPA and open audio links | the kaikki.org Ukrainian dump (about 255 MB) |
| [`extract-puls-cefr-overlay.py`](scripts/ukrainian-frequency/extract-puls-cefr-overlay.py) | the validated CEFR overlay (validated-cefr/) | `puls-cefr.raw.csv` (withheld; the profile's authors at puls.peremova.org) |
| [`extract-source.py`](scripts/ukrainian-frequency/extract-source.py) | the committed seed `ubertext-lemmas-top12k.json` | `ubertext_freq.csv.xz` from lang.org.ua (UberText 2.0, CC BY 4.0) |
| [`extract-stress.py`](scripts/ukrainian-frequency/extract-stress.py) | the reviewed stress snapshot `stress.json` | the ukrainian-word-stress dictionary (lang-uk, MIT), the kaikki.org dump, the uk.wiktionary pages-articles dump and uk.wikipedia lead sentences |
| [`extract-wiktionary-families.py`](scripts/ukrainian-frequency/extract-wiktionary-families.py) | the Wiktionary word-family graph | the kaikki.org Ukrainian dump |
| [`fetch-profiler-validation.py`](scripts/ukrainian-frequency/fetch-profiler-validation.py) | the profiler's validation texts (`profiler-validation.json`) | network access to learn-ukrainian.github.io (CC BY-SA 4.0) |
| [`fold-worklist-gold.py`](scripts/ukrainian-frequency/fold-worklist-gold.py) | folds a filled gold worklist into `cefr-gold.json` | a worklist filled by hand from PULS (`gen-gold-worklist.py` writes the empty one) |
| [`gapfill-model.py`](scripts/ukrainian-frequency/gapfill-model.py) | the predicted CEFR levels (predicted-cefr/) | `predicted-cefr.snapshot.json` (withheld: VESUM features), numpy, wordfreq and pymorphy3-dicts-uk |
| [`gen-gold-worklist.py`](scripts/ukrainian-frequency/gen-gold-worklist.py) | the gold-expansion worklist for a person to fill from PULS | the snapshots here (`cefr-gold.json`, `cefr-overlay.json`) |
| [`genre-freq.py`](scripts/ukrainian-frequency/genre-freq.py) | a lemma list from one UberText 2.0 subcorpus | a UberText 2.0 subcorpus (`.bz2`, lang.org.ua) |
| [`parse-b1-corpus.py`](scripts/ukrainian-frequency/parse-b1-corpus.py) | the dependency parse behind the B1 usage tables (`b1-usage.snapshot.json`) | UberText 2.0's Wikipedia subcorpus and spaCy's uk_core_news_sm |
| [`parse-borodin-a2-pdf.py`](scripts/ukrainian-frequency/parse-borodin-a2-pdf.py) | reads the A2 minimum out of its PDF (`borodin-a2.raw.json`) | the A2 volume, DOI 10.11584/opus4-1448 (CC BY 4.0) |
| [`relemmatize-b1-corpus.py`](scripts/ukrainian-frequency/relemmatize-b1-corpus.py) | the nlp_uk re-lemmatization measurement | nlp_uk with the VESUM dictionary; its output is withheld |

## What is withheld, and why

The walls the study keeps: the PARSEME corpus is read one way and never
redistributed; nothing derived from the VESUM dictionary leaves (its terms are
CC BY-NC-SA and the study does not relicense it); only the levels of the list's
own lemmas are redistributed from PULS, never the full harvest; no contact
details. The files below stay in the source repository, so the code above that
reads them documents what it needs rather than running here.

| Source snapshot | Why it is withheld |
|---|---|
| `list-audit.json` | the audit's evidence: pymorphy3 classes for every row, from VESUM; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `puls-cefr.raw.csv` | the full PULS harvest; only the list lemmas' levels are redistributed (puls-cefr.SOURCE.md) |
| `predicted-cefr.snapshot.json` | the model's feature snapshot, which includes VESUM lexicon features; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `b1-aspect.json` | its verb rows carry the VESUM lexicon's aspect tag (aspectVesum); VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `b1-aspect.ubertext-counts.json` | carries the VESUM lexicon's aspect per lemma; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `b1-aspect.vesum-readings.json` | VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `b1-multiword.json` | carries the PARSEME 2.0 validation read (CC BY-NC-SA), which is walled out of every release |
| `b1-multiword.parseme.json` | the PARSEME 2.0 read (CC BY-NC-SA), walled out of every release |
| `b1-multiword.part-lemmas.json` | the parts' lemmas from pymorphy3 over VESUM; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `b1-usage.relemmatize.json` | a sentence-by-sentence measurement through VESUM; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `uk-dimlex/attestation.json` | lemmatized through VESUM, and used only for an upstream note; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `uk-lexicon-dict_uk.txt.gz` | dict_uk headwords (VESUM's source project); not redistributed, see its SOURCE.md for the extraction recipe |
| `lemmatizer-roundtrip.json` | the hosted lemmatizer's round trip, VESUM output; VESUM (brown-uk/dict_uk) is CC BY-NC-SA and the study never redistributes it |
| `uk-wiktionary-presence.json` | an upstream worklist check; carries a contact address |
| `review-ledger.json` | the continuous review's ledger of production checks; operations |
| `review-baseline.json` | the continuous review's baseline; operations |
| `review-upstreams.json` | the continuous review's upstream watch list; operations |
| `reviewer-panel.json` | the review desk's panel description; not a derivation input |
| `stress-game-exclusions.json` | a game on the study's own site; not a derivation input |
| `zenodo.json` | published at registry/zenodo.json |

| Script | Why it is not here |
|---|---|
| `build-package.py` | published at scripts/build-package.py, where it reads downloads/ |
| `build-descriptors.mjs` | typesets the PDFs in downloads/ukrainian-frequency/descriptors/ from the Zenodo deposit bundle; deposit tooling, not derivation |
| `zenodo-deposit.mjs` | Zenodo deposit tooling (credentials, the private deposit engine); the datasheets and registry/zenodo.json are what it publishes |
| `build-stress-game.mjs` | builds a game for the study's own site from the course data |
| `review.mjs` | the continuous review that reads production against the source repository; operations |
| `review-on-deploy.mjs` | dispatches the continuous review after a deploy; operations |
| `lemmatizer-roundtrip.mjs` | drives the hosted lemmatizer, which runs VESUM server-side |
| `lemmatizer-cold-start.mjs` | drives the hosted lemmatizer, which runs VESUM server-side |
| `hf-cards.mjs` | drafts Hugging Face cards for the registry listings; outreach |
| `contrib-fetch-evidence.mjs` | drafts upstream worklists; outreach, nothing submitted from the repository |
| `contrib-fetch-ukwiktionary.mjs` | drafts upstream worklists; outreach, and it carries a contact address |
| `contrib-worklists.mjs` | drafts upstream worklists; outreach |
| `scrape-puls-cefr.py` | harvested the PULS profile by its authors' permission; neither the harvest nor the harvester is redistributed, so a fork asks the authors (puls.peremova.org) |
| `lookup-puls-levels.py` | looked up PULS entries by hand-picked worklist under the same permission; carries a contact address |

## Licenses

The code here is under the same terms as the `uavocab` package (CC BY-NC-SA
4.0; see [LICENSE.md](../LICENSE.md)). Each source snapshot carries its own
source's license, stated in its `*.SOURCE.md`: UberText 2.0 counts CC BY 4.0,
Wiktionary-derived tables CC BY-SA, the PULS levels CC BY-NC-SA 4.0 by the
authors' permission, the Borodin minimums CC BY 4.0, LanguageTool's tables
LGPL-2.1, UK-DiMLex MIT (its `LICENSE` beside it).
