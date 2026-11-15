# Homograph corpus count source (thread 07, word stress)

`stress-homographs.json` here is DERIVED: the output of one run of
`scripts/ukrainian-frequency/count-homographs.py` on 2026-10-01 over the
committed `stress.json` snapshot, the kaikki.org extraction of en.wiktionary,
the site's own lemmatizer and the five UberText 2.0 subcorpora. The pure
builder (`src/lib/ukrainian-frequency/stress.mjs`, `applyHomographCounts`)
reads it; nothing in the build or CI touches the corpus.

## What it is

For each of the 88 in-scope homograph rows of the stress column
(one spelling, two words, two stresses: о́рган the body, орга́н the instrument;
прохо́дити to pass, проходи́ти to walk for a while), keyed by rank because пора
is on the list twice: both readings as en.wiktionary gives them, the inflected
forms that are spelled differently between the readings, how often those forms
occur in each subcorpus, and a decision. Where the count decides, the builder
makes that reading the primary, puts the counts on the row in `source` and
sets the status `homograph_corpus`. Where it cannot, the row stays `homograph`
with the first en.wiktionary entry as primary and the note says why.

## Why it exists

The stress column inherited each homograph's primary from the order of the
en.wiktionary entries, which is not evidence of anything. The list is built on
UberText 2.0, so the honest question is which reading that corpus uses more,
and for a pair whose paradigms differ somewhere in spelling the corpus can be
asked without a tagger: count the forms only one reading has.

## Method

1. **Readings.** Every en.wiktionary entry whose headword strips to the lemma,
   grouped by the stress position of the canonical headword. A lemma with one
   group is not decidable (kaikki carries one reading).
2. **Distinguishing forms.** A reading's forms minus the other reading's,
   minus the headword itself, minus any form that is itself a lemma on the
   list (an aspect partner kaikki lists under `forms` belongs to its own row),
   minus bare aspect-partner entries, minus any form the thread-04 paradigms
   file lists for another lemma (заходи: the imperative of заходи́ти and the
   plural of захід), minus any form or headword of any other en.wiktionary word
   (твердь: the noun against the imperative of тве́рдити), and, the check that
   catches the rest, minus any form the site's own lemmatizer (VESUM through
   `/api/lemmatize`, token mode) reads as any word but the lemma (зводи: the
   imperative of зводи́ти and the plural of звід; деревинка, a diminutive
   kaikki lists among the noun's forms). A form VESUM does not know keeps
   kaikki's word for it. 79 of 710 candidate forms were struck
   by the lemmatizer. A pair is decidable when every reading keeps at least
   one form.
3. **Count.** Each subcorpus is streamed once from lang.org.ua, lowercased,
   tokenized on Cyrillic letters and the apostrophe, and the distinguishing
   forms counted. Nothing of the corpus lands on disk.
4. **Decision.** The reading with more hits wins if it has at least 20 hits
   and 1.5 times the other reading's; otherwise the pair is "too close or too
   few" and stays `homograph`. The floor and the ratio are recorded in the
   JSON (`rule`).

## The run of 2026-10-01

| subcorpus | lines | tokens | complete |
|---|---|---|---|
| social | 4,494,263 | 38,336,994 | yes |
| court | 8,146,891 | 221,677,930 | yes |
| fiction | 17,025,440 | 190,861,656 | yes |
| wikipedia | 29,531,702 | 311,310,951 | yes |
| news | 126,213,181 | 1,571,216,132 | yes |

32 of 88 pairs are decidable by spelling; 31 were
decided, 4 of them away from the first en.wiktionary entry (сходи́ти over схо́дити, 653 against 225; тверди́ти over тве́рдити, 22 against 1; зго́дитися over згоди́тися, 183 against 19; виріза́ти over ви́різати, 1,307 against 787).
The pairs spelled alike in every cell (most noun pairs: о́рган / орга́н, за́мок /
замо́к) cannot be settled this way and say so on the row.

## Honesty limits

- **A surface count is not sense disambiguation.** It counts the cells where
  the two words part ways in spelling, mostly the imperative and the synthetic
  future of verbs, and the oblique cases of nouns with a different stem. A
  reading whose distinguishing cells are rare in text (an imperative) is
  under-measured against a reading whose cells are common (a participle),
  which is why the decision needs a margin and a floor rather than a bare
  majority, and why the counts are published beside every decision.
- **A cut stream is never passed off as the corpus.** Each subcorpus is
  read through a proxy, and an earlier run lost the end of the news stream
  (about 3.6 GB compressed); the script records the lines it did read and
  marks such a corpus `truncated` in the JSON. In the run above all five
  streams read to the end.
- **The floor is a floor, not confidence.** тверди́ти won on 22 hits against
  1 after the lemmatizer struck тве́рдити's own imperative (твердь, which is
  also the noun for the firmament); the rule passed, the counts are on the
  row, and a reader who wants more than twenty tokens can see exactly how
  little the corpus had to say.
- **Where the pipeline's reading and the ledger agree, both are kept.** The
  manual-decision ledger is applied after the count and wins where it
  disagrees. зводити had a goroh tiebreak before the corpus could be asked and
  the corpus agrees, so the row keeps the counted status and the ledger's
  evidence is appended to `source` rather than erasing the count.
- **Unknown forms are kaikki's word.** VESUM does not know a few archaic
  imperatives (переходіте, заходім); they stay in the plan on kaikki's say-so
  and contribute almost nothing.

## Reproduce

```bash
python3 scripts/ukrainian-frequency/count-homographs.py \
  --kaikki https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl \
  --corpus social=https://lang.org.ua/static/downloads/ubertext2.0/social/sentenced/ubertext.social.filter_rus_gcld+short.text_only.txt.bz2 \
  --corpus court=... --corpus fiction=... --corpus wikipedia=... --corpus news=... \
  --snapshot 2026-10-01
```

The kaikki pass, the lemmatizer answers and each subcorpus's counts are
cached under `build/stress-homographs/` (a cached corpus is reused only
while its form set still covers the plan), so a re-run after a change to the
plan streams only what the change needs. `npm run uk-freq:build-stress` then
rebuilds the release; `npm run uk-freq:check-stress` holds it.

## License

The counts are facts about UberText 2.0 (lang-uk, CC-BY 4.0); the readings and
forms are from en.wiktionary (CC-BY-SA 3.0). The lemmatizer answers come from
VESUM (dict_uk, CC BY-NC-SA), used only to strike forms: a struck form is an
absence in the plan, and nothing from that dictionary is redistributed. The
JSON ships inside the CC-BY-SA 4.0 stress release.
