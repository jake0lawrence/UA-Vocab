#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : the v0.2.0 list (seed + crosswalk)
#
# v0.1.0 re-published the UberText 2.0 dictionary's top 12,000 rows as they
# came. This builds the candidate v0.2.0 seed from the same source with the
# reviewed cleanup ledger applied (src/data/ukrainian-frequency/list-cleanup.json;
# evidence in list-audit.json, written by audit-list.py):
#
#   1. explicit ledger rows: a merge adds the row's count to its target, a drop
#      removes the row from the list (its tokens stay in the coverage universe:
#      they were real running words, just not assignable to a lemma);
#   2. the apostrophe rule: U+0027 and U+02BC become U+2019, and rows that then
#      coincide merge;
#   3. the name rule: a capitalized lemma tagged anything but PROPN, NOUN or
#      ADJ joins the lowercase common noun when the Ukrainian dictionary knows
#      it as a plain common noun, else the name's PROPN row, else its all-caps
#      abbreviation, else a PROPN row of its own.
#
# The rules run over EVERY source row, not only the top 12,000, so a junk row
# below the cut still pays its tokens to the right lemma, and the list refills
# from below whatever the cleanup removed. Review items in the ledger are not
# applied; they wait on the owner.
#
# Writes (no downstream tier reads either yet; they switch in later passes):
#   src/data/ukrainian-frequency/ubertext-lemmas-top12k.json
#   src/data/ukrainian-frequency/list-v0.2.0-crosswalk.json
#
# The v0.2.0 seed carries no `docs` column. The source's doc_count exceeds its
# own count in 2,553 of the top 12,000 rows (посилання: 817,018 tokens in
# 1,135,001 documents), which a document frequency cannot do; its doc_frequency
# column divides doc_count by a constant near 5.59 million and exceeds 1 for в.
# The source does not define the column, so the list stops republishing it.
#
#   python3 scripts/ukrainian-frequency/build-list-v2.py ubertext_freq.csv.xz
#
# Needs pymorphy3 + pymorphy3-dicts-uk (VESUM) for the name rule's common-noun
# check. Not run in CI (needs the 89 MB source); CI holds the two outputs to each
# other and to the ledger (__tests__/list-v2.test.js).
# House rule: no em-dashes.
# ============================================================
import csv
import json
import lzma
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")

UK = re.compile(r"^[абвгґдеєжзиіїйклмнопрстуфхцчшщьюяАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ'’ʼ\-]+$")
KEEP = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON", "DET", "NUM", "ADP", "CCONJ", "SCONJ", "PART", "INTJ"}
N = 12000
VERSION = "v0.2.0"
APOS = re.compile("['ʼ]")
NAME_OK = {"PROPN", "NOUN", "ADJ"}
PROPER = {"Name", "Surn", "Patr", "Geox", "Orgn", "Trad", "Abbr", "Dist"}


def read_source(path):
    rows = []
    with lzma.open(path, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r)
        for rec in r:
            if len(rec) < 4:
                continue
            lemma, pos, count = rec[0], rec[1], rec[2]
            if pos not in KEEP or not UK.match(lemma):
                continue
            if len(lemma) == 1 and pos == "PROPN":
                continue
            try:
                rows.append((lemma, pos, int(count)))
            except ValueError:
                continue
    return rows


def ranked(rows):
    return sorted(rows, key=lambda x: (-x[2], x[0], x[1]))


