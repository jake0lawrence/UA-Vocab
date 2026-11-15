#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 3: the CORPUS PARSE (one-time,
# reproducible, NOT run in the build or CI).
#
# Streams a prefix of UberText 2.0's Wikipedia subcorpus (CC-BY-SA text, the
# license-compatible subcorpus the plan names for attested examples), parses it
# with spaCy's uk_core_news_sm (UD-trained: pymorphy3 lemmas, dependency
# labels, morphological Case), and writes COUNTS ONLY plus attested example
# sentences for the B1 lemma set. No other text leaves this script.
#
# What it aggregates:
#   gov       (verb lemma, preposition, Case, dep) -> n   : case government
#   pairs     (dep, head lemma, head POS, child lemma, child POS) -> n : the
#             dependency-linked pairs logDice is computed over
#   uni       (lemma, POS) -> n : the unigram frequencies logDice needs
#   examples  B1 lemma -> up to 4 attested sentences (6 to 24 tokens, no PROPN)
#   stats     tokens, content tokens, and how many content tokens land on a
#             thread-01 lemma string (the lemmatizer reconciliation rate: the
#             parser's pymorphy3 lemmas against lang-uk's, reported, never
#             merged into the ranks)
#
# Reproduce (about 12 minutes on one CPU for 400k source lines):
#   python3 -m pip install spacy \
#     https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl
#   curl -sS "https://lang.org.ua/static/downloads/ubertext2.0/wikipedia/sentenced/ubertext.wikipedia.filter_rus_gcld+short.text_only.txt.bz2" \
#     | bzcat | head -n 400000 > /tmp/wiki-prefix.txt
#   python3 scripts/ukrainian-frequency/parse-b1-corpus.py /tmp/wiki-prefix.txt /tmp/parsed-wiki.json
#   python3 scripts/ukrainian-frequency/extract-b1-usage.py --snapshot --parsed /tmp/parsed-wiki.json
#
# House rule: no em-dashes.
# ---------------------------------------------------------------------------
import sys, json, re, time, collections
import spacy
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
seed = json.load(open(f"{ROOT}/src/data/ukrainian-frequency/ubertext-lemmas-top12k.json", encoding="utf-8"))
puls = json.load(open(f"{ROOT}/src/data/ukrainian-frequency/puls-cefr.json", encoding="utf-8"))
# The list writes the apostrophe as U+2019; Wikipedia text mixes U+2019, U+02BC
# and U+0027, and spaCy's lemma keeps whichever the token had. Fold to the
# list's form so an apostrophe lemma joins whatever the source typed.
def fold(s):
    return s.replace("\u0027", "\u2019").replace("\u02bc", "\u2019")


LIST = {(fold(r["lemma"].lower()), r["pos"]) for r in seed["rows"]}
LIST_LEMMAS = {fold(r["lemma"].lower()) for r in seed["rows"]}
B1 = {(fold(r["lemma"].lower()), r["pos"]) for r in puls["rows"] if r["level"] == "B1"}
B1_LEMMAS = {l for l, p in B1}
CONTENT = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
MAX_EX = 4

nlp = spacy.load("uk_core_news_sm", disable=["ner"])
gov = collections.Counter()      # (verb, prep, case) -> n
verb_tot = collections.Counter() # verb -> n of oblique/object dependents counted
pairs = collections.Counter()    # (rel, head_lemma, head_pos, child_lemma, child_pos) -> n
uni = collections.Counter()      # (lemma, pos) -> n
examples = collections.defaultdict(list)
stats = collections.Counter()
t0 = time.time()

def texts():
    for line in open(sys.argv[1], encoding="utf-8"):
        s = line.strip()
        if len(s) < 30 or len(s) > 400 or s.count(" ") < 5:
            continue
        if re.search(r"[A-Za-z]{4,}|\d{4}|[|{}\[\]=]", s):  # skip lines heavy with latin/markup
            continue
        yield s

for doc in nlp.pipe(texts(), batch_size=64):
    stats["sentences"] += 1
    toks = [t for t in doc if not t.is_punct and not t.is_space]
    stats["tokens"] += len(toks)
    seen_b1 = set()
    for t in toks:
        lem = t.lemma_.lower().replace("́", "").replace("\u0027", "\u2019").replace("\u02bc", "\u2019")
        key = (lem, t.pos_)
        uni[key] += 1
        if t.pos_ in CONTENT:
            stats["content"] += 1
            if lem in LIST_LEMMAS: stats["content_on_list"] += 1
            if key in LIST: stats["content_on_list_pos"] += 1
        if key in B1: seen_b1.add(lem)
        # dependency pairs (content words only, excluding PROPN on either side)
        h = t.head
        if t.dep_ in ("obl", "obj", "iobj", "nmod", "amod", "advmod", "nsubj", "acl", "advcl", "conj") and h is not t:
            hl = h.lemma_.lower().replace("́", "").replace("\u0027", "\u2019").replace("\u02bc", "\u2019")
            if t.pos_ in ("NOUN", "VERB", "ADJ", "ADV") and h.pos_ in ("NOUN", "VERB", "ADJ", "ADV"):
                pairs[(t.dep_, hl, h.pos_, lem, t.pos_)] += 1
        # government: verb + (prep) + case of a nominal dependent
        if h.pos_ == "VERB" and t.pos_ in ("NOUN", "PROPN", "PRON") and t.dep_ in ("obl", "obj", "iobj"):
            case = t.morph.get("Case")
            case = case[0] if case else "?"
            prep = ""
            for c in t.children:
                if c.dep_ == "case" and c.pos_ == "ADP":
                    prep = c.lemma_.lower(); break
            hl = h.lemma_.lower().replace("́", "").replace("\u0027", "\u2019").replace("\u02bc", "\u2019")
            gov[(hl, prep, case, t.dep_)] += 1
            verb_tot[hl] += 1
    for lem in seen_b1:
        if len(examples[lem]) < MAX_EX and 6 <= len(toks) <= 24 and not any(t.pos_ == "PROPN" for t in toks):
            examples[lem].append(doc.text)
    if stats["sentences"] % 20000 == 0:
        print(stats["sentences"], stats["tokens"], round(time.time() - t0), "s", file=sys.stderr, flush=True)

out = {
  "stats": dict(stats), "seconds": round(time.time() - t0),
  "gov": [[k[0], k[1], k[2], k[3], n] for k, n in gov.items() if n >= 2],
  "verbTot": dict(verb_tot),
  "pairs": [[k[0], k[1], k[2], k[3], k[4], n] for k, n in pairs.items() if n >= 3],
  "uni": [[k[0], k[1], n] for k, n in uni.items() if n >= 3],
  "examples": examples,
}
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print("done", dict(stats), round(time.time() - t0), "s")
