# genre-split.json : source and reproduction

## The question this exists to answer

Thread 02 measured that **229 word entries** of the A2 lexical minimum do not
rank in this site's top 12,000, and read that as the ceiling on frequency-first
learning. That reading carries an untested assumption. This site's list is built
on UberText 2.0's **combined** corpus, and the largest component of that corpus
by a wide margin is **news** (3.5 GB of about 5.1 GB). So "absent from the
frequency list" could mean either:

- **(a)** the vocabulary is genuinely rare in written Ukrainian, or
- **(b)** the vocabulary is ordinary, and journalism does not discuss forks,
  pumpkins or neckties.

Those imply opposite advice for anyone building a word list, and thread 02 could
not distinguish them. This thread measures which one it is.

## The answer

Two frequency lists, one from UberText's **fiction** subcorpus and one from its
**news** subcorpus, same size and same pipeline:

| | entries reached (of 936) | |
|---|---|---|
| News top-12,000 | 658 | 70.3% |
| Fiction top-12,000 | 648 | 69.2% |
| **Union of both** | **744** | **79.5%** |

The two genres reach **almost exactly the same amount** of the A2 minimum and
disagree sharply about **which** part: 562 entries are in both, 96 are news-only,
86 are fiction-only, 192 are in neither. Fiction recovers **30.9%** of what news
misses; news recovers **33.3%** of what fiction misses. The reciprocity is close
to symmetric, so neither genre is better.

The answer is therefore **(b)**, for a substantial share of the misses. Cooking
methods go from 14% coverage in news to 86% in fiction; family terms 57% to 100%;
body parts 75% to 100%. And the exclusive sets read exactly as the theory
predicts: news-only is `анкета`, `банкомат`, `безкоштовний`, `бланк`,
`Антарктида` (institutional, geographic, bureaucratic); fiction-only is `гарбуз`,
`закуска`, `краватка`, `веселка`, `змучений` (domestic, bodily, sensory).

The practical finding: **for a pedagogical vocabulary target, corpus diversity
buys what corpus size cannot.** A second genre of the same size adds 9.2 points
that more of the first genre would not have added.

## What makes the comparison fair

Every one of these had to hold, and each is a way the result could have been an
artifact instead of a finding:

1. **Same collection.** Both genres are UberText 2.0 subcorpora: same crawl, same
   cleaning, same Russian-language filtering. Using a separate fiction corpus
   (the Chtyvo library, say) would have confounded genre with collection and
   processing, and a difference could not have been attributed to genre.
2. **Same lemmatizer.** Both sides go through pymorphy3 in `genre-freq.py`.
3. **Same size.** Corpus size drives how deep a frequency list reaches, so both
   are capped to **85,552,190 tokens**.
4. **Same sampling shape.** Both are fractions of lines spread across the whole
   subcorpus (fiction 1/2, news 1/9 then capped), never a prefix. Reading a
   prefix would confound genre with position in the collection, and a fiction
   prefix can be one publisher or one era.

The result was checked at three sizes (171M unmatched, 107M matched, 85.5M
matched-and-spread). The per-theme deltas held in direction and rough magnitude
at all three.

## The red line

**These ranks are not comparable to this site's shipped frequency list.** That
list is lang-uk's own lemmatization of the combined corpus; this is our
pymorphy3 pass over two subcorpora. Mixing them would let a lemmatization
difference masquerade as a genre difference. Every published figure here is
fiction-versus-news with both sides measured by this pipeline. The shipped
`matched` flag is carried in the per-entry table for reference and is never used
in a headline figure; a test enforces that the two stay separate.

## Known limitation, stated rather than hidden

pymorphy3 mis-lemmatizes a few high-frequency Ukrainian pronouns (`його` to
`йога`, `мене` to `мен`; both appear in the fiction top-15). This affects
function words rather than the content vocabulary the comparison is about, and it
affects **both genres identically**, so it cannot generate a genre difference.

## Reproduce

```
# 1. fetch the two subcorpora (fiction 414 MB, news 3.5 GB; not vendored)
base=https://lang.org.ua/static/downloads/ubertext2.0
curl -o fiction.txt.bz2 "$base/fiction/cleansed/ubertext.fiction.filter_rus_gcld+short.text_only.txt.bz2"
curl "$base/news/cleansed/ubertext.news.filter_rus_gcld+short.text_only.txt.bz2" \
  | bunzip2 -c | awk 'NR%9==0' > news_sample.txt

# 2. one lemma frequency list per genre, size-matched and spread-sampled
python3 -m pip install pymorphy3 pymorphy3-dicts-uk
python3 scripts/ukrainian-frequency/genre-freq.py fiction.txt.bz2 freq_fiction.json 85552190 1/2
python3 scripts/ukrainian-frequency/genre-freq.py news_sample.txt  freq_news.json    85552190

# 3. the committed table, browser tier and public download
python3 scripts/ukrainian-frequency/build-genre-split.py freq_fiction.json freq_news.json
```

Step 3 refuses to run if the two genres differ in size by more than 0.1%, so the
central control cannot be lost by accident. The intermediate per-genre lists are
about 19 MB each and are not committed; `genre-split.json` is.

Deterministic; documented, not run in the build or in CI (same posture as the
other thread extractors).

## What is redistributed

Our own derived counts: per-entry fiction and news ranks, and the per-theme
aggregates. No corpus text is reproduced. The corpus is UberText 2.0 (lang-uk,
https://lang.org.ua/en/ubertext/); the entry list is the CC-BY-4.0 A2 lexical
minimum already credited in `borodin-a2.SOURCE.md`.
