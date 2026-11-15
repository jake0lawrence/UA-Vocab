# B1 extension, stage 3: the multiword table (sources)

A frequency list ranks lemmas, so a phrase is invisible to it. This table gives
every multiword expression its own ID, the validated level and rank of each
part, and its own count over a real corpus, which is the measurement the
UK-DiMLex attestation note said a unigram dictionary cannot make.

## The inventory (license-clean by construction)

- `uk-dimlex/UK_DiMLex.xml`: the lexicon of Ukrainian discourse connectives
  (Scheffler, Solopova, Zolotarenko, Razno, ICTERI 2021), MIT, committed
  verbatim for WO-4 and reused here. Entry IDs are kept as `sources[].id`, and
  where the entry's headword is a single word (`якщо`, `адже`, `щодо`, three
  more) the table's text is the canonical MULTIWORD orthography instead, with
  the headword recorded on the source row. Six entries differ this way.
- `borodin-a1.raw.json`, `borodin-a2.raw.json`: the two published Borodin
  lexical minimums (CC-BY-4.0), already committed for thread 02. Their
  registers are word lists that carry notation: a slash or comma for variants
  (`бізнесмен / бізнесменка`), a dash for an aspect pair (`брати - взяти`), an
  equals sign for a gloss (`бо = тому що`), parentheses for inflection hints
  (`ваш (ваша, ваше, ваші)`). `split_entry` splits on those and keeps only the
  segments that are still multiword, so `брати участь - взяти участь` yields two
  expressions and `в, у` yields none.

## Levels, ranks and parts

Levels come from the validated PULS join (CC-BY-NC-SA), ranks from thread 01's
top-12,000, and both are joined **per part**. A part is a word FORM, not a
lemma: `таким чином` is the instrumental of `такий` plus the instrumental of
`чин`, and joining the forms straight onto a lemma list finds neither. So each
part resolves in two recorded steps: the form itself when the list has it,
otherwise the lemmatizer's normal forms in order. `b1-multiword.part-lemmas.json`
is that map, written at snapshot time by pymorphy3 over the VESUM dictionary and
committed so the build, the tests and CI never need the analyzer. The dictionary
version is recorded rather than assumed to match the one the stage-3 usage
tables used; it does not (2.5.0 here, 2.4.1.1.1663094765 there).

`gatingLevel` is the highest validated level among the parts. It is a **floor**,
not a level for the expression: the profile levels words, not expressions.
`таким чином` reads C1 part by part, which is as wrong for the unit as A1 would
be, and the page says so where it shows the column.

## The corpus count

`b1-multiword.corpus-counts.json`: occurrences of every expression variant over
the same 400,000-line file prefix of UberText 2.0's Wikipedia subcorpus
(CC-BY-SA text) the stage-3 usage tables were cut from. It is **not** the same
subset: that parse kept only the 194,242 lines passing a clean-sentence filter
and counted 2,880,835 parsed tokens, and the filter drops exactly the short
lines connectives live on, so it is not applied here. This denominator
(4,694,436 word tokens) is larger and the two per-million rates are not
interchangeable. The snapshot carries the per-variant hits and the per-part
unigram hits, so the unit-against-its-rarest-part comparison re-derives.

Matching is a whole-token sequence match after folding case, stress,
apostrophes and the Latin `i` UK-DiMLex spells `і` with. A discontinuous
connective (`або...або`, `не лише...а й`) counts once per sentence line in
which both halves appear in order, while a contiguous one counts every
occurrence; the asymmetry is recorded in the snapshot's `matcher` field.

## PARSEME: read, never redistributed

The PARSEME 2.0 Ukrainian corpus (Kanishcheva, Shvedova, Sytar; annotated over
GRAC news text, <https://hdl.handle.net/11372/LRT-6123>) is **CC-BY-NC-SA 4.0**.
Its inventory is not ours to redistribute, in any release or the `ukvocab` package, so it is
used only as an independent validation of the inventory above, and in one
direction: the join reads, it never adds. No expression enters this table
because PARSEME has it, no PARSEME sentence is copied, and the per-expression
read is walled into `b1-multiword.parseme.json`, which the public downloads and
the package exclude (a fail-closed test asserts it). Only aggregate figures
reach the browser tier and the CSVs.

The release ships two sets of figures that disagree: the README counts 12,078
sentences / 198,555 tokens / 5,993 MWEs, `total-stats.md` counts 10,955 /
179,580 / 5,432. Reading the `.cupt` files reconciles with the README (the
21-token gap is the multiword token ranges and empty nodes the reader skips),
not with `total-stats.md`. Both are recorded and neither is repeated as fact.

## Reproduce

```bash
curl -sS --range 0-31000000 "https://lang.org.ua/static/downloads/ubertext2.0/wikipedia/sentenced/ubertext.wikipedia.filter_rus_gcld+short.text_only.txt.bz2" \
  | bzcat 2>/dev/null | head -n 400000 > /tmp/wiki-400k.txt
# PARSEME 2.0 UK.zip from https://hdl.handle.net/11372/LRT-6123 (CC-BY-NC-SA, do not vendor)
python3 -m pip install pymorphy3 pymorphy3-dicts-uk
npm run uk-freq:b1-multiword -- --snapshot --corpus /tmp/wiki-400k.txt --parseme-dir /tmp/parseme/UK
```

Without `--snapshot` every derived artifact rebuilds from the committed
snapshots, which is what CI does; `npm run uk-freq:check-b1-multiword` fails
when anything committed drifted from them.
