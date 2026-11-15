# dmklinger/ukrainian dictionary snapshot (thread 07 companion)

`dmk-dictionary.json` is a SNAPSHOT of the open Ukrainian-to-English
dictionary at https://github.com/dmklinger/ukrainian (Daniel Klinger, CC BY-SA 3.0),
restricted to the headwords that are lemmas of list v0.2.0. It is the data
behind the word lookup (`/research/ukrainian-frequency/lookup`,
`GET /api/uk/lookup/<word>`) and the third reading of the stress column.
Regenerate with `npm run uk-freq:fetch-dmk` (network).

## Provenance

| field | value |
|---|---|
| upstream file | `words.json` at https://raw.githubusercontent.com/dmklinger/ukrainian/master/words.json |
| fetched | 2026-10-03 |
| upstream SHA-256 | `6a0769103618fd1214a5527e6b1b34b06ec0818af630769a25302f781d537b17` |
| upstream entries | 30,111 |
| kept entries | 9,444 (headword is a list lemma, stress stripped, apostrophe folded) |
| list lemmas covered | 9,100 of 12,000 |

The upstream README states its sources: definitions scraped from the English
Wiktionary and from DBnary (which carries definitions for words Wiktionary has
no entry for yet), inflected forms filled from the ULIF national dictionary
(lcorp.ulif.org.ua) where a match was found. The headword carries the stress
mark the source gave it; an either-stress headword keeps both marks
(`та́ко́ж`), the Wiktionary notation the stress column splits into variants.

## What is kept per entry

`word` (the stressed headword, NFC), `pos` (the dictionary's own label:
noun, verb, adjective, adverb, particle, phrase, numeral, pronoun), `defs`
(the English definitions in the dictionary's order), `info` (gender and
animacy for nouns), `freq` (the dictionary's own frequency figure, kept for
reference, not this list's rank), `ranks` (the list ranks whose lemma this
headword spells; usually one, two where the list keeps a word under two tags).
The forms are dropped: thread 04 publishes the list's own paradigms. One
normalization is applied to the definitions: the em dash (U+2014), which the
upstream uses inside a few parentheticals, becomes a comma when spaced and a
hyphen when not, because nothing that leaves this site carries one. Everything
else is the upstream's text.

## License

The dictionary is CC BY-SA 3.0. Anything that re-publishes its definitions
(the lookup answers, this snapshot) carries that license and the attribution
above; the frequency list itself stays CC BY and is never merged with it.
