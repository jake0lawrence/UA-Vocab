# CEFR overlay source (thread 02, experimental)

`cefr-overlay.json` (and the generated `src/lib/ukrainian-frequency/cefr-overlay.data.mjs`
plus the public `public/downloads/ukrainian-frequency/cefr-overlay/lemmas.csv`)
is a DERIVED artifact, not a source corpus.

## What it is

An **experimental, unvalidated** CEFR overlay on the thread-01 frequency list.
For each of the top-12,000 lemmas that also appears in an open Ukrainian course,
it records the lowest CEFR course level whose lessons introduce that lemma. It is
a rough teaching-order signal, not a proficiency label.

## Why it exists

The one corpus-**validated** CEFR profile for Ukrainian (Synchak et al. 2025, the
PULS platform) is browse-only and cannot be joined onto our list (see `cefr.mjs`).
This overlay is the honest complement: an **open, joinable, but unvalidated**
signal. The contrast between the two is the point of thread 02.

## Source and license

- **Source:** the [learn-ukrainian](https://github.com/learn-ukrainian/learn-ukrainian.github.io)
  open course by Krisztian Koos. Its per-lesson vocabulary lives under
  `curriculum/l2-uk-en/<level>/<module>/vocabulary.yaml`, with the CEFR level in
  the path. The course vocabulary is an **expert selection based on Ukraine's
  2024 State Standard for Ukrainian as a Foreign Language**, not corpus-frequency
  validated.
- **License:** the learn-ukrainian curriculum content is **CC-BY-SA 4.0**. We
  redistribute only the factual lemma-to-level assignment (never the course's
  translations, examples, or prose), attribute the source, and license these
  derived overlay artifacts **CC-BY-SA 4.0** in turn. (Thread 01's own release
  stays CC-BY-4.0; only this overlay is share-alike, because its source is.)

## Honesty limits (all surfaced on the page)

- **Unvalidated.** Expert/course selection, not a corpus-validated profile.
- **First-occurrence heuristic.** A lemma's level is the first course lesson that
  introduces it, which can misplace a word taught early in a specific context.
- **Reaches B2 only.** The course's populated CEFR vocabulary stops at B2; C1/C2
  carry no labels here.
- **Lemma-string join.** Matched to our list by exact lemma string; a handful of
  entries may be wordforms rather than strict lemmas.

## Reproduce

Not run in the build or CI (it needs a full clone of the external course repo).
To refresh:

```bash
git clone --depth 1 https://github.com/learn-ukrainian/learn-ukrainian.github.io.git /tmp/learn-ukrainian
python3 scripts/ukrainian-frequency/extract-cefr-overlay.py --learn-ukrainian /tmp/learn-ukrainian
```

Then commit the three regenerated artifacts. CI re-verifies them against each
other (`__tests__/cefr.test.js`), not against the course clone.

Without `--learn-ukrainian` the script re-keys the committed join onto the
current seed by lemma and part of speech (the join's own key) and re-grades
it, which is how the overlay moved from list v0.1.0 to v0.2.0 without touching
the dated course snapshot: a row whose lemma left the list is dropped, every
other row takes its new rank.
