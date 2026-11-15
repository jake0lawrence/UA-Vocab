#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : the v0.2.0 list audit (evidence pass)
#
# The v0.1.0 list is the UberText 2.0 lemma dictionary's top 12,000 rows,
# re-published as it came. The dictionary was lemmatized automatically, and the
# lemmatizer left rows that are not lemmas at all: an inflected form standing
# as its own lemma (прес-служб, the genitive plural of прес-служба), a
# hyphenated compound split across parts of speech it cannot have (прес-служба
# as a particle and as an adverb), and spellings no dictionary knows
# (прем'єр-міністрий). This pass finds them. It changes nothing.
#
# Every row of the source (not only the top 12,000: v0.2.0 refills the list
# from below whatever it removes) is read against pymorphy3's Ukrainian
# dictionary (VESUM, the same morphology the B1 pipeline uses) and filed into
# one class, with the evidence that put it there:
#
#   ok              the dictionary knows it as a lemma (normal form) of a part
#                   of speech compatible with the row's UD tag
#   pos-mismatch    the dictionary knows the lemma, but never under a part of
#                   speech compatible with the row's tag (прес-служба ADV)
#   inflected-form  the dictionary knows the string only as a FORM of another
#                   lemma, named in `target` (прес-служб -> прес-служба)
#   unknown         the dictionary does not know the string at all. For a
#                   proper noun this is expected (names); for anything else it
#                   is a lemmatizer invention or a real word VESUM lacks
#
# plus one flag independent of class: `ascii_apostrophe`, set when the lemma
# writes the apostrophe as U+0027 where the list's convention is U+2019.
#
# A class is a CANDIDATE, not a verdict. кошти reads as an inflected form of
# кошт, and a learner needs кошти ("funds"); that is why the fixes go through a
# reviewed ledger with a reason per row (list-cleanup.json), never straight
# from this file.
#
# Not run in CI (needs the 89 MB source dictionary and pymorphy3). Writes the
# committed evidence snapshot src/data/ukrainian-frequency/list-audit.json.
#
#   curl -sSL -o ubertext_freq.csv.xz \
#     https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz
#   pip install pymorphy3 pymorphy3-dicts-uk
#   python3 scripts/ukrainian-frequency/audit-list.py ubertext_freq.csv.xz
#
# House rule: no em-dashes.
# ============================================================
import csv
import json
import lzma
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "src", "data", "ukrainian-frequency", "list-audit.json")

# the same row filter extract-source.py applies, so ranks line up with v0.1.0
UK = re.compile(r"^[абвгґдеєжзиіїйклмнопрстуфхцчшщьюяАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ'’ʼ\-]+$")
KEEP = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON", "DET", "NUM", "ADP", "CCONJ", "SCONJ", "PART", "INTJ"}
# how deep to read: the top 12,000 plus a margin to refill from
DEPTH = 14000

# pymorphy3 (OpenCorpora-style) part of speech -> the UD tags it is compatible
# with. Deliberately generous: a UD determiner is a pymorphy pronoun or
# adjective, a UD adjective can be a pymorphy participle, a UD adverb can be a
# pymorphy predicative or comparative. pos-mismatch only fires when NO reading
# is compatible.
COMPAT = {
    "NOUN": {"NOUN", "PROPN"},
    "ADJF": {"ADJ", "DET", "NUM", "PROPN", "NOUN"},
    "ADJS": {"ADJ", "ADV"},
    "COMP": {"ADJ", "ADV"},
    "VERB": {"VERB"},
    "INFN": {"VERB"},
    "PRTF": {"ADJ", "VERB", "NOUN"},
    "PRTS": {"ADJ", "VERB"},
    "GRND": {"VERB", "ADV"},
    "NUMR": {"NUM", "DET"},
    "ADVB": {"ADV", "PART", "SCONJ", "CCONJ", "ADP"},
    # pronominal adverbs (де, тут, тоді, завжди) are NPRO in this tag set
    "NPRO": {"PRON", "DET", "NOUN", "ADV", "SCONJ"},
    "PRED": {"ADV", "VERB"},
    "PREP": {"ADP"},
    "CONJ": {"CCONJ", "SCONJ", "PART", "ADV"},
    "PRCL": {"PART", "ADV", "CCONJ", "SCONJ"},
    "INTJ": {"INTJ", "PART"},
}