def main(path):
    ledger = json.load(open(os.path.join(DATA, "list-cleanup.json"), encoding="utf-8"))
    explicit = {(r["lemma"], r["pos"]): r for r in ledger["rows"]}
    source = read_source(path)
    import pymorphy3

    morph = pymorphy3.MorphAnalyzer(lang="uk")
    common_cache = {}

    def common_noun(low):
        # VESUM knows it as a plain common noun lemma: not a name, surname,
        # patronymic, place, organization, abbreviation or non-standard spelling
        if low not in common_cache:
            common_cache[low] = any(
                p.is_known and p.normal_form == low.replace("\u2019", "'") and p.tag.POS == "NOUN" and not (set(p.tag.grammemes) & PROPER)
                for p in morph.parse(low.replace("\u2019", "'"))
            )
        return common_cache[low]
    universe = sum(c for _, _, c in source)
    v1 = ranked(source)[:N]
    base = {}
    for lemma, pos, count in source:
        k = (APOS.sub("\u2019", lemma), pos)
        base[k] = base.get(k, 0) + count
    v1_rank = {(l, p): i + 1 for i, (l, p, _) in enumerate(v1)}

    # every source row resolves to a destination (lemma, pos) or to None (dropped),
    # with the step that decided it
    def destination(lemma, pos):
        e = explicit.get((lemma, pos))
        if e:
            if e["action"] == "drop":
                return None, "ledger:drop"
            return (e["into"]["lemma"], e["into"]["pos"]), "ledger:merge"
        folded = APOS.sub("’", lemma)
        step = "apostrophe" if folded != lemma else None
        if folded[:1].isupper() and pos not in NAME_OK:
            return name_home(folded), "name-pos"
        return (folded, pos), step

    # A capitalized row the tagger mislabeled finds its home in a fixed order:
    # the common noun capitalized at the start of a sentence (Прес-служба ->
    # прес-служба NOUN), but only when VESUM knows that noun as a plain common
    # noun (the source also holds lowercased names and Russian words: помпео,
    # сегодня); then the name as written (Янукович PROPN); then the abbreviation
    # the lemmatizer title-cased (Тасс -> ТАСС PROPN); otherwise a PROPN row of
    # its own.
    def name_home(lemma):
        low = lemma.lower()
        if (low, "NOUN") in base and common_noun(low):
            return (low, "NOUN")
        for cand in ((lemma, "PROPN"), (lemma.upper(), "PROPN")):
            if cand in base:
                return cand
        return (lemma, "PROPN")

    totals = {}
    absorbed = {}
    fate = {}
    for lemma, pos, count in source:
        dest, step = destination(lemma, pos)
        fate[(lemma, pos)] = (dest, step)
        if dest is None:
            continue
        totals[dest] = totals.get(dest, 0) + count
        if dest != (lemma, pos):
            absorbed.setdefault(dest, []).append({"lemma": lemma, "pos": pos, "count": count, "step": step})

    v2 = ranked([(l, p, c) for (l, p), c in totals.items()])[:N]
    v2_rank = {(l, p): i + 1 for i, (l, p, _) in enumerate(v2)}

    seed = {
        "source": "UberText 2.0 lemma frequency dictionary (lang-uk)",
        "source_file": "ubertext_freq.csv.xz",
        "source_url": "https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz",
        "source_citation": "Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern Ukrainian at Scale. Proc. 2nd Ukrainian NLP Workshop (UNLP), ACL.",
        "version": VERSION,
        "cleanup": "src/data/ukrainian-frequency/list-cleanup.json",
        "extraction": "The v0.1.0 filter (Ukrainian-Cyrillic-alphabetic lemmas with a linguistic UD tag), then the cleanup ledger over every source row: explicit merges and drops, U+0027/U+02BC apostrophes folded to U+2019, capitalized lemmas tagged other than PROPN/NOUN/ADJ joined to the lowercase common noun when VESUM knows it as a plain common noun, else to the name's PROPN row, else to its all-caps abbreviation, else kept as a PROPN row of their own. Top 12000 lemma+POS rows by merged count, ties broken by lemma then POS. The source's doc_count is not carried.",
        "pos_scheme": "Universal Dependencies (UD) v2",
        "word_token_universe_total": universe,
        "n": len(v2),
        "rows": [
            dict({"lemma": l, "pos": p, "count": c}, **({"absorbed": sorted(absorbed[(l, p)], key=lambda a: -a["count"])} if (l, p) in absorbed else {}))
            for l, p, c in v2
        ],
    }

    cross = []
    for lemma, pos, count in v1:
        dest, step = fate[(lemma, pos)]
        row = {"v1Rank": v1_rank[(lemma, pos)], "lemma": lemma, "pos": pos, "count": count}
        if dest is None:
            row["fate"] = "dropped"
        elif dest == (lemma, pos):
            row["fate"] = "kept" if dest in v2_rank else "fell-below"
        else:
            row["fate"] = "merged"
            row["into"] = {"lemma": dest[0], "pos": dest[1]}
        if step:
            row["step"] = step
        if dest is not None and dest in v2_rank:
            row["v2Rank"] = v2_rank[dest]
        cross.append(row)
    entered = [{"v2Rank": v2_rank[(l, p)], "lemma": l, "pos": p, "count": c} for l, p, c in v2 if (l, p) not in v1_rank]

    doc = {
        "from": "v0.1.0",
        "to": VERSION,
        "note": "Every v0.1.0 row once, with what v0.2.0 did to it and the v0.2.0 rank it now counts toward; then the rows that entered from below the v0.1.0 cut. A downstream table keyed on v0.1.0 ranks migrates through this file.",
        "rows": cross,
        "entered": entered,
    }
    with open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    # one row per line: diffable, and a third the size of an indented dump
    line = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(DATA, "list-v0.2.0-crosswalk.json"), "w", encoding="utf-8") as fh:
        head = {k: v for k, v in doc.items() if k not in ("rows", "entered")}
        fh.write(line(head)[:-1] + ',\n"rows":[\n' + ",\n".join(line(r) for r in doc["rows"]) + '\n],\n"entered":[\n' + ",\n".join(line(r) for r in doc["entered"]) + "\n]}\n")

    from collections import Counter
    fates = Counter(r["fate"] for r in cross)
    moved = sum(1 for r in cross if r["fate"] == "kept" and r["v2Rank"] != r["v1Rank"])
    print(f"v0.1.0 rows: {dict(fates)}; kept rows whose rank moved: {moved}; entered: {len(entered)}")
    print(f"universe {universe}; v0.2.0 rows {len(v2)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: build-list-v2.py ubertext_freq.csv.xz")
    main(sys.argv[1])
