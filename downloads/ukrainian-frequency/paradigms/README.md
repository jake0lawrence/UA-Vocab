# Ukrainian Frequency, thread 04: audio and paradigms

The top-12,000 lemmas of modern Ukrainian (from thread 01, the UberText 2.0
frequency list), each with its inflection paradigm, IPA, and a link to open
native-speaker pronunciation audio on Wikimedia Commons. Coverage thins with rank
(a rarer lemma is less likely to have a Wiktionary entry); the page grades it.

Two files:

## `lemmas.csv` (one row per lemma)

| column | meaning |
|---|---|
| `rank` | the lemma's frequency rank on the thread-01 list (1 = most frequent) |
| `lemma` | the dictionary form |
| `pos` | Universal Dependencies part of speech |
| `ipa` | IPA transcription from Wiktionary (empty if none) |
| `form_count` | number of distinct inflected wordforms (the declension / conjugation) |
| `audio_url` | link to open Wikimedia Commons pronunciation audio (empty if none) |

## `forms.csv.gz` (gzipped; one row per wordform)

The raw CSV is about 14 MB, so it ships gzipped. Decompress with `gunzip -k
forms.csv.gz` (or any gzip tool).


| column | meaning |
|---|---|
| `rank` | the lemma's frequency rank |
| `lemma` | the dictionary form |
| `pos` | Universal Dependencies part of speech |
| `form` | the inflected form, stress marks included |
| `tags` | space-separated grammatical tags (case, number, gender, person, tense, aspect, mood) |
| `inflectional` | `1` if the form is a declension / conjugation form counted toward `form_count`, `0` if it is a derivational spin-off (a relational adjective, a diminutive) |

## Source and license

Forms, IPA, and audio links come from the open, machine-readable **Wiktionary
extraction at [kaikki.org](https://kaikki.org/dictionary/Ukrainian/)**
(`wiktextract`). Wiktionary content is **CC-BY-SA-3.0** (and GFDL); the Wikimedia
Commons audio is CC-BY-SA. This derived release carries the same notice, and the
audio is **linked, never re-hosted**.

## Honesty

Coverage is **graded, not assumed**: not every lemma has a Wiktionary paradigm,
IPA, or audio, and the page reports the real percentages. Forms are Wiktionary's
own, verbatim. See `src/data/ukrainian-frequency/paradigms.SOURCE.md` and the page
at `/research/ukrainian-frequency#paradigms` for full method and limits.

## Joining it to the list

Join on `rank`, not on `(lemma, pos)`. The `pos` column is the part of speech
of the Wiktionary entry the join matched, and it differs from the frequency
list's tag on some rows (не is ADV here and PART on the list; що is CCONJ here
and SCONJ there).

Known defect: the join stamps a spelling's best-ranked row whatever part of
speech it matched, so a homograph can carry the other reading's paradigm. Rank
222 ніж ("than") carries the paradigm of ніж ("knife"), and the text profiler
reads ножем as the conjunction. It is held by a ratchet in
`src/app/research/ukrainian-frequency/__tests__/downloads-integrity.test.js`
until the join is fixed.

## Where it fits

- The text profiler reads `forms.csv.gz` directly to map every inflected form
  back to its lemma (року, роки and році all count as рік).
- The Lightning Course flashcards open a forms and audio panel built from both
  files, fetched on first open.
- The research page (`#paradigms`) grades the coverage by rank band and
  reports the forms per lemma by part of speech.
