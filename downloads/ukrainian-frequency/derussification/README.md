# Ukrainian Frequency, thread 03: the derussification pass

`lemmas.csv` lists the top-12,000 lemmas of modern Ukrainian (from thread 01,
the UberText 2.0 frequency list) that the open Ukrainian idiomatic-style tooling
flags, each paired with the native alternative the tooling recommends.

## Columns

| column | meaning |
|---|---|
| `rank` | the lemma's frequency rank on the thread-01 list (1 = most frequent) |
| `lemma` | the flagged form, as it appears on the frequency list |
| `pos` | Universal Dependencies part of speech |
| `tier` | `hard` (LanguageTool `replace.txt`) or `soft` (`replace_soft.txt`) |
| `suggestion` | the tooling's first recommended native alternative, verbatim |
| `swap` | where the native form sits: `off-list` (not in the top 12,000), `rarer` (on the list but less frequent than the flagged form), `commoner` (on the list and more frequent), or `phrase` (the recommendation is a construction, e.g. a relative clause, not one word) |

## Source and license

Flags and suggestions come from **LanguageTool's Ukrainian replacement tables**
(brown-uk / Andriy Rysin and contributors), the open Pravopysnyk-style layer
backed by the VESUM morphology. Those resources are **LGPL-2.1**; this derived
list carries the same notice.

## Honesty

This is an **unvalidated, prescriptive** signal: what an open style checker would
replace, not a settled linguistic verdict. Its core is derussification
(russianisms, surzhyk, calques) but its scope is broader than strictly-Russian
loans, and some entries are live usage debates. Proper-noun / orthographic fixes
are excluded. See `src/data/ukrainian-frequency/derussification.SOURCE.md` and the
page at `/research/ukrainian-frequency#derussification` for full method and limits.

## Where it fits

Join to `../v0.1.0/lemmas.csv` on `rank`. A lemma flagged under two parts of
speech has two rows (поліцейський is a NOUN at 1255 and an ADJ at 3296).

The finding is in the `swap` column: of the single-word swaps (every row except
`phrase`), most have the flagged form at least as common as the native one
(`rarer` or `off-list`), so a frequency-first course would teach the form a
style checker corrects. No flagged lemma sits in the top 1,000.

Used by the research page (`#derussification`) and by the Lightning Course
flashcards, which join this table to the card being studied by lemma and part
of speech and show the native alternative as a style note, labeled as the
tooling's opinion.
