#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 3: the MULTIWORD TABLE.
#
# Connectors and idioms cannot live in a lemma list. A frequency list ranks
# lemmas, so a phrase is invisible to it: "тому що" is counted as one very
# common conjunction plus one very common pronoun, and a learner who "knows"
# both has never met the connective. This table gives every multiword
# expression its own ID, its own corpus count, and the levels of its parts,
# so the gap between knowing the words and knowing the phrase is measurable
# rather than assumed.
#
# THE INVENTORY IS LICENSE-CLEAN BY CONSTRUCTION. Two sources, both usable in
# an open release:
#   - UK-DiMLex (Scheffler, Solopova, Zolotarenko, Razno; MIT), the lexicon of
#     Ukrainian discourse connectives, committed verbatim under
#     src/data/ukrainian-frequency/uk-dimlex/. Its entry IDs are kept.
#   - The Borodin A1 and A2 lexical minimums (CC-BY-4.0), already committed as
#     raw snapshots for thread 02. Their multiword entries are extracted here;
#     the notation the books use for variants, aspect pairs and inflection
#     hints is parsed off rather than counted as a phrase (see split_entry).
#
# Levels and ranks come from the validated PULS join (CC-BY-NC-SA) and thread
# 01's top-12,000, per PART. A unit level is NOT invented: gatingLevel is the
# highest validated level among the parts, which is a floor on the unit and is
# labeled as one.
#
# Counts come from the same corpus slice the stage-3 usage tables used (a
# 400,000-line prefix of UberText 2.0's Wikipedia subcorpus, CC-BY-SA), so a
# phrase count and a government count are comparable. This is the measurement
# the UK-DiMLex note said was missing: a unigram dictionary attests words, not
# phrases.
#
# PARSEME IS READ BUT NEVER REDISTRIBUTED. The PARSEME 2.0 Ukrainian corpus
# (Kanishcheva, Shvedova, Sytar) is CC-BY-NC-SA 4.0 and its inventory is not
# ours to redistribute, in any release or in the ukvocab package. It is used as an INDEPENDENT
# VALIDATION of the inventory above and in one direction only: the join reads,
# it never adds. No expression enters this table because PARSEME has it, no
# PARSEME sentence is copied, and the per-expression read is walled into
# b1-multiword.parseme.json, which the release and the package exclude. Only
# aggregate figures reach the browser tier and the public CSV.
#
# Three modes:
#   --snapshot   counts phrases over the corpus prefix (--corpus) and, when
#                given --parseme-dir, records the PARSEME validation read.
#                Writes the committed snapshots, then builds.
#   (default)    rebuilds every derived artifact from the committed snapshots,
#                so CI re-derives the table with no corpus and no download.
#   --check      rebuilds into memory and fails if anything committed differs.
#
# Reproduce the snapshot:
#   curl -sS --range 0-31000000 "https://lang.org.ua/static/downloads/ubertext2.0/wikipedia/sentenced/ubertext.wikipedia.filter_rus_gcld+short.text_only.txt.bz2" \
#     | bzcat 2>/dev/null | head -n 400000 > /tmp/wiki-400k.txt
#   # PARSEME 2.0 UK.zip from https://hdl.handle.net/11372/LRT-6123 (CC-BY-NC-SA, do not vendor)
#   python3 scripts/ukrainian-frequency/extract-b1-multiword.py --snapshot \
#     --corpus /tmp/wiki-400k.txt --parseme-dir /tmp/parseme/UK
#
# House rule: no em-dashes in anything this writes.
# ---------------------------------------------------------------------------

import argparse
import collections
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
LIB = os.path.join(ROOT, "src", "lib", "ukrainian-frequency")
DL = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "b1-extension")

SNAPSHOT_DATE = "2026-09-17"
CORPUS_SOURCE = "UberText 2.0, Wikipedia subcorpus (lang-uk), the same 400000-line file prefix the stage-3 usage tables were cut from, every line counted"
CORPUS_URL = "https://lang.org.ua/en/ubertext/"
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_IDX = {l: i + 1 for i, l in enumerate(LEVELS)}
SAMPLE = 12
APOS = "’"
ELLIPSIS = "..."

# UK-DiMLex spells the Cyrillic conjunction "i" with a Latin i in several
# entries; thread 02's attestation snapshot records the same fold.
LATIN_FOLD = {"i": "і", "I": "І"}


def strip_stress(s):
    """Borodin's books mark stress with a combining acute; the list does not."""
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", s) if c != "́"))


