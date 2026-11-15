# Licenses

This repository holds data under several licenses, because its tables are
built over sources with different terms. **Each folder's README is
authoritative for its own files**; this page is the summary.

## The data, by folder

| Folder | License |
|---|---|
| [`v0.2.0/`](downloads/ukrainian-frequency/v0.2.0) | CC-BY-4.0 |
| [`stress/`](downloads/ukrainian-frequency/stress) | CC-BY-SA-4.0 |
| [`validated-cefr/`](downloads/ukrainian-frequency/validated-cefr) | CC-BY-NC-SA-4.0 (by permission) |
| [`predicted-cefr/`](downloads/ukrainian-frequency/predicted-cefr) | CC-BY-NC-SA-4.0 |
| [`cefr-overlay/`](downloads/ukrainian-frequency/cefr-overlay) | CC-BY-SA-4.0 |
| [`borodin-a1/`](downloads/ukrainian-frequency/borodin-a1) | CC-BY-4.0 |
| [`borodin-a2/`](downloads/ukrainian-frequency/borodin-a2) | CC-BY-4.0 |
| [`minimums-crosswalk/`](downloads/ukrainian-frequency/minimums-crosswalk) | CC-BY-NC-SA-4.0 |
| [`genre-split/`](downloads/ukrainian-frequency/genre-split) | CC-BY-4.0 inputs |
| [`derussification/`](downloads/ukrainian-frequency/derussification) | LGPL-2.1 |
| [`paradigms/`](downloads/ukrainian-frequency/paradigms) | CC-BY-SA-3.0 |
| [`wiktionary-families/`](downloads/ukrainian-frequency/wiktionary-families) | CC-BY-NC-SA-4.0 (CC-BY-SA without the level column) |
| [`b1-extension/`](downloads/ukrainian-frequency/b1-extension) | CC-BY-NC-SA-4.0 where a level column is present; CC-BY-SA-4.0 for the rest |
| [`profiler/`](downloads/ukrainian-frequency/profiler) | CC-BY-NC-SA-4.0 (see its manifest) |
| [`vocab-test/`](downloads/ukrainian-frequency/vocab-test) | CC-BY-4.0 (see its manifest) |
| [`descriptors/`](downloads/ukrainian-frequency/descriptors) | Each under the license of the dataset it describes |

**The PULS levels are CC BY-NC-SA 4.0.** Every file that carries a level from the
Ukrainian Vocabulary Profile (PULS) is licensed CC-BY-NC-SA-4.0 as a whole, the
terms its authors decided on (O. Synchak, 2026-09-24); columns from other sources
keep their own licenses, so a file with its level column dropped owes only what
those columns owe. Frozen bundles from before that date (`minimums-crosswalk/v1.0.0`
and `v1.1.0`, `profiler/v1.0.0` to `v1.1.0`) are kept byte-identical and still
read CC-BY-SA in their own manifests; that marking is superseded and the levels
in them are under the same NonCommercial terms. Cite the profile as its authors
ask: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.

## The Python packages and the scripts

`python/uavocab/` is distributed as a whole under CC BY-NC-SA 4.0, because
PULS levels run through most of its tables;
[python/uavocab/LICENSES.md](python/uavocab/LICENSES.md) gives every dataset's
own license and attribution. Its code is under the same terms, to keep one
license on the wheel. `python/ukvocab/` (a re-export with no data) and the two
scripts in `scripts/` are under the same terms as `python/uavocab/`.

## The datasheets and READMEs

Each datasheet in `datasheets/` and each README in `downloads/` describes one
dataset and is under that dataset's license.

The license texts: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/;
CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/; CC BY-SA 3.0,
https://creativecommons.org/licenses/by-sa/3.0/; CC BY-NC-SA 4.0,
https://creativecommons.org/licenses/by-nc-sa/4.0/; LGPL-2.1,
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
