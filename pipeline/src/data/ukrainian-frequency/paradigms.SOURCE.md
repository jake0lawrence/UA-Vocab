# Audio and paradigms source (thread 04)

The thread-04 artifacts (the generated
`src/lib/ukrainian-frequency/paradigms.data.mjs` and the public
`public/downloads/ukrainian-frequency/paradigms/{lemmas,forms}.csv`) are DERIVED,
not a source corpus. There is deliberately **no committed multi-MB `paradigms.json`**:
the two public CSVs are the committed full record and the open-data release at once.

## What it is

The top-12,000 lemmas of the thread-01 frequency list, each with its **inflection
paradigm** (declension / conjugation forms, stress marks included), its **IPA**,
and a **link to open native-speaker pronunciation audio** on Wikimedia Commons.
Coverage thins with rank (a rarer lemma is less likely to have a Wiktionary
entry), so the page grades it honestly rather than assuming it.

## Why it exists

Threads 01 to 03 operate on the bare lemma. A learner of a heavily inflected
language actually meets the lemma's forms, not its headword. Thread 04 attaches
the forms and the sound, and measures the inflection tax at the morphology level:
the inflecting lemmas in the top-12,000 expand to many times that many distinct
wordforms (the "inflection multiplier").

## Source and license

- **Source:** the open, machine-readable **Wiktionary extraction from
  [kaikki.org](https://kaikki.org/dictionary/Ukrainian/)** (Tatu Ylonen's
  `wiktextract`). Each entry's `forms` array is the Wiktionary declension /
  conjugation table; its `sounds` array carries the IPA and the Wikimedia Commons
  audio file. This is the exact source thread 04 names: open Wiktionary tables
  plus open pronunciation audio.
- **License:** Wiktionary content is **CC-BY-SA-3.0** (and GFDL); the Wikimedia
  Commons audio is CC-BY-SA. We redistribute the factual lemma-to-forms / IPA
  assignment and **link** (never re-host) the audio, attribute the source, and
  license these derived artifacts CC-BY-SA in turn.

## Honesty limits (all surfaced on the page)

- **Coverage is graded, not assumed.** Wiktionary does not have every lemma; the
  page reports the real percentages (paradigm / IPA / audio out of the 12,000).
- **Forms are verbatim.** Stress marks kept; romanized forms, placeholders (`-`),
  and template rows dropped. Nothing is generated, and derivational spin-offs (a
  relational adjective off a noun, a diminutive) are carried but not counted as
  inflection, so the multiplier measures declension / conjugation only.
- **Audio is linked, not re-hosted.** Every audio URL points at Wikimedia Commons.
- **Lemma-string + POS-family join, apostrophe-folded.** Matched to our list by
  lemma string with a part-of-speech-family sanity filter; the best-covered
  matching entry wins. The two sides spell the apostrophe differently (the list
  U+2019, Wiktionary U+02BC or an ASCII quote), so the key is folded to one
  glyph before matching. Keyed raw, the join silently dropped 156 of the 158
  apostrophe lemmas on the list. The fold applies to the key ONLY: the lemma
  column keeps the list's own spelling and the forms stay Wiktionary's own.
- **Covers the whole top-12,000 list.** The first release covered the top-2,000;
  it was then deepened to the full list (coverage graded, thinning with rank).

## Reproduce

Not run in the build or CI (it needs the ~277 MB kaikki Ukrainian dump, which is
not vendored). Stream it, so nothing huge lands on disk. kaikki serves only the
current edition, so a re-run always picks up whatever is published that day;
`--dump-date` is required and records which one, so drift between runs is
legible instead of silent (the same contract `extract-wiktionary-families.py`
uses). Read it from the dump's `Last-Modified` header:

```bash
curl -sSI https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl
curl -sS https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl \
  | python3 scripts/ukrainian-frequency/extract-paradigms.py --stdin --dump-date 2026-09-20
```

The committed tier is the 2026-09-20 edition. A spelling the list holds under
several parts of speech gets one entry per part-of-speech family, each stamped
on the rank of the list row of that family (before 2026-09-23 one entry was
stamped on the spelling's best rank, so rank 222, the conjunction ніж, carried
the noun "knife"). To recompute the stamping and every derived figure without
the dump, read the chosen entries back out of the committed CSVs:

```bash
python3 scripts/ukrainian-frequency/extract-paradigms.py --rebuild
```

Then commit the regenerated `paradigms.data.mjs`, `lemmas.csv`, and the gzipped
`forms.csv.gz` (the raw forms CSV is ~14 MB, so it ships gzipped like the repo's
`uk-lexicon-dict_uk.txt.gz`; `mtime=0` keeps it byte-stable). CI re-verifies them
against each other and against the seed (`__tests__/paradigms.test.js`), not
against the dump.
