# `uk-lexicon-dict_uk.txt.gz`

A build-time-only quality-assurance corpus for thread 05 (the vocabulary-size
self-test). Not part of the public open-data release; not imported by the
client page. `src/lib/ukrainian-frequency/vocab-test-release.mjs` loads and
decompresses it to reject any generated pseudoword that collides with a real
Ukrainian word outside the top-12000-lemma list itself (the 12000-lemma
collision check alone is not enough: a single-letter substitution on a common
short lemma has a real chance of landing on another real, if rarer, word).

333,097 unique lowercase Cyrillic headwords, extracted from the LibreOffice
Ukrainian hunspell dictionary (`uk_UA.dic`), which is itself built from the
`dict_uk` project (Andriy Rysin and contributors, brown-uk / dict_uk):

- Source: https://github.com/LibreOffice/dictionaries/blob/master/uk_UA/uk_UA.dic
- Upstream project: https://github.com/brown-uk/dict_uk
- License: MPL (Mozilla Public License) 1.1
- Fetched: 2026-07-14

Extraction: each `.dic` line's headword (the text before the first `/`
affix-flag separator) was kept if it matched Cyrillic letters, apostrophes, and
hyphens only, then lowercased and deduplicated. No affix expansion, no
inflection generation; this is stems and headwords only, used purely as a
larger negative-collision set, not redistributed as a standalone dictionary
product.
