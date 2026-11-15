# B1 extension, stage 3: government, collocations, examples (sources)

- `b1-usage.snapshot.json`: the parse output of
  `scripts/ukrainian-frequency/parse-b1-corpus.py` sliced down to the B1 set.
  The corpus is a 400,000-line prefix of UberText 2.0's Wikipedia subcorpus
  (lang-uk; Wikipedia text, CC-BY-SA), parsed with spaCy `uk_core_news_sm`
  3.8.0 (UD Ukrainian-IU conventions; pymorphy3 lemmas). It carries counts
  only, plus up to two attested example sentences per B1 lemma, verbatim with
  whitespace normalized. It also carries the lemmatizer convention check
  (pymorphy3's normal form of each PULS B1 headword against the headword) and
  the russianism gate's report.
- `b1-usage.json` and `src/lib/ukrainian-frequency/b1-usage.data.mjs`: the
  derived tables and browser tier (the derived JSON does not repeat the
  example sentences; they live in the snapshot and the public CSV).

The russianism gate reads LanguageTool's Ukrainian replacement tables
(`replace.txt`, `replace_soft.txt`; LGPL-2.1, not vendored, read at snapshot
time from the LanguageTool repository) and the VESUM lexicon via pymorphy3.
The reference check's textbook government list is the maintainer-written
`REFERENCE` in the extractor, not an independent annotator.

The parser's lemmas are used only to aggregate; the join keys are the PULS
headwords. The convention check and the content-token-on-list rate are
reported in the snapshot and on the page, never merged into thread 01's
ranks.

**The nlp_uk re-lemmatization is done, and it is why these tables were not
rebuilt** (`b1-usage.relemmatize.json`, `relemmatize-b1-corpus.py`,
2026-09-17). The pinned step assumed that re-running the parse layer through
nlp_uk / TagText, the toolchain PULS itself used, would tighten the joins.
Measured over this same slice, sentence by sentence through the VESUM
pipeline in `services/lemmatizer`, it does not: the two conventions agree on
92.6 percent of the 2,880,835 tokens, and content words land on thread 01's
list at 73.0 percent under pymorphy3 against 72.6 under nlp_uk (72.0 against
70.6 when the part of speech has to match too). The measurement reproduced
this snapshot's own published rates exactly, 73.0 and 72.0, before comparing
anything, so the pipeline is the one these tables were built with.

The gap is a convention rather than an error on either side: nlp_uk treats a
substantivized adjective as its own headword, so російською reads російська
where this list has російський, and a sentence-initial capital often reads as
a proper noun. Both readings are defensible and neither is the one the ranks
carry. Agreement is lowest on the closed classes, where the two tag
conventions differ most: pronouns 64.2 percent over 42,688 tokens, then
determiners 81.0 and proper nouns 84.7 (`lowestAgreement` derives this from
the table with a 1,000-token floor rather than asserting it).

The gap itself is 9,019 content tokens and it closes exactly: 38,454 move off
the list and 29,435 move on, counted over the content tokens the rate is
measured on. `disagreementClasses` is a different population, every part of
speech and disagreeing tokens only, so its counters are not these; the
artifact says so and `check_gap_accounting` refuses to write a file whose
parts do not sum.

Reproduce: see the header of `parse-b1-corpus.py`; then
`extract-b1-usage.py --snapshot --parsed <parsed.json> --lt-dir <dir with the
LanguageTool tables>`. Without `--snapshot` the derived artifacts rebuild from
the committed snapshot. CI re-derives shares, logDice and the gate's totals
(`__tests__/b1-extension.test.js`).
