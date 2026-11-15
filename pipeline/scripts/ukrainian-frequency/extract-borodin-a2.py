#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02: the Borodin/Lazarenko A2 lexical-minimum join.
#
# One-time, reproducible. NOT run in the build or in CI. Joins the "1000 i 1
# slovo" A2 lexical minimum (Borodin, Lazarenko; Europa-Universitat Viadrina,
# CC-BY-4.0) onto thread 01's top-12000 frequency list, cross-references the
# joined lemmas against the two CEFR overlays already on the page, and reads the
# book's own thematic dictionary as a second axis.
#
# WHY THIS EXISTS: thread 02 already carries the A1 volume of this series, whose
# provenance note recorded the open seam plainly: "The A2 volume exists but has
# not been shared machine-readable." It has since been published open access
# (DOI 10.11584/opus4-1448, CC-BY-4.0), so the seam closes, and the two levels
# can be read against each other and against the same frequency spine.
#
# WHAT IS NEW HERE, beyond replaying the A1 join one level up:
#   - LEVEL-TO-LEVEL. The A1 and A2 minimums are the same authors' same series,
#     so the A2 entries that are NOT in A1 are a clean read of what one CEFR step
#     actually costs, measured in frequency ranks rather than in word counts.
#   - THE THEMATIC AXIS. The A1 list arrived as a flat column. The A2 book also
#     prints its vocabulary regrouped under 51 topic headings, which lets the
#     teachability trade be asked per semantic field: not just HOW MUCH of a
#     pedagogical minimum a news-heavy frequency core misses, but WHICH FIELDS it
#     misses. That is the question thread 02 could not previously ask.
#
# The join, kept honest (same rules as the A1 extractor, one addition):
#   - ENTRIES, NOT LEMMAS: the authors' unit is the published entry, which can be
#     a single word, an aspect pair, a masculine/feminine pair, a variant set or
#     a phrase. Every entry is kept verbatim; parsing only EXTRACTS candidate
#     headwords, it never rewrites.
#   - LEMMA-STRING JOIN, LOWEST RANK: the list carries no part of speech, so the
#     join is by lemma string against the highest-frequency seed lemma with that
#     spelling. Coarser than the POS-aware overlays, and the page says so.
#   - AN ENTRY WITH NO SINGLE-WORD CANDIDATE IS A PHRASE and is counted, never
#     force-joined.
#   - ADDITION: APOSTROPHE AND HOMOGLYPH FOLDING. The A2 book sets the Ukrainian apostrophe as
#     U+02BC in some entries and U+2019 in others, while the frequency list uses
#     U+2019; folding them is required for the join to see 13 entries it would
#     otherwise report as off-list. This folds apostrophe variants for MATCHING
#     only. Display text stays verbatim. The same applies to the Latin lookalikes
#     the book sets in place of Cyrillic characters in a few words (see
#     HOMOGLYPHS): correct on the page, wrong in the character stream.
#
# LICENSE: CC-BY-4.0 (the publication's own license), attribution required.
# Only the factual entry list and the factual joins are redistributed.
#
#   python3 scripts/ukrainian-frequency/extract-borodin-a2.py
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import json
import math
import os
import re
import unicodedata

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_IDX = {lvl: i + 1 for i, lvl in enumerate(LEVELS)}
CHECKPOINTS = [1000, 2000, 5000, 12000]
SNAPSHOT_DATE = "2026-07-28"

# The authors' separators between alternative headwords inside one entry.
# En dash only WITH surrounding space (aspect pairs); a bare hyphen stays inside
# a word (по-українськи). "=" marks a synonym pair, "≠" an antonym pair.
SEP = re.compile(r"\s*(?:/|,|;|=|≠|\s–\s)\s*")
GRAMMAR_NOTES = {"док.", "недок.", "…", "...", "*"}
APOSTROPHES = "ʼ’‘`´"
# Latin letters that are visually identical to a Cyrillic letter in this book's
# typeface. The published PDF sets a handful of words with a Latin lookalike in
# place of the Cyrillic character (verified at the glyph level: "cонцезахисний"
# and "cвятковий" both open with U+0063 LATIN SMALL LETTER C, not U+0441). The
# word is correct on the page and wrong only in the character stream, so this
# folds the lookalike back for MATCHING; display text stays verbatim.
HOMOGLYPHS = {
    "a": "а", "c": "с", "e": "е", "i": "і", "o": "о", "p": "р", "x": "х", "y": "у",
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "І", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
}
CYRILLIC = re.compile(r"[А-Яа-яЄєІіЇїҐґ]")