def fold(s):
    """One spelling per string: the list's apostrophe, Cyrillic i, no stress."""
    s = strip_stress(s)
    s = s.replace("'", APOS).replace("ʼ", APOS).replace("ʹ", APOS)
    for a, b in LATIN_FOLD.items():
        s = s.replace(a, b)
    return s


TOKEN_RE = re.compile(r"[Ѐ-ӿ" + APOS + r"\-]+")


def tokens(s):
    """Word tokens of Ukrainian text, normalized to the list's spelling."""
    return TOKEN_RE.findall(fold(s).lower())


# ---------------------------------------------------------------------------
# The inventory
# ---------------------------------------------------------------------------

# Borodin's registers are word lists, but several entries carry notation: a
# slash or comma for variants (бізнесмен / бізнесменка), a dash for an aspect
# pair (брати - взяти), an equals sign for a gloss (бо = тому що), parentheses
# for inflection hints (ваш (ваша, ваше, ваші)). Splitting on those and then
# keeping only the segments that are still multiword is what separates a real
# expression (брати участь - взяти участь is two of them) from notation.
# The dash separators are written as escapes (re reads them, so no literal
# en, em or minus dash glyph sits in this file).
SEPARATORS = re.compile(r"[/;,=]|\s[\u2013\u2014\u2212-]\s")
PARENS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
WORD_ONLY = re.compile(r"^[Ѐ-ӿ" + APOS + r"\-]+$")


def split_entry(raw):
    """The multiword expressions a raw minimum entry actually contains."""
    text = PARENS.sub(" ", fold(raw))
    out = []
    for seg in SEPARATORS.split(text):
        words = [w for w in seg.split() if w]
        if len(words) < 2:
            continue                      # a single word is thread 01's business
        if not all(WORD_ONLY.match(w) for w in words):
            continue                      # a stray marker (*, digits, Latin)
        out.append(" ".join(words))
    return out


def read_dimlex():
    """Connectives with their orthographic variants, categories and senses."""
    path = os.path.join(DATA, "uk-dimlex", "UK_DiMLex.xml")
    root = ET.parse(path).getroot()
    entries, quirks = [], {"orthTypeWhitespace": 0, "latinIFolded": []}
    for e in root.findall("entry"):
        eid, word = e.get("id"), e.get("word")
        variants = []
        for o in e.findall("./orths/orth"):
            otype = (o.get("type") or "").strip()
            if otype != (o.get("type") or ""):
                quirks["orthTypeWhitespace"] += 1
            for p in o.findall("part"):
                text = (p.text or "").strip()
                if not text:
                    continue
                folded = fold(text)
                if folded != strip_stress(text):
                    quirks["latinIFolded"].append({"id": eid, "from": text, "to": folded})
                variants.append({
                    "text": folded,
                    "canonical": o.get("canonical") == "1",
                    "discontinuous": otype == "discont" or ELLIPSIS in folded,
                })
        cats = sorted({c.text for c in e.findall("./syn/cat") if c.text})
        senses = sorted({s.get("sense") for s in e.findall("./syn/sem/pdtb3_relation") if s.get("sense")})
        english = (e.findtext("english_equivalent") or "").strip()
        entries.append({"id": eid, "word": fold(word), "variants": variants,
                        "cats": cats, "senses": senses, "english": english})
    quirks["latinIFolded"].sort(key=lambda x: (x["id"], x["from"]))
    return entries, quirks


def read_minimum(name, level):
    """The multiword entries of one Borodin register."""
    d = json.load(open(os.path.join(DATA, name), encoding="utf-8"))
    found = []
    for raw in d["entries"]:
        for text in split_entry(raw):
            found.append({"text": text, "raw": raw, "level": level})
    return found, {"entries": d["entryCount"], "license": d["license"], "source": d["source"]}