APOS = re.compile("['ʼ’]")


def fold(s):
    return APOS.sub("’", s).lower()


def read_source(path):
    rows = []
    total = 0
    with lzma.open(path, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r)
        for rec in r:
            if len(rec) < 4:
                continue
            lemma, pos, count, doc_count = rec[0], rec[1], rec[2], rec[3]
            if pos not in KEEP or not UK.match(lemma):
                continue
            if len(lemma) == 1 and pos == "PROPN":
                continue
            try:
                c, dc = int(count), int(doc_count)
            except ValueError:
                continue
            total += c
            rows.append((lemma, pos, c, dc))
    rows.sort(key=lambda x: (-x[2], x[0], x[1]))
    return rows, total


def classify(morph, lemma, pos):
    # VESUM writes the apostrophe as U+0027; the list mostly writes U+2019, and a
    # glyph mismatch would file every apostrophe word as unknown
    parses = morph.parse(APOS.sub("'", lemma))
    known = [p for p in parses if p.is_known]
    key = fold(lemma)
    as_lemma = [p for p in known if fold(p.normal_form) == key]
    compat = [p for p in as_lemma if pos in COMPAT.get(str(p.tag.POS), set())]
    evidence = sorted({f"{p.normal_form}:{p.tag.POS}" for p in known})[:6]
    if compat:
        return "ok", None, evidence
    if as_lemma:
        return "pos-mismatch", None, evidence
    if known:
        # the most probable known reading names the lemma this string is a form of
        best = max(known, key=lambda p: p.score)
        target = best.normal_form
        if lemma[:1].isupper():
            target = target[:1].upper() + target[1:]
        # keep the list's own apostrophe glyph convention
        target = APOS.sub("’", target)
        return "inflected-form", target, evidence
    return "unknown", None, evidence


def main(path):
    import pymorphy3

    morph = pymorphy3.MorphAnalyzer(lang="uk")
    rows, total = read_source(path)
    present = {(fold(l), p) for l, p, _, _ in rows[: DEPTH * 3]}
    out = []
    for i, (lemma, pos, count, doc_count) in enumerate(rows[:DEPTH]):
        cls, target, evidence = classify(morph, lemma, pos)
        row = {"rank": i + 1, "lemma": lemma, "pos": pos, "count": count, "docCount": doc_count, "class": cls}
        if target:
            row["target"] = target
            row["targetInSource"] = (fold(target), pos) in present
        if "'" in lemma:
            row["asciiApostrophe"] = True
        if cls != "ok":
            row["evidence"] = evidence
        out.append(row)

    top = out[:12000]
    summary = {
        "classes": dict(Counter(r["class"] for r in top)),
        "classesNonPropn": dict(Counter(r["class"] for r in top if r["pos"] != "PROPN")),
        "asciiApostrophe": sum(1 for r in top if r.get("asciiApostrophe")),
        "docCountAboveCount": sum(1 for r in top if r["docCount"] > r["count"]),
        "tokensFlagged": sum(r["count"] for r in top if r["class"] != "ok" and r["pos"] != "PROPN"),
    }
    doc = {
        "source": "UberText 2.0 lemma frequency dictionary (lang-uk), ubertext_freq.csv.xz",
        "sourceUrl": "https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz",
        "morphology": "pymorphy3 with pymorphy3-dicts-uk (VESUM, brown-uk / dict_uk)",
        "morphologyVersion": getattr(pymorphy3, "__version__", "unknown"),
        "note": "Candidates only. A class is evidence for review, not a correction; fixes go through list-cleanup.json with a reason per row.",
        "depth": DEPTH,
        "wordTokenUniverse": total,
        "summaryTop12000": summary,
        # only the rows that need a look ship in full; ok rows are counted above
        "flagged": [r for r in out if r["class"] != "ok" or r.get("asciiApostrophe")],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"flagged rows written (to depth {DEPTH}): {len(doc['flagged'])}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: audit-list.py ubertext_freq.csv.xz")
    main(sys.argv[1])