def strip_accents(s):
    # Remove the pedagogical stress accent but keep й/ї intact: decompose, drop
    # the combining acute only, recompose.
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", s).replace("́", ""))


def fold_homoglyphs(s):
    """Fold Latin lookalikes to Cyrillic, but ONLY inside a token that is already
    mostly Cyrillic, so a genuinely Latin token is left alone ("ID-kartka" must
    not become Cyrillic). Applied for matching only."""
    out = []
    for token in re.split(r"(\s+)", s):
        if CYRILLIC.search(token):
            token = "".join(HOMOGLYPHS.get(ch, ch) for ch in token)
        out.append(token)
    return "".join(out)


def match_key(s):
    s = strip_accents(s)
    for ch in APOSTROPHES:
        s = s.replace(ch, "’")
    return fold_homoglyphs(s).lower()


def clean_piece(p):
    return p.strip().strip("!?.… ").strip()


def candidates(entry):
    """All candidate headword strings for one entry: single-word pieces from the
    main text and from parenthetical groups, folded for matching."""
    parens = re.findall(r"\(([^)]*)\)", entry)
    main = re.sub(r"\([^)]*\)", " ", entry)
    main_pieces = [clean_piece(x) for x in SEP.split(main)]
    main_pieces = [x for x in main_pieces if x]
    paren_pieces = []
    for grp in parens:
        for x in SEP.split(grp):
            x = clean_piece(x)
            if x and x not in GRAMMAR_NOTES:
                paren_pieces.append(x)
    single = []
    for x in main_pieces + paren_pieces:
        if " " not in x:
            w = match_key(x)
            if w and w not in GRAMMAR_NOTES and w not in single:
                single.append(w)
    is_phrase = all(" " in x for x in main_pieces) if main_pieces else False
    return single, is_phrase


def pct(numerator, denominator):
    """One-decimal percent, rounded HALF UP.

    Python's round() is banker's rounding and JavaScript's Math.round() is not,
    so the two disagree on exact .5 cases (62.5 tenths: Python 6.2, JS 6.3). The
    page re-derives these figures live in the browser and CI re-derives them
    again, so the Python side has to round the way JavaScript does or a true
    number fails its own check.
    """
    if not denominator:
        return 0
    return math.floor(numerator / denominator * 1000 + 0.5) / 10


def fmt_pct(value):
    """Render a percent for CSV the way JSON.parse would hand it back, so the
    shipped file matches the byte-for-byte rebuild in the drift guard."""
    return f"{value:g}"


