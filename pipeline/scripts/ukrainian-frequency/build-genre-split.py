#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 06: the genre split.
#
# Reads the two per-genre lemma lists that genre-freq.py produced and writes the
# committed table, the browser tier and the public download.
#
#   python3 scripts/ukrainian-frequency/build-genre-split.py FICTION.json NEWS.json
#
# THE QUESTION. Thread 02 reports that 229 word entries of the A2 lexical
# minimum do not rank in the top 12,000 of this site's frequency list, and reads
# that as a limit of frequency-first learning. But this site's list is built on
# UberText 2.0's COMBINED corpus, whose largest component by far is news. So the
# finding could mean either of two very different things:
#
#   (a) that vocabulary is genuinely rare in written Ukrainian, or
#   (b) that vocabulary is common, and journalism does not discuss it.
#
# Those have opposite consequences for anyone building a word list, and the
# published claim cannot tell them apart. This measures which one it is.
#
# THE DESIGN. Both genres are UberText 2.0 subcorpora (same crawl, cleaning and
# Russian filtering), lemmatized by the same tool, sampled the same shape, capped
# to the same token count. Genre is the only variable.
#
# WHAT IS AND IS NOT COMPARED. Every figure here is fiction-versus-news, both
# sides measured by THIS pipeline. Nothing is compared against the shipped
# lang-uk ranks, because a different lemmatizer produced those and mixing the two
# would let a lemmatization difference masquerade as a genre difference. The
# shipped `matched` flag is carried through for reference and is never used in a
# headline figure.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import json
import math
import os
import re
import sys
import unicodedata

TOP_N = 12000
SNAPSHOT_DATE = "2026-07-28"
SEP = re.compile(r"\s*(?:/|,|;|=|≠|\s–\s)\s*")
APOS = str.maketrans({"ʼ": "’", "'": "’", "`": "’", "´": "’"})
HOMO = {"a": "а", "c": "с", "e": "е", "i": "і", "o": "о", "p": "р", "x": "х", "y": "у"}
CYR = re.compile(r"[А-Яа-яЄєІіЇїҐґ]")


def norm(w):
    w = unicodedata.normalize("NFC", unicodedata.normalize("NFD", w).replace("́", "")).translate(APOS)
    if CYR.search(w):
        w = "".join(HOMO.get(c, c) for c in w)
    return w.lower().strip("’ ")


def headwords(entry):
    main = re.sub(r"\([^)]*\)", " ", entry)
    out = []
    for p in SEP.split(main):
        p = p.strip(" !?.…*")
        if p and " " not in p:
            w = norm(p)
            if w:
                out.append(w)
    return out


def pct(n, d):
    return math.floor(n / d * 1000 + 0.5) / 10 if d else 0


