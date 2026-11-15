# Ukrainian Frequency: the B1 enrichment tables (datasheet)

Seven tables over the lemmas the validated Ukrainian Vocabulary Profile (PULS) labels B1 on the Ukrainian Frequency top-12,000 list: each B1 verb related to its aspect partner and its corpus-attested prefixed derivatives (every related verb keeping its own PULS level, so split-level pairs are visible), the motion-verb prefix grid, verb-plus-preposition-plus-case government counts, logDice collocations, two attested example sentences per lemma, and the multiword table a lemma list cannot hold, all counted over open data. Snapshot 2026-09-11, aspect table rebuilt 2026-09-13, multiword table added 2026-09-17. CC-BY-SA 4.0.

## What it is

- `aspect-relations.csv`: one row per (B1 verb, related verb); columns `b1_verb, b1_rank, b1_aspect, related, kind, related_aspect, related_level, related_validated, related_rank, ubertext_count, attested, split_level`. 442 B1 verbs, 378 paired, 591 prefixed derivatives, 102 split-level pairs.
- `motion-grid.csv`: the prefix by root grid over the eight core motion pairs, sixteen canonical prefixes, 211 of 256 cells attested.
- `government.csv`: verb + preposition + case with the share of the verb's nominal dependents, 365 verbs.
- `collocations.csv`: dependency-linked lemma pairs ranked by logDice, the strongest eight per lemma, at least three co-occurrences, 1,087 lemmas.
- `examples.csv`: up to two attested sentences per lemma, 1,497 lemmas, every sentence through a fail-closed russianism gate.
- `multiword.csv`: one row per multiword expression; columns `id, expression, kind, words, variants, discontinuous, sources, cats, senses, minimum_levels, gating_level, all_parts_on_list, all_parts_leveled, max_part_rank, occurrences, per_million, rarest_part_occurrences`. 142 expressions: 63 discourse connectives from UK-DiMLex (MIT) and 79 multiword entries of the two published Borodin lexical minimums (CC BY 4.0). `gating_level` is the highest validated level among the expression's PARTS and is a floor, not a level for the expression, because the profile levels words and not expressions.
- `multiword-parts.csv`: one row per part; columns `expression_id, expression, position, word, lemma, resolved_via, rank, level`. 307 parts, `resolved_via` recording whether the part joined the list as its own form (235), through the lemmatizer's normal form (48), or not at all (24).
- `README.md`: the site's column documentation. `DATASHEET.md` (this file) and `manifest.json` with SHA-256 per file.

## How it was built

Aspect: `extract-b1-aspect.py` over the Wiktionary Ukrainian entries (kaikki.org) for headword-listed aspect partners, a hand-curated suppletive table, and prefix-plus-lemma candidates attested in UberText 2.0 (at least 100 occurrences as a VERB lemma, known to the lexicon as that infinitive). Usage: `parse-b1-corpus.py` parses a 2,880,835-token prefix of the UberText 2.0 Wikipedia subcorpus with spaCy uk_core_news_sm 3.8.0; `extract-b1-usage.py` counts government (phonological variants of one preposition merged), collocations (logDice = 14 + log2(2 f_xy / (f_x + f_y))), and examples, with LanguageTool's Ukrainian replacement tables run on every token as the russianism gate (a hit drops the sentence). A 60-verb maintainer-written reference check on the parser is published beside the counts (59 of 60 top patterns agree) and is labeled as not an annotator.

Multiword: `extract-b1-multiword.py` reads the committed UK-DiMLex XML and the two committed Borodin raw snapshots, splits the registers' notation for variants, aspect pairs, glosses and inflection hints off the entries and keeps only the segments that are still multiword, resolves every part against the list (its own form first, then pymorphy3's normal forms from a committed map) and counts each expression as a whole-token sequence over 4,694,436 word tokens of the same UberText Wikipedia file prefix. That is a larger slice than the usage tables above, which applied a clean-sentence filter that drops the short lines connectives live on, so the two per-million rates are not interchangeable.

## What it excludes

- Any VESUM data. Aspect tags, the lexicon check and the multiword part lemmas use VESUM through pymorphy3 at build time; nothing from it is bundled.
- Anything derived per expression from the PARSEME 2.0 Ukrainian corpus. That corpus (Kanishcheva, Shvedova, Sytar, <https://hdl.handle.net/11372/LRT-6123>) is CC-BY-NC-SA 4.0 and its inventory is not ours to redistribute, so nothing from it enters this bundle. It was read as an independent check on the multiword inventory, in one direction only (no expression is in the table because PARSEME has it; 35 of the 142 are attested there), it is not vendored anywhere in the repository, and the per-expression read stays in a snapshot the release excludes behind a fail-closed test. Only the aggregate is published, on the page.
- Corpus text beyond the example sentences, which are verbatim Wikipedia sentences under CC-BY-SA.
- Levels for the prefixed derivatives the profile does not cover (`related_level` is blank, not guessed).

## Known defects

- The corpus slice was cut when the validated B1 set held 1,585 lemmas. The 2026-09-13 join fix added 20 B1 lemmas (validated B1 words the two tag conventions had kept apart, such as військовий, вчений, слід); they have no government, collocation or example rows until the corpus is re-parsed, and are counted as absent, not zero.
- One parsed Wikipedia prefix, not the whole corpus: counts are stable for frequent verbs and thin for rare ones; `government.csv` marks 29 verbs with no dependents observed.
- The parser is a small spaCy model; the reference check measures it on 60 verbs, not on the whole table.
- 15 verbs where PULS and Wiktionary disagree on aspect are kept with both opinions rather than resolved.

## Intended uses

B1 course and exercise writing (aspect pairs with their levels, government patterns with shares, collocations); a candidate list for the PULS authors' own review of aspect counterparts; corrections upstream to Wiktionary and VESUM (the disagreement rows are the worklist).

## Unintended uses

Treating a count over one Wikipedia prefix as a norm of the language; treating an unattested cell of the motion grid as a non-word; treating the example sentences as pedagogically graded (they are attested, not simplified).

## Attribution

- Levels: Ukrainian Vocabulary Profile (PULS), Synchak, O., Starko, V., Burak, M., Svystun, M., https://puls.peremova.org/, redistributed with the authors' permission, CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24; snapshot 2026-07-23). Cite as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.
- Aspect partners: Wiktionary via kaikki.org (wiktextract), CC-BY-SA 3.0. https://kaikki.org/dictionary/Ukrainian/
- Corpus counts and example sentences: UberText 2.0, Wikipedia subcorpus (lang-uk; Chaplynskyi 2023), CC-BY 4.0 for the counts, CC-BY-SA for the Wikipedia text. https://lang.org.ua/en/ubertext/
- Russianism gate: LanguageTool Ukrainian replacement tables (LGPL), used at build time only.
- Aspect tags and lexicon check at build time: VESUM via pymorphy3 (pymorphy3-dicts-uk); no VESUM data bundled.

## Cite this deposit

Lawrence, J. (2026). Ukrainian Frequency: the B1 enrichment tables (aspect relations, case government, collocations, examples). Zenodo. Concept DOI: see the deposit record. Live page: https://uavocab.org/research#b1

## Maintenance

The aspect table follows the overlay; the usage tables follow the corpus parse, which is re-run when the B1 set changes materially. Each rebuild is a new version under the same concept DOI.