def build_inventory():
    """Every expression, with its own ID, deduplicated across the sources."""
    dimlex, quirks = read_dimlex()
    a1, a1_meta = read_minimum("borodin-a1.raw.json", "A1")
    a2, a2_meta = read_minimum("borodin-a2.raw.json", "A2")

    by_text = {}

    def slot(text, kind):
        key = text.lower()
        if key not in by_text:
            by_text[key] = {"text": text, "kind": kind, "sources": [], "variants": [],
                            "cats": [], "senses": [], "english": "", "minimumLevels": []}
        return by_text[key]

    for e in dimlex:
        multi = [v for v in e["variants"] if len(v["text"].replace(ELLIPSIS, " ").split()) > 1]
        if not multi:
            continue                      # a one-word connective belongs to thread 01
        # The expression IS a multiword form, so the table's text is the
        # canonical MULTIWORD orthography, not the entry headword: UK-DiMLex
        # heads "якщо...то" and "адже ж" on their one-word spelling, and taking
        # the headword would put a single word in a multiword table.
        canon = next((v["text"] for v in multi if v["canonical"]), multi[0]["text"])
        x = slot(canon, "connective")
        x["sources"].append({"source": "uk-dimlex", "id": e["id"], "headword": e["word"]})
        x["cats"] = sorted(set(x["cats"]) | set(e["cats"]))
        x["senses"] = sorted(set(x["senses"]) | set(e["senses"]))
        x["english"] = x["english"] or e["english"]
        seen = {v["text"] for v in x["variants"]}
        for v in multi:
            if v["text"] not in seen:
                x["variants"].append({"text": v["text"], "discontinuous": v["discontinuous"]})
                seen.add(v["text"])

    for rows, src in ((a1, "borodin-a1"), (a2, "borodin-a2")):
        for r in rows:
            x = slot(r["text"], "phrase")
            x["sources"].append({"source": src, "id": r["raw"]})
            x["minimumLevels"].append(r["level"])
            if not any(v["text"] == r["text"] for v in x["variants"]):
                x["variants"].append({"text": r["text"], "discontinuous": False})

    expressions = []
    for i, key in enumerate(sorted(by_text), start=1):
        x = by_text[key]
        x["id"] = f"mw{i:04d}"
        x["minimumLevels"] = sorted(set(x["minimumLevels"]), key=lambda l: LEVEL_IDX[l])
        # A connective that a learner register also lists is both; the kind
        # records where the expression is defined, the sources say who has it.
        x["inMinimum"] = bool(x["minimumLevels"])
        expressions.append(x)
    meta = {"dimlex": {"entries": len(dimlex), "quirks": quirks},
            "borodinA1": a1_meta, "borodinA2": a2_meta}
    return expressions, meta


# ---------------------------------------------------------------------------
# Levels and ranks, per part
# ---------------------------------------------------------------------------

