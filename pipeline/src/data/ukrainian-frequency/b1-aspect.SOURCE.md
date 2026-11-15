# B1 extension, stage 3: the aspect relation table (sources)

Committed snapshots (the inputs the extractor consulted, sliced) and the
derived table. None of these is a source corpus.

- `b1-aspect.wiktionary.json`: for every verb the table can mention, its
  aspect (the canonical form's tag) and the aspect partners its Wiktionary
  headword lists, from the kaikki.org wiktextract dump of Ukrainian
  (CC-BY-SA 3.0). No conjugation tables, no glosses.
- `b1-aspect.ubertext-counts.json`: `[count, doc_count]` as a VERB lemma in
  UberText 2.0's lemma frequency dictionary (lang-uk, CC-BY 4.0) for every
  lemma looked up, keyed with the ASCII apostrophe (UberText writes U+2019;
  every key is normalized). Absent means looked up and not found. It also
  carries `lexicon`: the aspect the VESUM lexicon (via pymorphy3-dicts-uk)
  gives each lemma it knows as an infinitive, dictionary hits only. That map is
  VESUM-derived, regenerable with `--snapshot`, and not part of the public
  release.
- `b1-aspect.json` and `src/lib/ukrainian-frequency/b1-aspect.data.mjs`: the
  derived table and its browser tier; `public/downloads/ukrainian-frequency/b1-extension/`
  the public CSVs.

Levels and PULS aspect tags come from `puls-cefr.json` and `puls-cefr.raw.csv`
(by permission). The suppletive pairs are the hand-curated `SUPPLETIVE` list
in the extractor. The derussification flags on grid cells come from
`derussification.json` (thread 03).

Reproduce: `scripts/ukrainian-frequency/extract-b1-aspect.py --snapshot
--kaikki <verb jsonl> --freq <ubertext_freq.csv.xz>`; without `--snapshot`
the derived artifacts rebuild from the committed snapshots. CI re-derives the
aggregates from `b1-aspect.json` (`__tests__/b1-extension.test.js`).