def repatch_shipped(data_dir):
    """--shipped-only: the genre ranks need the two subcorpus frequency lists,
    which are not committed; the one list-dependent field, `shippedMatched`
    (copied from borodin-a2.json), is not. After the shipped list moves (v0.1.0
    -> v0.2.0) and borodin-a2 is rebuilt, this rewrites that field in the
    committed genre-split.json from the rebuilt A2 join and touches nothing else:
    the public CSVs, the README and the browser tier carry no shipped figure."""
    path = os.path.join(data_dir, "genre-split.json")
    full = json.load(open(path, encoding="utf-8"))
    a2 = json.load(open(os.path.join(data_dir, "borodin-a2.json"), encoding="utf-8"))
    matched = {r["entry"]: r["matched"] for r in a2["rows"] if r["kind"] == "word"}
    changed = 0
    for r in full["rows"]:
        if r["entry"] not in matched:
            sys.exit(f"entry not in borodin-a2.json: {r['entry']}")
        if r["shippedMatched"] != matched[r["entry"]]:
            r["shippedMatched"] = matched[r["entry"]]
            changed += 1
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    print(f"shippedMatched re-read from borodin-a2.json: {changed} of {len(full['rows'])} entries changed")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", ".."))
    data_dir = os.path.join(repo, "src", "data", "ukrainian-frequency")
    if "--shipped-only" in sys.argv:
        repatch_shipped(data_dir)
        return
    if len(sys.argv) < 3:
        sys.exit("usage: build-genre-split.py FICTION.json NEWS.json | --shipped-only")

    fic = json.load(open(sys.argv[1], encoding="utf-8"))
    new = json.load(open(sys.argv[2], encoding="utf-8"))
    if abs(fic["tokens"] - new["tokens"]) > 0.001 * max(fic["tokens"], new["tokens"]):
        sys.exit(f"genres are not size-matched: {fic['tokens']} vs {new['tokens']}")

    fic_rank = {l: i + 1 for i, (l, _) in enumerate(fic["rows"])}
    new_rank = {l: i + 1 for i, (l, _) in enumerate(new["rows"])}

    def rank_of(rank_map, hws):
        r = min((rank_map.get(h, 10 ** 9) for h in hws), default=10 ** 9)
        return r if r <= TOP_N else None

    a2 = json.load(open(os.path.join(data_dir, "borodin-a2.json"), encoding="utf-8"))
    raw = json.load(open(os.path.join(data_dir, "borodin-a2.raw.json"), encoding="utf-8"))

    rows = []
    for r in a2["rows"]:
        if r["kind"] != "word":
            continue
        hws = headwords(r["entry"])
        if not hws:
            continue
        f, n = rank_of(fic_rank, hws), rank_of(new_rank, hws)
        rows.append({
            "entry": r["entry"],
            "fictionRank": f,
            "newsRank": n,
            "only": "fiction" if f and not n else "news" if n and not f else None,
            "shippedMatched": r["matched"],
        })

    both = sum(1 for r in rows if r["fictionRank"] and r["newsRank"])
    only_f = sum(1 for r in rows if r["only"] == "fiction")
    only_n = sum(1 for r in rows if r["only"] == "news")
    neither = sum(1 for r in rows if not r["fictionRank"] and not r["newsRank"])
    in_f = both + only_f
    in_n = both + only_n
    union = both + only_f + only_n

    themes = []
    for t in raw["themes"]:
        units = [w for w in t["words"] if headwords(w)]
        if len(units) < 5:
            continue
        f = sum(1 for w in units if rank_of(fic_rank, headwords(w)))
        n = sum(1 for w in units if rank_of(new_rank, headwords(w)))
        themes.append({
            "theme": t["theme"], "units": len(units),
            "news": n, "fiction": f,
            "newsPct": pct(n, len(units)), "fictionPct": pct(f, len(units)),
            "deltaPct": pct(f, len(units)) - pct(n, len(units)),
        })
    themes.sort(key=lambda t: (-t["deltaPct"], t["theme"]))

    meta = {
        "source": "UberText 2.0 subcorpora (lang-uk): fiction and news, read separately",
        "sourceUrl": "https://lang.org.ua/en/ubertext/",
        "license": "The derived counts are ours; the corpus is lang-uk's UberText 2.0.",
        "snapshot": SNAPSHOT_DATE,
        "question": "Is the vocabulary a frequency list misses rare in Ukrainian, or absent from journalism?",
        "method": (
            "Both genres are UberText 2.0 subcorpora (same crawl, cleaning and Russian "
            "filtering), lemmatized by the same tool (pymorphy3), sampled the same shape, "
            "and capped to the same token count. Genre is the only variable. These ranks "
            "are NOT comparable to this site's shipped lang-uk ranks and are never mixed "
            "with them."
        ),
        "lemmatizer": "pymorphy3 (uk). Not lang-uk's; mis-lemmatizes a few high-frequency pronouns, identically in both genres.",
        "tokensPerGenre": fic["tokens"],
        "newsTokens": new["tokens"],
        "fictionSampling": fic.get("keep", "1/1"),
        "newsSampling": new.get("keep", "1/1"),
        "topN": TOP_N,
        "entries": len(rows),
        "inBoth": both,
        "fictionOnly": only_f,
        "newsOnly": only_n,
        "neither": neither,
        "inFiction": in_f,
        "inNews": in_n,
        "union": union,
        "inFictionPct": pct(in_f, len(rows)),
        "inNewsPct": pct(in_n, len(rows)),
        "unionPct": pct(union, len(rows)),
        "unionGainPct": pct(union, len(rows)) - max(pct(in_f, len(rows)), pct(in_n, len(rows))),
        "fictionRecoversOfNewsMisses": pct(only_f, len(rows) - in_n),
        "newsRecoversOfFictionMisses": pct(only_n, len(rows) - in_f),
        "themes": themes,
        "fictionOnlySample": [r["entry"] for r in rows if r["only"] == "fiction"][:12],
        "newsOnlySample": [r["entry"] for r in rows if r["only"] == "news"][:12],
        "download": "/downloads/ukrainian-frequency/genre-split/entries.csv",
    }

    full = dict(meta)
    full["rows"] = rows
    with open(os.path.join(data_dir, "genre-split.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    dl = os.path.join(repo, "public", "downloads", "ukrainian-frequency", "genre-split")
    os.makedirs(dl, exist_ok=True)
    with open(os.path.join(dl, "entries.csv"), "w", encoding="utf-8") as fh:
        fh.write("entry,fiction_rank,news_rank,only\n")
        for r in rows:
            fh.write(",".join([
                '"' + r["entry"].replace('"', '""') + '"',
                str(r["fictionRank"] or ""), str(r["newsRank"] or ""), r["only"] or "",
            ]) + "\n")
    with open(os.path.join(dl, "themes.csv"), "w", encoding="utf-8") as fh:
        fh.write("theme,units,news,fiction,news_pct,fiction_pct,delta_pct\n")
        for t in themes:
            fh.write(",".join([
                '"' + t["theme"].replace('"', '""') + '"', str(t["units"]),
                str(t["news"]), str(t["fiction"]),
                f"{t['newsPct']:g}", f"{t['fictionPct']:g}", f"{t['deltaPct']:g}",
            ]) + "\n")
    with open(os.path.join(dl, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "# The genre split: fiction against news, same size, same pipeline\n\n"
            "Every word entry of the \"1000 i 1 slovo\" A2 lexical minimum (Borodin and\n"
            "Lazarenko, CC-BY-4.0, https://doi.org/10.11584/opus4-1448) looked up in two\n"
            "frequency lists built from the fiction and news subcorpora of UberText 2.0\n"
            "(lang-uk, https://lang.org.ua/en/ubertext/), each capped to the same token\n"
            "count and lemmatized by the same tool.\n\n"
            "entries.csv: one row per word entry of the A2 minimum (phrase entries are\n"
            "left out). Columns `entry,fiction_rank,news_rank,only`. `entry` is the\n"
            "published entry, verbatim; `only` is `news` or `fiction` when exactly one\n"
            "genre's top 12,000 reaches the entry, blank when both or neither do.\n"
            "\n"
            "`themes.csv`: one row per topic heading of the A2 book that has word entries.\n"
            "Columns `theme,units,news,fiction,news_pct,fiction_pct,delta_pct`: the units\n"
            "under the heading, how many each genre reaches, those as percentages, and\n"
            "`delta_pct`, fiction minus news (positive where fiction reaches more).\n"
            "\n"
            "A blank rank means the entry is outside that genre's top 12,000.\n\n"
            "These ranks are NOT comparable to the main jakelawrence.xyz Ukrainian\n"
            "frequency list, which lang-uk's own lemmatizer produced over the combined\n"
            "corpus. They are comparable only to each other.\n\n"
            "Where it fits: ../borodin-a2/ found that a large share of the A2 minimum does\n"
            "not rank on the main list, which is built mostly from news. This split holds\n"
            "genre as the only variable and finds that fiction and news reach about the\n"
            "same amount of the minimum but different parts of it (news: institutional and\n"
            "geographic words; fiction: domestic and bodily ones), so the gap is mostly a\n"
            "genre effect. Shown as thread 6 of the research page. Nothing joins on these\n"
            "ranks, by design; a test keeps them apart from the thread-01 ranks.\n"
            "\n"
            "License: the entries are the Borodin and Lazarenko A2 minimum (CC-BY-4.0);\n"
            "the ranks derive from UberText 2.0 (lang-uk, CC-BY-4.0). Attribute both.\n"
            "\n"
            f"Tokens per genre: {fic['tokens']:,}\nSnapshot: {SNAPSHOT_DATE}\n"
        )

    lib = os.path.join(repo, "src", "lib", "ukrainian-frequency")
    with open(os.path.join(lib, "genre-split.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(
            "// GENERATED by scripts/ukrainian-frequency/build-genre-split.py - do not edit by hand.\n"
            "// Thread 06, the genre split: the A2 lexical minimum looked up in a FICTION\n"
            "// and a NEWS frequency list built from UberText 2.0 subcorpora at equal size\n"
            "// through one pipeline. These ranks are internally comparable ONLY; they are\n"
            "// not this site's shipped lang-uk ranks. See genre-split.SOURCE.md.\n"
            "export const GENRE_SPLIT = " + json.dumps(meta, ensure_ascii=False, indent=2) + ";\n"
        )

    print(f"entries {len(rows)} | both {both} | fiction-only {only_f} | news-only {only_n} | neither {neither}")
    print(f"news {in_n} ({meta['inNewsPct']}%) | fiction {in_f} ({meta['inFictionPct']}%) | union {union} ({meta['unionPct']}%)")
    print(f"fiction recovers {meta['fictionRecoversOfNewsMisses']}% of what news misses; news {meta['newsRecoversOfFictionMisses']}% of fiction's")
    print("widest themes: " + ", ".join(f"{t['theme']} {t['deltaPct']:+g}" for t in themes[:4]))


if __name__ == "__main__":
    main()