def load_parts_context():
    seed = json.load(open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    puls = json.load(open(os.path.join(DATA, "puls-cefr.json"), encoding="utf-8"))
    rank, level = {}, {}
    # the seed rows are ordered by rank and carry no rank field; the index is it
    for i, r in enumerate(seed["rows"], start=1):
        lem = fold(r["lemma"]).lower()
        rk = r.get("rank", i)
        if lem not in rank or rk < rank[lem]:
            rank[lem] = rk
    for r in puls["rows"]:
        lem = fold(r["lemma"]).lower()
        lv = r["level"]
        if lem not in level or LEVEL_IDX[lv] < LEVEL_IDX[level[lem]]:
            level[lem] = lv           # the easiest reading a learner could have met
    return rank, level, len(seed["rows"]), puls["count"]


def attach_parts(expressions, rank, level, lemmas=None):
    """Join every part onto the list and the validated levels.

    A part is a word FORM, not a lemma: "таким чином" is the instrumental of
    "такий" plus the instrumental of "чин", and joining the forms straight
    onto a lemma list finds neither. So each part resolves in two steps and
    records which one worked: the form itself when the list has it (function
    words and nominatives already are lemmas), otherwise the lemmatizer's
    normal forms in order. The map is committed by --snapshot so CI re-derives
    this without pymorphy3 installed.
    """
    lemmas = lemmas or {}
    for x in expressions:
        parts = []
        for w in x["text"].replace(ELLIPSIS, " ").split():
            key = w.lower()
            if key in rank or key in level:
                parts.append({"word": w, "lemma": key, "via": "form",
                              "rank": rank.get(key), "level": level.get(key)})
                continue
            hit = None
            for cand in lemmas.get(key, []):
                if cand in rank or cand in level:
                    hit = cand
                    break
            if hit:
                parts.append({"word": w, "lemma": hit, "via": "lemma",
                              "rank": rank.get(hit), "level": level.get(hit)})
            else:
                first = (lemmas.get(key) or [None])[0]
                parts.append({"word": w, "lemma": first, "via": "unresolved",
                              "rank": None, "level": None})
        x["parts"] = parts
        x["partsViaLemma"] = sum(1 for p in parts if p["via"] == "lemma")
        x["partsUnresolved"] = sum(1 for p in parts if p["via"] == "unresolved")
        known = [p["level"] for p in parts if p["level"]]
        x["allPartsOnList"] = all(p["rank"] for p in parts)
        x["allPartsLeveled"] = len(known) == len(parts)
        x["gatingLevel"] = max(known, key=lambda l: LEVEL_IDX[l]) if known else None
        x["maxPartRank"] = max((p["rank"] for p in parts if p["rank"]), default=None)
        x["wordCount"] = len(parts)


def lemmatize_words(words):
    """Normal forms for every part word, via pymorphy3 over the VESUM dictionary.

    Snapshot-time only: the result is committed so the build, the tests and CI
    never need the analyzer. Every reading is kept in the analyzer's own order
    and the join picks the first that the list knows, so the choice is visible
    in the committed map rather than made here.
    """
    import pymorphy3
    import pymorphy3_dicts_uk
    m = pymorphy3.MorphAnalyzer(lang="uk")
    out = {}
    for w in sorted(words):
        forms = []
        for parse in m.parse(w):
            nf = fold(parse.normal_form).lower()
            if nf not in forms:
                forms.append(nf)
        out[w] = forms
    return {
        "lemmatizer": "pymorphy3 " + pymorphy3.__version__,
        "dictionary": "pymorphy3-dicts-uk " + pymorphy3_dicts_uk.__version__,
        "note": "normal forms per part word, in the analyzer's own order; the join takes the first one thread 01's list or the validated map knows. The stage-3 usage tables used pymorphy3-dicts-uk 2.4.1.1.1663094765; this is a later dictionary and is recorded rather than assumed to agree.",
        "snapshot": SNAPSHOT_DATE,
        "words": out,
    }


# ---------------------------------------------------------------------------
# The corpus count (the measurement the unigram dictionary cannot make)
# ---------------------------------------------------------------------------

def count_corpus(path, expressions):
    """Occurrences of every expression variant over the corpus prefix."""
    contiguous = collections.defaultdict(list)   # first token -> [(key, tuple)]
    discont = []                                 # (key, head tuple, tail tuple)
    part_words = set()
    for x in expressions:
        for v in x["variants"]:
            key = (x["id"], v["text"])
            if v["discontinuous"] and ELLIPSIS in v["text"]:
                head, _, tail = v["text"].partition(ELLIPSIS)
                h, t = tuple(tokens(head)), tuple(tokens(tail))
                if h and t:
                    discont.append((key, h, t))
                    continue
            seq = tuple(tokens(v["text"]))
            if len(seq) > 1:
                contiguous[seq[0]].append((key, seq))
        for p in x["parts"]:
            part_words.add(p["word"].lower())   # tokens are folded and lowercased

    hits = collections.Counter()
    part_hits = collections.Counter()
    lines = 0
    total_tokens = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            lines += 1
            toks = tokens(line)
            if not toks:
                continue
            total_tokens += len(toks)
            for w in toks:
                if w in part_words:
                    part_hits[w] += 1
            for i, w in enumerate(toks):
                for key, seq in contiguous.get(w, ()):
                    if toks[i:i + len(seq)] == list(seq):
                        hits[key] += 1
            for key, h, t in discont:
                # both halves, in order, inside one sentence line
                start = find_seq(toks, h)
                if start >= 0 and find_seq(toks, t, start + len(h)) >= 0:
                    hits[key] += 1
    return {
        "source": CORPUS_SOURCE, "url": CORPUS_URL, "license": "CC-BY-SA (Wikipedia text)",
        "snapshot": SNAPSHOT_DATE, "lines": lines, "tokens": total_tokens,
        "matcher": "whole-token sequence match after folding case, stress, apostrophes and the Latin i; a discontinuous connective counts when both halves appear in order inside one sentence line",
        "comparability": "the same file prefix as the stage-3 usage tables but NOT the same subset: that parse kept only the 194242 lines passing a clean-sentence filter (30 to 400 characters, at least 5 spaces, no Latin runs or markup) and counted 2880835 parsed tokens. The filter was built to select readable example sentences and drops exactly the short lines connectives live on, so it is not applied here. This denominator is therefore larger and the two per-million rates are not interchangeable.",
        "variantHits": {f"{k[0]}\t{k[1]}": n for k, n in sorted(hits.items())},
        "partHits": dict(sorted(part_hits.items())),
    }


def find_seq(toks, seq, start=0):
    n = len(seq)
    first = seq[0]
    for i in range(start, len(toks) - n + 1):
        if toks[i] == first and toks[i:i + n] == list(seq):
            return i
    return -1


# ---------------------------------------------------------------------------
# PARSEME: the validation read, one direction only
# ---------------------------------------------------------------------------

def read_parseme(dirpath, expressions):
    """Which of OUR expressions the gold corpus independently attests.

    Reads .cupt, matches PARSEME's annotated MWEs against this table's
    expressions by surface or lemma sequence, and records only the matches.
    PARSEME MWEs that are not in this table are counted, never listed: the
    corpus is CC-BY-NC-SA and its inventory is not ours to redistribute.
    """
    wanted = {}
    for x in expressions:
        for v in x["variants"]:
            seq = tuple(tokens(v["text"].replace(ELLIPSIS, " ")))
            if len(seq) > 1:
                wanted.setdefault(seq, set()).add(x["id"])

    matched = collections.defaultdict(lambda: collections.Counter())
    cats = collections.Counter()
    sentences = tokens_seen = instances = 0
    files = []
    for name in sorted(os.listdir(dirpath)):
        if not name.endswith(".cupt"):
            continue
        files.append(name)
        for surfaces, lemmas, mwes in read_cupt(os.path.join(dirpath, name)):
            sentences += 1
            tokens_seen += len(surfaces)
            for idx, (cat, members) in sorted(mwes.items()):
                instances += 1
                cats[cat] += 1
                for seq_src in (tuple(fold(surfaces[i]).lower() for i in members),
                                tuple(fold(lemmas[i]).lower() for i in members)):
                    for eid in wanted.get(seq_src, ()):
                        matched[eid][cat] += 1
    return {
        "source": "PARSEME Shared Task corpora, edition 2.0, Ukrainian (Kanishcheva, Shvedova, Sytar); annotated over GRAC news text",
        "url": "https://hdl.handle.net/11372/LRT-6123",
        "license": "CC-BY-NC-SA-4.0",
        "redistributable": False,
        "wall": "NonCommercial. Read as validation only, never vendored and never shipped: this file holds the matched IDs of expressions already in the license-clean inventory, no PARSEME sentence and no PARSEME-only expression. The public release, the browser tier and the ukvocab package carry aggregate figures only.",
        "snapshot": SNAPSHOT_DATE, "files": files,
        "corpus": {"sentences": sentences, "tokens": tokens_seen, "mweInstances": instances,
                   "categories": len(cats)},
        "publishedClaims": {
            "readme": {"sentences": 12078, "tokens": 198555, "mwes": 5993},
            "totalStatsFile": {"sentences": 10955, "tokens": 179580, "mwes": 5432},
            "note": "the release ships two sets of figures that disagree. Counting the .cupt files reconciles with the README (the 21-token gap is the multiword token ranges and empty nodes this reader skips), not with total-stats.md. Counted here rather than repeated from either.",
        },
        "matched": {eid: dict(sorted(c.items())) for eid, c in sorted(matched.items())},
    }


def read_cupt(path):
    """Yield (surfaces, lemmas, mwes) per sentence, all keyed by token id.

    mwes maps PARSEME's per-sentence MWE index to (category, [token ids]).
    """
    surfaces, lemmas, mwes, order = {}, {}, {}, []

    def flush():
        return ({i: surfaces[i] for i in order},
                {i: lemmas[i] for i in order},
                {k: (cat, [i for i in order if i in set(ids)]) for k, (cat, ids) in mwes.items()})

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                if order:
                    yield flush()
                surfaces, lemmas, mwes, order = {}, {}, {}, []
                continue
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 11:
                continue
            tid = cols[0]
            if "-" in tid or "." in tid:
                continue                  # multiword token ranges and empty nodes
            i = int(tid)
            order.append(i)
            surfaces[i] = cols[1]
            lemmas[i] = cols[2] if cols[2] != "_" else cols[1]
            field = cols[10]
            if field in ("*", "_", ""):
                continue
            for item in field.split(";"):
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    idx, cat = item.split(":", 1)
                    mwes.setdefault(idx, (cat, []))[1].append(i)
                elif item in mwes:
                    mwes[item][1].append(i)
    if order:
        yield flush()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(expressions, meta, corpus, parseme, rank, level, list_size, puls_count, lemmas):
    attach_parts(expressions, rank, level, lemmas["words"])
    hits = collections.Counter()
    for key, n in corpus["variantHits"].items():
        eid, _, _variant = key.partition("\t")
        hits[eid] += n
    million = corpus["tokens"] / 1_000_000 if corpus["tokens"] else 0

    for x in expressions:
        n = hits[x["id"]]
        x["occurrences"] = n
        x["perMillion"] = round(n / million, 2) if million else None
        x["attested"] = n > 0
        # the comparison that makes the point: the rarest part against the unit
        part_counts = [corpus["partHits"].get(p["word"].lower(), 0) for p in x["parts"]]
        x["rarestPartOccurrences"] = min(part_counts) if part_counts else 0
        x["unitShareOfRarestPart"] = round(n / x["rarestPartOccurrences"], 4) if x["rarestPartOccurrences"] else None

    expressions.sort(key=lambda x: (-x["occurrences"], x["text"]))

    attested = [x for x in expressions if x["attested"]]
    connectives = [x for x in expressions if x["kind"] == "connective"]
    phrases = [x for x in expressions if x["kind"] == "phrase"]
    all_parts_known = [x for x in expressions if x["allPartsLeveled"]]
    # THE FINDING: an expression whose every part is validated at or below B1
    # is, word by word, "already known" to a lemma-list coverage figure.
    invisible = [x for x in all_parts_known
                 if LEVEL_IDX[x["gatingLevel"]] <= LEVEL_IDX["B1"]]
    per_gating = collections.Counter(x["gatingLevel"] for x in expressions if x["gatingLevel"])
    per_kind = collections.Counter(x["kind"] for x in expressions)
    per_words = collections.Counter(x["wordCount"] for x in expressions)
    cats = collections.Counter()
    for x in connectives:
        for c in x["cats"]:
            cats[c] += 1

    pm = parseme or {}
    matched = pm.get("matched", {})
    full = {
        "snapshot": SNAPSHOT_DATE,
        "sources": {
            "connectives": {"name": "UK-DiMLex, a computational lexicon of Ukrainian discourse connectives (Scheffler, Solopova, Zolotarenko, Razno, ICTERI 2021)",
                            "url": "https://github.com/TScheffler/UK_DiMLex", "license": "MIT",
                            "entries": meta["dimlex"]["entries"],
                            "quirks": meta["dimlex"]["quirks"]},
            "minimums": {"a1": meta["borodinA1"], "a2": meta["borodinA2"]},
            "levels": {"name": "Ukrainian Vocabulary Profile (PULS), the validated join onto this list",
                       "license": "CC-BY-NC-SA-4.0", "labeledLemmas": puls_count},
            "ranks": {"name": "UberText 2.0 lemma frequency list, thread 01's top-12,000", "listSize": list_size},
            "partLemmas": {k: lemmas[k] for k in ("lemmatizer", "dictionary", "note")},
            "corpus": {k: corpus[k] for k in ("source", "url", "license", "lines", "tokens", "matcher")},
        },
        "license": "CC-BY-NC-SA-4.0 (the part levels are the profile's, CC BY-NC-SA 4.0 by permission; the inventory itself is MIT and CC-BY)",
        "expressions": expressions,
        "counts": {
            "expressions": len(expressions),
            "connectives": len(connectives),
            "phrases": len(phrases),
            "alsoInMinimum": sum(1 for x in expressions if x["inMinimum"]),
            "variants": sum(len(x["variants"]) for x in expressions),
            "discontinuous": sum(1 for x in expressions if any(v["discontinuous"] for v in x["variants"])),
            "attested": len(attested),
            "unattested": len(expressions) - len(attested),
            "allPartsOnList": sum(1 for x in expressions if x["allPartsOnList"]),
            "allPartsLeveled": len(all_parts_known),
            "parts": sum(x["wordCount"] for x in expressions),
            "partsViaForm": sum(x["wordCount"] - x["partsViaLemma"] - x["partsUnresolved"] for x in expressions),
            "partsViaLemma": sum(x["partsViaLemma"] for x in expressions),
            "partsUnresolved": sum(x["partsUnresolved"] for x in expressions),
            "occurrences": sum(x["occurrences"] for x in expressions),
        },
        "perKind": dict(sorted(per_kind.items())),
        "perWordCount": {str(k): v for k, v in sorted(per_words.items())},
        "perGatingLevel": {l: per_gating[l] for l in LEVELS if per_gating[l]},
        "connectiveCats": dict(sorted(cats.items())),
        "finding": {
            "invisible": len(invisible),
            "ofLeveled": len(all_parts_known),
            "pct": round(100 * len(invisible) / len(all_parts_known), 1) if all_parts_known else None,
            "statement": "every part validated at B1 or easier, so a coverage figure computed word by word counts the expression as already known",
        },
        "downloads": {
            "multiword": "/downloads/ukrainian-frequency/b1-extension/multiword.csv",
            "parts": "/downloads/ukrainian-frequency/b1-extension/multiword-parts.csv",
        },
        "parseme": {
            "source": pm.get("source"), "url": pm.get("url"), "license": pm.get("license"),
            "redistributable": False,
            "corpus": pm.get("corpus"),
            "matchedExpressions": len(matched),
            "ofExpressions": len(expressions),
            "matchedPct": round(100 * len(matched) / len(expressions), 1) if expressions else None,
            "matchedConnectives": sum(1 for x in connectives if x["id"] in matched),
            "matchedPhrases": sum(1 for x in phrases if x["id"] in matched),
            "note": "an independent gold annotation of the same expressions, read in one direction: no expression enters this table because PARSEME has it. Aggregates only; the per-expression read is walled into b1-multiword.parseme.json and excluded from the release and the package because the corpus is NonCommercial.",
        } if parseme else None,
    }
    return full


def write_outputs(full, check=False):
    changed = []

    def emit(path, text):
        if check:
            have = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if have != text:
                changed.append(os.path.relpath(path, ROOT))
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    emit(os.path.join(DATA, "b1-multiword.json"),
         json.dumps(full, ensure_ascii=False, indent=0) + "\n")

    # public CSV: no PARSEME column; PARSEME is read as validation only
    rows = ["id,expression,kind,words,variants,discontinuous,sources,cats,senses,minimum_levels,gating_level,all_parts_on_list,all_parts_leveled,max_part_rank,occurrences,per_million,rarest_part_occurrences"]
    for x in full["expressions"]:
        rows.append(",".join(csv_cell(c) for c in [
            x["id"], x["text"], x["kind"], x["wordCount"], len(x["variants"]),
            "yes" if any(v["discontinuous"] for v in x["variants"]) else "no",
            " ".join(sorted({s["source"] for s in x["sources"]})),
            " ".join(x["cats"]), " ".join(x["senses"]), " ".join(x["minimumLevels"]),
            x["gatingLevel"] or "", "yes" if x["allPartsOnList"] else "no",
            "yes" if x["allPartsLeveled"] else "no", x["maxPartRank"] or "",
            x["occurrences"], x["perMillion"], x["rarestPartOccurrences"],
        ]))
    emit(os.path.join(DL, "multiword.csv"), "\n".join(rows) + "\n")

    parts = ["expression_id,expression,position,word,lemma,resolved_via,rank,level"]
    for x in full["expressions"]:
        for i, p in enumerate(x["parts"], start=1):
            parts.append(",".join(csv_cell(c) for c in [x["id"], x["text"], i, p["word"], p["lemma"] or "",
                                                        p["via"], p["rank"] or "", p["level"] or ""]))
    emit(os.path.join(DL, "multiword-parts.csv"), "\n".join(parts) + "\n")

    # browser tier: aggregates, the finding, samples; never the full table
    slim = {k: v for k, v in full.items() if k != "expressions"}
    slim["sample"] = [slim_row(x) for x in full["expressions"][:SAMPLE]]
    slim["invisibleSample"] = [slim_row(x) for x in full["expressions"]
                               if x["allPartsLeveled"] and LEVEL_IDX[x["gatingLevel"]] <= LEVEL_IDX["B1"]][:SAMPLE]
    slim["unattestedSample"] = [slim_row(x) for x in sorted(
        [x for x in full["expressions"] if not x["attested"]], key=lambda x: x["text"])][:SAMPLE]
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-b1-multiword.py - do not edit by hand.\n"
        "// Browser-safe tier of the B1 extension's MULTIWORD TABLE (stage 3): the discourse\n"
        "// connectives of UK-DiMLex (MIT) and the multiword entries of the Borodin A1 and A2\n"
        "// minimums (CC-BY-4.0), each with its own ID, the validated level and rank of every\n"
        "// part, and its own count over the same UberText Wikipedia slice the usage tables\n"
        "// used. The PARSEME read is aggregate only (that corpus is NonCommercial). The full\n"
        "// table is src/data/ukrainian-frequency/b1-multiword.json and the public CSVs.\n"
        "export const B1_MULTIWORD = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    emit(os.path.join(LIB, "b1-multiword.data.mjs"), body)
    return changed


def slim_row(x):
    return {"id": x["id"], "text": x["text"], "kind": x["kind"], "english": x["english"],
            "cats": x["cats"], "minimumLevels": x["minimumLevels"], "gatingLevel": x["gatingLevel"],
            "parts": [{"word": p["word"], "lemma": p["lemma"], "via": p["via"], "rank": p["rank"], "level": p["level"]} for p in x["parts"]],
            "occurrences": x["occurrences"], "perMillion": x["perMillion"],
            "rarestPartOccurrences": x["rarestPartOccurrences"],
            "allPartsOnList": x["allPartsOnList"]}


def csv_cell(v):
    s = "" if v is None else str(v)
    return '"' + s.replace('"', '""') + '"' if any(c in s for c in ',"\n') else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="count over the corpus prefix and rewrite the committed snapshots first")
    ap.add_argument("--corpus", help="path to the plain-text corpus prefix (400000 lines)")
    ap.add_argument("--parseme-dir", help="path to the unzipped PARSEME 2.0 UK directory (read, never vendored)")
    ap.add_argument("--check", action="store_true", help="rebuild and fail if anything committed differs")
    args = ap.parse_args()

    expressions, meta = build_inventory()
    rank, level, list_size, puls_count = load_parts_context()

    corpus_path = os.path.join(DATA, "b1-multiword.corpus-counts.json")
    parseme_path = os.path.join(DATA, "b1-multiword.parseme.json")
    lemmas_path = os.path.join(DATA, "b1-multiword.part-lemmas.json")

    if args.snapshot:
        if not args.corpus:
            sys.exit("--snapshot needs --corpus (the plain-text prefix)")
        words = {w.lower() for x in expressions for w in x["text"].replace(ELLIPSIS, " ").split()}
        lemmas = lemmatize_words(words)
        with open(lemmas_path, "w", encoding="utf-8") as fh:
            json.dump(lemmas, fh, ensure_ascii=False, indent=0)
            fh.write("\n")
        print(f"part lemmas: {len(lemmas['words'])} distinct part words via {lemmas['dictionary']}")
        attach_parts(expressions, rank, level, lemmas["words"])
        corpus = count_corpus(args.corpus, expressions)
        with open(corpus_path, "w", encoding="utf-8") as fh:
            json.dump(corpus, fh, ensure_ascii=False, indent=0)
            fh.write("\n")
        print(f"corpus: {corpus['lines']} lines, {corpus['tokens']} tokens, "
              f"{sum(corpus['variantHits'].values())} expression occurrences")
        if args.parseme_dir:
            parseme = read_parseme(args.parseme_dir, expressions)
            with open(parseme_path, "w", encoding="utf-8") as fh:
                json.dump(parseme, fh, ensure_ascii=False, indent=0)
                fh.write("\n")
            print(f"parseme: {parseme['corpus']['mweInstances']} gold MWE instances, "
                  f"{len(parseme['matched'])} of this table's expressions attested")

    corpus = json.load(open(corpus_path, encoding="utf-8"))
    lemmas = json.load(open(lemmas_path, encoding="utf-8"))
    parseme = json.load(open(parseme_path, encoding="utf-8")) if os.path.exists(parseme_path) else None
    full = build(expressions, meta, corpus, parseme, rank, level, list_size, puls_count, lemmas)
    changed = write_outputs(full, check=args.check)
    if args.check:
        if changed:
            print("multiword table drifted from its sources:\n  " + "\n  ".join(changed))
            sys.exit(1)
        print("multiword table re-derives byte-for-byte")
        return
    c = full["counts"]
    f = full["finding"]
    print(f"expressions {c['expressions']} ({c['connectives']} connectives, {c['phrases']} phrases, "
          f"{c['alsoInMinimum']} also in a minimum); {c['variants']} variants, {c['discontinuous']} discontinuous")
    print(f"attested in the slice: {c['attested']}, unattested {c['unattested']}; "
          f"all parts on the list {c['allPartsOnList']}, all parts leveled {c['allPartsLeveled']}")
    print(f"parts {c['parts']}: {c['partsViaForm']} joined as the form, {c['partsViaLemma']} via the lemmatizer, "
          f"{c['partsUnresolved']} unresolved")
    print(f"finding: {f['invisible']} of {f['ofLeveled']} ({f['pct']} percent) are invisible to a word-by-word coverage figure")
    if full["parseme"]:
        p = full["parseme"]
        print(f"parseme validation: {p['matchedExpressions']} of {p['ofExpressions']} ({p['matchedPct']} percent) gold-attested")


if __name__ == "__main__":
    main()
