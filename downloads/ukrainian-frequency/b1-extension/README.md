# Ukrainian Frequency: the B1 extension (enrichment layer)

Five tables over the 1,604 lemmas the validated Ukrainian Vocabulary Profile
(PULS) labels B1 on the [Ukrainian Frequency](https://uavocab.org/research)
top-12,000 list. Every figure is a count over open data; nothing is generated.
Snapshot 2026-09-11. The corpus slice behind the usage tables (government,
collocations, examples) was cut when the validated B1 set held 1,585 lemmas;
the 20 lemmas the 2026-09-13 join fix added (validated B1 words the two tag
conventions had kept apart, such as військовий, вчений, слід) have no usage
rows until the corpus is re-parsed, and are counted as absent, not zero.

## The aspect relation table

`aspect-relations.csv`: one row per (B1 verb, related verb). Columns
`b1_verb,b1_rank,b1_aspect,related,kind,related_aspect,related_level,related_validated,related_rank,ubertext_count,attested,split_level`.

- `kind` is `partner` (a Wiktionary-listed aspect partner, or one of the
  hand-curated suppletive pairs such as брати / взяти) or `prefixed` (a
  corpus-attested prefix + lemma derivative of an imperfective B1 verb, where
  the meaning-shifting perfectives live).
- Each related verb keeps its own PULS level (`related_level`), so a
  `split_level` row is a B1 verb whose partner the profile places elsewhere.
  `related_validated` says whether that level is the validated join onto this
  list (`yes`) or a PULS entry off the list (`no`).
- `attested` means at least 100 occurrences in UberText 2.0 as a VERB lemma
  (and, for prefixed rows, known to the VESUM lexicon as that infinitive).

`motion-grid.csv`: the prefix x root grid over the eight core motion pairs,
sixteen canonical prefixes (allomorphs folded: від/віді, з/зі/с, об/обі,
над/наді, під/піді, роз/розі, в/у). A row per generated cell; the attested
forms of a cell each get a row with their count, rank and level. Empty cells
carry no form.

## The multiword table

A frequency list ranks lemmas, so a phrase is invisible to it: "тому що" is
counted as one very common conjunction plus one very common pronoun, and
nowhere as the connective it is. These two files give every multiword
expression its own ID.

`multiword.csv`: one row per expression. Columns
`id,expression,kind,words,variants,discontinuous,sources,cats,senses,minimum_levels,gating_level,all_parts_on_list,all_parts_leveled,max_part_rank,occurrences,per_million,rarest_part_occurrences`.

- `kind` is `connective` (a discourse connective from UK-DiMLex, MIT) or
  `phrase` (a multiword entry of the Borodin A1 or A2 lexical minimum,
  CC-BY-4.0). `sources` names every register the expression is in.
- `gating_level` is the highest validated level among the expression's PARTS.
  It is a floor, not a level for the expression: the profile levels words, not
  expressions. "таким чином" is a frozen instrumental of a C1 noun and so reads
  C1 part by part, which is as wrong for the unit as A1 would be.
- `occurrences` counts the expression (every orthographic variant together)
  over 4,694,436 word tokens of UberText 2.0's Wikipedia subcorpus. That is the
  same file prefix the usage tables above were cut from but not the same subset:
  they applied a clean-sentence filter that drops the short lines connectives
  live on, so the two per-million rates are not interchangeable.
  `rarest_part_occurrences` is the rarest part's count over the same slice,
  which is what makes "the parts are common, the unit is not" a number.
- `discontinuous` marks a correlative pair written with an ellipsis
  ("або...або", "не лише...а й"). Those count once per sentence line in which
  both halves appear in order; a contiguous expression counts every occurrence.

`multiword-parts.csv`: one row per part. Columns
`expression_id,expression,position,word,lemma,resolved_via,rank,level`. A part
is a word form, not a lemma, so `resolved_via` says how it reached the list:
`form` (the list has the form itself), `lemma` (via the lemmatizer's normal
form, recorded in `lemma`), or `unresolved` (the lemma is genuinely not in the
top-12,000, which is most of the everyday A1 and A2 vocabulary a news corpus
has little use for).

A part is matched by spelling, not by part of speech, so `rank` is the
spelling's most frequent reading on the list and `level` the easiest level the
profile gives any reading of it. The two can come from different readings: що
in тому що carries rank 8 (the conjunction, validated A2) and level A1 (the
pronoun at rank 39). `gating_level` is built from these part levels, so it is a
floor on the easiest reading, not a claim about the sense the expression uses.

The PARSEME 2.0 Ukrainian corpus was read as an independent check on this
inventory and is NOT part of it or of these files: that corpus is CC-BY-NC-SA,
and its inventory is not ours to redistribute. The check ran in one
direction only, so no expression is here because PARSEME has it. The aggregate
is on the page.

## The usage layer

`government.csv`: verb + preposition + case with the share of that verb's
nominal dependents, aggregated over 2,880,835 parsed tokens of UberText 2.0's
Wikipedia subcorpus (spaCy uk_core_news_sm 3.8.0). `shown` marks the patterns
above the display threshold (10 percent and 3 observations); every counted
pattern is in the file. Phonological variants of one preposition (в/у, з/із/зі)
are merged before counting.

`collocations.csv`: dependency-linked lemma pairs ranked by logDice
(14 + log2(2 f_xy / (f_x + f_y))), the strongest eight per B1 lemma, at least
three co-occurrences. `relation` is the UD dependency label; `side` says
whether the B1 lemma is the head or the child.

`examples.csv`: up to two attested sentences per B1 lemma, verbatim from the
Wikipedia subcorpus up to whitespace and dash normalization (em dashes become a
spaced hyphen). Every sentence passed the russianism gate (LanguageTool's
Ukrainian replacement tables, run on every token; a hit drops the sentence).

## License and attribution

Counts and derived statistics: CC-BY-SA 4.0. Levels: Ukrainian Vocabulary
Profile (PULS), Synchak, O., Starko, V., Burak, M., Svystun, M., https://puls.peremova.org/,
redistributed with the authors' permission, CC BY-NC-SA 4.0 at their decision
(2026-09-24), attribution required; the tables that carry a level column
(aspect-relations, motion-grid, multiword, multiword-parts) are therefore
CC-BY-NC-SA-4.0 as a whole, and government, collocations and examples are not.
Cite the profile as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026. Aspect
partners: Wiktionary via kaikki.org, CC-BY-SA 3.0. Corpus counts: UberText 2.0
(lang-uk), CC-BY 4.0. Example sentences: Ukrainian Wikipedia text via UberText
2.0, CC-BY-SA. Aspect tags and the lexicon check: VESUM via pymorphy3
(pymorphy3-dicts-uk); no VESUM data is bundled here.

## Where it fits

Every table here starts from the lemmas labeled B1 in
`../validated-cefr/lemmas.csv`. Join to `../v0.1.0/lemmas.csv` on a table's
rank column where it has one (`b1_rank` and `related_rank` in the aspect
table, `rank` elsewhere; the collocations table is keyed by lemma). The parts
table joins by spelling (above), so use its `rank` for a per-reading level.

The multiword entries of the two lexical minimums are the `phrase` rows of
`multiword.csv`; the entries themselves are in `../borodin-a1/` and
`../borodin-a2/`. The aspect, government and collocation tables also ship in
the `ukvocab` Python package, and the folder is a Zenodo deposit.