def median(values):
    """Median, or None when there is nothing to take a median of.

    Not 0: a theme whose units all fall outside the frequency list has NO median
    rank, and publishing 0 reads as "rank 0", the most frequent word there is.
    """
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) // 2


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    data_dir = os.path.join(repo_root, "src", "data", "ukrainian-frequency")

    def load(name):
        return json.load(open(os.path.join(data_dir, name), encoding="utf-8"))

    raw = load("borodin-a2.raw.json")
    a1_raw = load("borodin-a1.raw.json")
    seed = load("ubertext-lemmas-top12k.json")
    puls = load("puls-cefr.json")
    overlay = load("cefr-overlay.json")

    # Best (lowest) rank per seed lemma string.
    seed_best = {}
    for i, r in enumerate(seed["rows"]):
        k = match_key(r["lemma"])
        if k not in seed_best:
            seed_best[k] = {"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"], "count": r["count"]}

    # Validated + open levels per lemma string (lowest level wins on collision).
    puls_level = {}
    for r in puls["rows"]:
        k = match_key(r["lemma"])
        if k not in puls_level or LEVEL_IDX[r["level"]] < LEVEL_IDX[puls_level[k]]:
            puls_level[k] = r["level"]
    open_level = {}
    for r in overlay["rows"]:
        k = match_key(r["lemma"])
        lvl = r.get("heuristicLevel", r["level"])
        if k not in open_level or LEVEL_IDX[lvl] < LEVEL_IDX[open_level[k]]:
            open_level[k] = lvl

    # Every headword the A1 minimum already claims, for the level-to-level read.
    a1_headwords = set()
    for e in a1_raw["entries"]:
        cands, _ = candidates(e)
        a1_headwords.update(cands)

    # Dedupe entries, keeping first occurrence and the authors' order.
    seen = set()
    unique_entries = []
    for e in raw["entries"]:
        if e not in seen:
            seen.add(e)
            unique_entries.append(e)
    duplicate_lines = len(raw["entries"]) - len(unique_entries)

    rows = []
    for e in unique_entries:
        cands, is_phrase = candidates(e)
        best = None
        matched_via = None
        for c in cands:
            hit = seed_best.get(c)
            if hit and (best is None or hit["rank"] < best["rank"]):
                best = hit
                matched_via = c
        row = {
            "entry": e,
            "kind": "phrase" if is_phrase else "word",
            "headwords": cands,
            "inA1": bool(cands) and any(c in a1_headwords for c in cands),
        }
        if best:
            row.update({
                "matched": True,
                "matchedForm": matched_via,
                "rank": best["rank"],
                "lemma": best["lemma"],
                "pos": best["pos"],
            })
            key = match_key(best["lemma"])
            if puls_level.get(key):
                row["pulsLevel"] = puls_level[key]
            if open_level.get(key):
                row["openLevel"] = open_level[key]
        else:
            row["matched"] = False
        rows.append(row)

    matched = [r for r in rows if r["matched"]]
    unmatched_words = [r for r in rows if not r["matched"] and r["kind"] == "word"]
    phrases = [r for r in rows if r["kind"] == "phrase"]

    # Distinct seed lemmas reached (several entries can share one lemma).
    by_lemma = {}
    for r in matched:
        k = match_key(r["lemma"])
        if k not in by_lemma or r["rank"] < by_lemma[k]["rank"]:
            by_lemma[k] = r
    distinct = sorted(by_lemma.values(), key=lambda r: r["rank"])
    n_distinct = len(distinct)

    per_band = {}
    for r in distinct:
        band = (r["rank"] - 1) // 1000 + 1
        per_band[band] = per_band.get(band, 0) + 1
    in_top_n = {n: sum(1 for r in distinct if r["rank"] <= n) for n in CHECKPOINTS}
    ranks = [r["rank"] for r in distinct]

    total_tokens = seed["word_token_universe_total"]
    matched_tokens = sum(seed_best[k]["count"] for k in by_lemma)
    coverage_pct = pct(matched_tokens, total_tokens)

    # A same-size frequency core, for the teachability trade.
    head_tokens = sum(r["count"] for r in seed["rows"][:n_distinct])
    freq_core_pct = pct(head_tokens, total_tokens)

    # Consensus with the validated PULS map, on the distinct matched lemmas.
    puls_rows = [r for r in distinct if r.get("pulsLevel")]
    puls_dist = {}
    for r in puls_rows:
        puls_dist[r["pulsLevel"]] = puls_dist.get(r["pulsLevel"], 0) + 1
    n_puls = len(puls_rows)
    a1a2 = puls_dist.get("A1", 0) + puls_dist.get("A2", 0)
    consensus = {
        "source": "Borodin/Lazarenko A2 membership vs the validated PULS level, on the lemmas both cover",
        "nBoth": n_puls,
        "atA1": puls_dist.get("A1", 0),
        "atA2": puls_dist.get("A2", 0),
        "withinA2": a1a2,
        "withinA2Pct": pct(a1a2, n_puls),
        "aboveA2": n_puls - a1a2,
        "aboveA2Pct": pct(n_puls - a1a2, n_puls),
        "perLevel": {lvl: puls_dist[lvl] for lvl in LEVELS if lvl in puls_dist},
    }

    open_rows = [r for r in distinct if r.get("openLevel")]
    open_a1a2 = sum(1 for r in open_rows if r["openLevel"] in ("A1", "A2"))
    open_check = {
        "source": "Borodin/Lazarenko A2 membership vs the open course overlay (heuristic), on the lemmas both cover",
        "nBoth": len(open_rows),
        "withinA2": open_a1a2,
        "withinA2Pct": pct(open_a1a2, len(open_rows)),
    }

    # Level-to-level: what one CEFR step costs, in ranks rather than in counts.
    carried = [r for r in rows if r["inA1"]]
    added = [r for r in rows if not r["inA1"]]
    added_matched = [r for r in added if r["matched"]]
    step = {
        "source": "A2 entries measured against the same authors' A1 minimum",
        "a1Entries": len(set(a1_raw["entries"])),
        "carriedFromA1": len(carried),
        "newAtA2": len(added),
        "newAtA2Pct": pct(len(added), len(unique_entries)),
        "newMatched": len(added_matched),
        "newOffList": sum(1 for r in added if not r["matched"] and r["kind"] == "word"),
        "medianRankCarried": median([r["rank"] for r in carried if r["matched"]]),
        "medianRankNew": median([r["rank"] for r in added_matched]),
    }

    # The thematic axis: the book's own 51 topic groupings, joined the same way.
    themes = []
    for block in raw["themes"]:
        words = block["words"]
        t_rows = []
        for w in words:
            cands, is_phrase = candidates(w)
            best = None
            for c in cands:
                hit = seed_best.get(c)
                if hit and (best is None or hit["rank"] < best["rank"]):
                    best = hit
            t_rows.append({"word": w, "rank": best["rank"] if best else None, "phrase": is_phrase})
        hit_ranks = [r["rank"] for r in t_rows if r["rank"]]
        off = [r["word"] for r in t_rows if not r["rank"] and not r["phrase"]]
        themes.append({
            "theme": block["theme"],
            "words": len(t_rows),
            "matched": len(hit_ranks),
            "offList": len(off),
            "offListPct": pct(len(off), len(t_rows)),
            "medianRank": median(hit_ranks),
            "offListSample": off[:6],
        })
    themes_sorted = sorted(themes, key=lambda t: (-t["offListPct"], t["theme"]))
    thematic_words = sum(t["words"] for t in themes)
    thematic_off = sum(t["offList"] for t in themes)

    off_list_sample = [r["entry"] for r in unmatched_words[:12]]
    sample = distinct[:6] + distinct[max(0, n_distinct // 2 - 3):n_distinct // 2 + 3] + distinct[-4:]
    sample = [
        {k: r[k] for k in ("rank", "lemma", "pos", "entry") if k in r}
        | ({"pulsLevel": r["pulsLevel"]} if r.get("pulsLevel") else {})
        for r in sample
    ]

    meta = {
        "source": "1000 i 1 slovo: Lexical Minimum in Ukrainian as a Foreign Language, Level A2 (Borodin, Lazarenko)",
        "sourceUrl": "https://doi.org/10.11584/opus4-1448",
        "urn": raw["urn"],
        "license": "CC-BY-4.0",
        "publisher": "Europa-Universitat Viadrina Frankfurt (Oder)",
        "provided": (
            "Published open access under CC-BY-4.0 (2026-05-08) and pointed at by co-author "
            "K. Borodin, 2026-07-28. The word list was extracted from the publication's own "
            "PDF by scripts/ukrainian-frequency/parse-borodin-a2-pdf.py; see "
            "borodin-a2.SOURCE.md. Attribution required."
        ),
        "snapshot": SNAPSHOT_DATE,
        "validated": False,
        "basis": "corpus-based A2 lexical minimum for Ukrainian as a foreign language (GRAK and Ukrainian Web 2022 corpora plus editorial criteria), published as a CC-BY-4.0 guide; an expert selection, not a corpus-validated CEFR profile",
        "method": "entries kept verbatim; candidate headwords extracted from the authors' separators and parentheses; apostrophe variants folded for matching only; lemma-string join onto the top-12000 frequency list at the best rank (no POS in the source, so the join is coarser than the POS-aware overlays)",
        "listSize": len(seed["rows"]),
        "rawLines": len(raw["entries"]),
        "duplicateLines": duplicate_lines,
        "entries": len(unique_entries),
        "wordEntries": len(unique_entries) - len(phrases),
        "phraseEntries": len(phrases),
        "grammarNotes": len(raw.get("grammar", {})),
        "matchedEntries": len(matched),
        "matchedLemmas": n_distinct,
        "offListWordEntries": len(unmatched_words),
        "offListSample": off_list_sample,
        "medianRank": median(ranks),
        "maxRank": max(ranks) if ranks else 0,
        "coveragePct": coverage_pct,
        "freqCorePct": freq_core_pct,
        "perBand": {str(b): per_band.get(b, 0) for b in range(1, 13)},
        "matchedInTopN": {str(n): in_top_n[n] for n in CHECKPOINTS},
        "consensus": consensus,
        "openCheck": open_check,
        "step": step,
        "themeCount": len(themes),
        "thematicWords": thematic_words,
        "thematicOffList": thematic_off,
        "thematicOffListPct": pct(thematic_off, thematic_words),
        "themes": themes_sorted,
        "download": "/downloads/ukrainian-frequency/borodin-a2/lemmas.csv",
        "themesDownload": "/downloads/ukrainian-frequency/borodin-a2/themes.csv",
    }

    full = dict(meta)
    full["rows"] = rows
    with open(os.path.join(data_dir, "borodin-a2.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    dl_dir = os.path.join(repo_root, "public", "downloads", "ukrainian-frequency", "borodin-a2")
    os.makedirs(dl_dir, exist_ok=True)
    with open(os.path.join(dl_dir, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("entry,kind,in_a1,matched,rank,lemma,pos,puls_level\n")
        for r in rows:
            entry = '"' + r["entry"].replace('"', '""') + '"'
            fh.write(",".join([
                entry, r["kind"], "yes" if r["inA1"] else "no",
                "yes" if r["matched"] else "no",
                str(r.get("rank", "")), r.get("lemma", ""), r.get("pos", ""),
                r.get("pulsLevel", ""),
            ]) + "\n")
    with open(os.path.join(dl_dir, "themes.csv"), "w", encoding="utf-8") as fh:
        fh.write("theme,words,matched,off_list,off_list_pct,median_rank\n")
        for t in themes:
            fh.write(",".join([
                '"' + t["theme"].replace('"', '""') + '"',
                str(t["words"]), str(t["matched"]), str(t["offList"]),
                fmt_pct(t["offListPct"]),
                "" if t["medianRank"] is None else str(t["medianRank"]),
            ]) + "\n")
    with open(os.path.join(dl_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "# 1000 i 1 slovo (A2) joined onto the Ukrainian frequency list\n\n"
            "The \"1000 i 1 slovo\" A2 lexical minimum for Ukrainian as a foreign\n"
            "language (Kseniia Borodin and Olesia Lazarenko; Europa-Universitat Viadrina\n"
            "Frankfurt (Oder), 2026; https://doi.org/10.11584/opus4-1448), joined onto the\n"
            "jakelawrence.xyz/research/ukrainian-frequency top-12,000 lemma frequency list\n"
            "(UberText 2.0, lang-uk).\n\n"
            "lemmas.csv: one row per published entry, verbatim. The entry text, whether it\n"
            "is a word or phrase entry, whether the same authors' A1 minimum already claims\n"
            "it, and, where a headword matches a lemma on the frequency list, the frequency\n"
            "rank, lemma, POS, and the validated PULS CEFR level where one exists (Synchak\n"
            "et al. 2025, by permission).\n\n"
            "The minimum carries no part of speech, so the join is by spelling: `rank`,\n"
            "`lemma` and `pos` are the spelling's most frequent reading on the list, and\n"
            "`puls_level` is the EASIEST level the profile gives any reading of that\n"
            "spelling. The two could belong to different readings (the A1 volume has\n"
            "such rows); in this volume every puls_level matches the validated level of\n"
            "its own rank. For a per-reading level, join `rank` to\n"
            "validated-cefr/lemmas.csv.\n\n"
            "themes.csv: the book's own thematic dictionary, one row per topic heading, with\n"
            "how much of that semantic field the frequency list reaches. `words` counts\n"
            "every unit under the heading; `matched` the units that reach the list;\n"
            "`off_list` the single-word units that do not. A phrase unit that does not\n"
            "match is in neither, so matched + off_list can be less than words, and\n"
            "`off_list_pct` is off_list over all words (phrases included).\n\n"
            "Where it fits: this is the syllabus side of the A2 comparison. `in_a1`\n"
            "measures the step from the A1 volume (../borodin-a1/): how many entries are\n"
            "carried over and how much deeper in the corpus the new ones sit. themes.csv\n"
            "shows which semantic fields a news-heavy frequency list misses, and\n"
            "../genre-split/ tests that directly by looking up every word entry here in\n"
            "same-size fiction and news lists. ../minimums-crosswalk/ classifies every\n"
            "disagreement between the two volumes and the whole validated profile; the\n"
            "text profiler offers it as a known-word set; the ukvocab Python package\n"
            "ships it; and its multiword entries are the phrase rows of\n"
            "../b1-extension/multiword.csv.\n"
            "\n"
            "License: CC-BY-4.0 (the publication's own license). Attribute:\n"
            "Borodin, K. and Lazarenko, O., \"1000 i 1 slovo. Leksychnyi minimum z\n"
            "ukrainskoi movy (A2). Navchalnyi posibnyk\". Europa-Universitat Viadrina\n"
            "Frankfurt (Oder), 2026. DOI 10.11584/opus4-1448. Frequency ranks CC-BY-4.0\n"
            "(UberText 2.0, lang-uk); PULS levels CC-BY-NC-SA-4.0 by the authors' permission.\n\n"
            f"Snapshot: {SNAPSHOT_DATE}\n"
        )

    lib_dir = os.path.join(repo_root, "src", "lib", "ukrainian-frequency")
    slim = {**meta, "sample": sample}
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-borodin-a2.py - do not edit by hand.\n"
        "// Browser-safe tier of the Borodin/Lazarenko A2 lexical-minimum join (thread 02):\n"
        "// the \"1000 i 1 slovo\" A2 minimum (Borodin, Lazarenko; CC-BY-4.0, published open\n"
        "// access at DOI 10.11584/opus4-1448) joined onto the top-12000 frequency list,\n"
        "// cross-referenced against the validated PULS CEFR map, read against the same\n"
        "// authors' A1 minimum, and broken out along the book's own thematic dictionary.\n"
        "// The full per-entry table is the committed src/data/ukrainian-frequency/\n"
        "// borodin-a2.json and the public CSVs. See borodin-a2.SOURCE.md.\n"
        "export const BORODIN_A2 = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(lib_dir, "borodin-a2.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    print(f"entries: {len(unique_entries)} (dupes {duplicate_lines}); words {meta['wordEntries']}, phrases {meta['phraseEntries']}")
    print(f"matched entries: {len(matched)} -> distinct lemmas: {n_distinct}; off-list word entries: {len(unmatched_words)}")
    print(f"median rank {meta['medianRank']}, max {meta['maxRank']}, coverage {coverage_pct}% vs same-size frequency core {freq_core_pct}%")
    print(f"in top N: {in_top_n}")
    print(f"PULS: n={n_puls}, within A2 {consensus['withinA2Pct']}%, above A2 {consensus['aboveA2Pct']}%, dist={consensus['perLevel']}")
    print(f"step from A1: carried {step['carriedFromA1']}, new {step['newAtA2']} ({step['newAtA2Pct']}%), median rank carried {step['medianRankCarried']} vs new {step['medianRankNew']}")
    print(f"themes: {len(themes)} covering {thematic_words} units; off-list {thematic_off} ({meta['thematicOffListPct']}%)")
    print("worst-covered themes: " + ", ".join(f"{t['theme']} {t['offListPct']}%" for t in themes_sorted[:4]))
    print(f"off-list sample: {off_list_sample}")


if __name__ == "__main__":
    main()
