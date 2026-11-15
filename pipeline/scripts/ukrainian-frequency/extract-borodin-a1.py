#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02: the Borodin A1 lexical-minimum join.
#
# One-time, reproducible. NOT run in the build or in CI. Joins the "1000 i 1
# slovo" A1 lexical minimum (Borodin, Turkevych; Slavic Language Education 3,
# CC-BY-4.0) onto thread 01's top-12000 frequency list, and cross-references the
# joined lemmas against the two CEFR overlays already on the page (the validated
# PULS map and the open course overlay).
#
# WHY THIS EXISTS: the field census called this list the one independent,
# empirically grounded A1 guideline for Ukrainian, and flagged it "walled"
# (published CC-BY-4.0 but only as a prose PDF behind an anti-bot wall), so the
# model left a seam: a second A1 source that would corroborate A1 by consensus
# but could not be joined. Co-author Kseniia Borodin closed that seam by sending
# the machine-readable list directly (2026-07-27); borodin-a1.SOURCE.md has the
# full provenance. This script folds it in.
#
# The join, kept honest:
#   - ENTRIES, NOT LEMMAS: the authors' unit is the published entry line, which
#     can be a single word, an aspect pair ("розуміти – зрозуміти"), a
#     masculine/feminine pair ("лікар / лікарка"), a variant set ("вчора,
#     учора"), or a phrase ("день народження"). Every unique entry is kept
#     verbatim; parsing only EXTRACTS candidate headwords, it never rewrites.
#   - CANDIDATE HEADWORDS: the entry text outside parentheses is split on the
#     authors' own separators (slash, comma, semicolon, en dash with spaces,
#     equals, does-not-equal); single-word pieces are candidates. Parenthetical
#     single-word pieces are candidates too (the authors use parens both for
#     variant forms, "вперед (уперед)", and to name the lemma behind a phrase,
#     "Що сталося? (Статися)"); grammar notes (док., недок.) and inflected-form
#     lists simply fail to match a lemma and drop out. Combining accents are
#     stripped for matching ("бра́ти" matches "брати"); display text stays
#     verbatim.
#   - LEMMA-STRING JOIN, LOWEST RANK: the list carries no part of speech, so the
#     join is by lemma string (lowercased), against the highest-frequency seed
#     lemma with that spelling; an entry with several matching candidates (an
#     aspect pair) joins at its best rank. This is a coarser join than the
#     POS-aware overlays and the page says so.
#   - AN ENTRY WITH NO SINGLE-WORD CANDIDATE IS A PHRASE and is counted, never
#     force-joined ("день народження" does not get relabeled "день").
#
# LICENSE: CC-BY-4.0 (the publication's own license), attribution required.
# Only the factual entry list and the factual joins are redistributed.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import json
import os
import re
import unicodedata

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_IDX = {lvl: i + 1 for i, lvl in enumerate(LEVELS)}
CHECKPOINTS = [1000, 2000, 5000, 12000]
SNAPSHOT_DATE = "2026-07-27"

# The authors' separators between alternative headwords inside one entry.
# En dash only WITH surrounding space (aspect pairs); a bare hyphen stays inside
# a word (по-українськи). "=" marks a synonym pair, "≠" an antonym pair.
SEP = re.compile(r"\s*(?:/|,|;|=|≠|\s–\s)\s*")
GRAMMAR_NOTES = {"док.", "недок.", "…", "..."}


def strip_accents(s):
    # Remove combining marks (the pedagogical stress accent) but keep й/ї intact:
    # normalize, drop U+0301 only, recompose.
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", s).replace("́", ""))


def clean_piece(p):
    p = p.strip().strip("!?.… ").strip()
    return p


def candidates(entry):
    """All candidate headword strings for one entry: single-word pieces from the
    main text and from parenthetical groups, cleaned for matching."""
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
            w = strip_accents(x).lower()
            if w and w not in single:
                single.append(w)
    is_phrase = all(" " in x for x in main_pieces) if main_pieces else False
    return single, is_phrase


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    data_dir = os.path.join(repo_root, "src", "data", "ukrainian-frequency")

    raw = json.load(open(os.path.join(data_dir, "borodin-a1.raw.json"), encoding="utf-8"))
    seed = json.load(open(os.path.join(data_dir, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    puls = json.load(open(os.path.join(data_dir, "puls-cefr.json"), encoding="utf-8"))
    overlay = json.load(open(os.path.join(data_dir, "cefr-overlay.json"), encoding="utf-8"))

    # Best (lowest) rank per seed lemma string.
    seed_best = {}
    for i, r in enumerate(seed["rows"]):
        k = r["lemma"].lower()
        if k not in seed_best:
            seed_best[k] = {"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"], "count": r["count"]}

    # Validated + open levels per lemma string (lowest level wins on collision).
    puls_level = {}
    for r in puls["rows"]:
        k = r["lemma"].lower()
        if k not in puls_level or LEVEL_IDX[r["level"]] < LEVEL_IDX[puls_level[k]]:
            puls_level[k] = r["level"]
    open_level = {}
    for r in overlay["rows"]:
        k = r["lemma"].lower()
        lvl = r.get("heuristicLevel", r["level"])
        if k not in open_level or LEVEL_IDX[lvl] < LEVEL_IDX[open_level[k]]:
            open_level[k] = lvl

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
        row = {"entry": e, "kind": "phrase" if is_phrase else "word", "headwords": cands}
        if best:
            row.update({
                "matched": True,
                "matchedForm": matched_via,
                "rank": best["rank"],
                "lemma": best["lemma"],
                "pos": best["pos"],
            })
            pl = puls_level.get(best["lemma"].lower())
            ol = open_level.get(best["lemma"].lower())
            if pl:
                row["pulsLevel"] = pl
            if ol:
                row["openLevel"] = ol
        else:
            row["matched"] = False
        rows.append(row)

    matched = [r for r in rows if r["matched"]]
    unmatched_words = [r for r in rows if not r["matched"] and r["kind"] == "word"]
    phrases = [r for r in rows if r["kind"] == "phrase"]

    # Distinct seed lemmas reached (several entries can share one lemma).
    by_lemma = {}
    for r in matched:
        k = r["lemma"].lower()
        if k not in by_lemma or r["rank"] < by_lemma[k]["rank"]:
            by_lemma[k] = r
    distinct = sorted(by_lemma.values(), key=lambda r: r["rank"])
    n_distinct = len(distinct)

    per_band = {}
    for r in distinct:
        band = (r["rank"] - 1) // 1000 + 1
        per_band[band] = per_band.get(band, 0) + 1
    in_top_n = {n: sum(1 for r in distinct if r["rank"] <= n) for n in CHECKPOINTS}
    ranks = sorted(r["rank"] for r in distinct)
    median_rank = ranks[len(ranks) // 2] if len(ranks) % 2 else (ranks[len(ranks) // 2 - 1] + ranks[len(ranks) // 2]) // 2

    # Running-text coverage of the matched set, from the seed's own counts.
    total_tokens = seed["word_token_universe_total"]
    matched_tokens = sum(seed_best[k]["count"] for k in by_lemma)
    coverage_pct = round(matched_tokens / total_tokens * 1000) / 10

    # Consensus with the validated PULS map, on the distinct matched lemmas.
    puls_rows = [r for r in distinct if r.get("pulsLevel")]
    puls_dist = {}
    for r in puls_rows:
        puls_dist[r["pulsLevel"]] = puls_dist.get(r["pulsLevel"], 0) + 1
    n_puls = len(puls_rows)
    a1 = puls_dist.get("A1", 0)
    a1a2 = a1 + puls_dist.get("A2", 0)
    consensus = {
        "source": "Borodin A1 membership vs the validated PULS level, on the lemmas both cover",
        "nBoth": n_puls,
        "atA1": a1,
        "atA1Pct": round(a1 / n_puls * 1000) / 10,
        "withinA2": a1a2,
        "withinA2Pct": round(a1a2 / n_puls * 1000) / 10,
        "perLevel": {lvl: puls_dist[lvl] for lvl in LEVELS if lvl in puls_dist},
    }

    # Same read against the open course overlay's heuristic levels.
    open_rows = [r for r in distinct if r.get("openLevel")]
    open_a1 = sum(1 for r in open_rows if r["openLevel"] == "A1")
    open_a1a2 = sum(1 for r in open_rows if r["openLevel"] in ("A1", "A2"))
    open_check = {
        "source": "Borodin A1 membership vs the open course overlay (heuristic), on the lemmas both cover",
        "nBoth": len(open_rows),
        "atA1": open_a1,
        "atA1Pct": round(open_a1 / len(open_rows) * 1000) / 10 if open_rows else 0,
        "withinA2": open_a1a2,
        "withinA2Pct": round(open_a1a2 / len(open_rows) * 1000) / 10 if open_rows else 0,
    }

    off_list_sample = [r["entry"] for r in unmatched_words[:12]]

    # Sample: the first entries by rank, a slice around the median, and the deepest.
    sample = distinct[:6] + \
        distinct[max(0, n_distinct // 2 - 3):n_distinct // 2 + 3] + distinct[-4:]
    sample = [{k: r[k] for k in ("rank", "lemma", "pos", "entry") if k in r} | (
        {"pulsLevel": r["pulsLevel"]} if r.get("pulsLevel") else {}) for r in sample]

    meta = {
        "source": "1000 i 1 slovo: Lexical Minimum in Ukrainian as a Foreign Language, Level A1 (Borodin, Turkevych)",
        "sourceUrl": "https://doi.org/10.18452/28236",
        "license": "CC-BY-4.0",
        "provided": "Machine-readable list shared by co-author K. Borodin (School of Ukrainian Language and Culture, Ukrainian Catholic University), 2026-07-27, for attributed open republication. Attribution required.",
        "snapshot": SNAPSHOT_DATE,
        "validated": False,
        "basis": "corpus-based A1 lexical minimum for Ukrainian as a foreign language, published as a CC-BY-4.0 guide; an expert selection, not a corpus-validated CEFR profile",
        "method": "entries kept verbatim; candidate headwords extracted from the authors' separators and parentheses; lemma-string join onto the top-12000 frequency list at the best rank (no POS in the source, so the join is coarser than the POS-aware overlays)",
        "listSize": len(seed["rows"]),
        "rawLines": len(raw["entries"]),
        "duplicateLines": duplicate_lines,
        "entries": len(unique_entries),
        "wordEntries": len(unique_entries) - len(phrases),
        "phraseEntries": len(phrases),
        "matchedEntries": len(matched),
        "matchedLemmas": n_distinct,
        "offListWordEntries": len(unmatched_words),
        "offListSample": off_list_sample,
        "medianRank": median_rank,
        "maxRank": ranks[-1],
        "coveragePct": coverage_pct,
        "perBand": {str(b): per_band.get(b, 0) for b in range(1, 13)},
        "matchedInTopN": {str(n): in_top_n[n] for n in CHECKPOINTS},
        "consensus": consensus,
        "openCheck": open_check,
        "download": "/downloads/ukrainian-frequency/borodin-a1/lemmas.csv",
    }

    full = dict(meta)
    full["rows"] = rows
    with open(os.path.join(data_dir, "borodin-a1.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    dl_dir = os.path.join(repo_root, "public", "downloads", "ukrainian-frequency", "borodin-a1")
    os.makedirs(dl_dir, exist_ok=True)
    with open(os.path.join(dl_dir, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("entry,kind,matched,rank,lemma,pos,puls_level\n")
        for r in rows:
            entry = '"' + r["entry"].replace('"', '""') + '"'
            fh.write(",".join([
                entry, r["kind"], "yes" if r["matched"] else "no",
                str(r.get("rank", "")), r.get("lemma", ""), r.get("pos", ""),
                r.get("pulsLevel", ""),
            ]) + "\n")
    with open(os.path.join(dl_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "# 1000 i 1 slovo (A1) joined onto the Ukrainian frequency list\n\n"
            "The \"1000 i 1 slovo\" A1 lexical minimum for Ukrainian as a foreign\n"
            "language (Kseniia Borodin and Oksana Turkevych; Slavic Language Education 3,\n"
            "LANGUAGE-LAB, Humboldt-Universitat zu Berlin; https://doi.org/10.18452/28236),\n"
            "joined onto the jakelawrence.xyz/research/ukrainian-frequency top-12,000\n"
            "lemma frequency list (UberText 2.0, lang-uk).\n\n"
            "One row per published entry, verbatim: the entry text, whether it is a word\n"
            "or phrase entry, and, where a headword matches a lemma on the frequency\n"
            "list, the frequency rank, lemma, POS, and the validated PULS CEFR level\n"
            "where one exists (Synchak et al. 2025, by permission).\n\n"
            "The minimum carries no part of speech, so the join is by spelling: `rank`,\n"
            "`lemma` and `pos` are the spelling's most frequent reading on the list, and\n"
            "`puls_level` is the EASIEST level the profile gives any reading of that\n"
            "spelling. The two can belong to different readings: багато is listed at rank\n"
            "280 as a determiner (validated A2) with puls_level A1, the level of the\n"
            "adverb at rank 542. For a per-reading level, join `rank` to\n"
            "validated-cefr/lemmas.csv instead.\n\n"
            "Where it fits: this is the syllabus side of the A1 comparison. The research\n"
            "page reads it for the two-source consensus (how many of the joined lemmas\n"
            "the validated profile also puts at A1) and for the teachability trade (the\n"
            "share of running text the matched lemmas cover, against a same-size\n"
            "frequency core). ../minimums-crosswalk/ classifies every disagreement\n"
            "between this volume, the A2 volume and the whole profile; the text profiler\n"
            "offers it as a known-word set; the ukvocab Python package ships it; and its\n"
            "multiword entries are the phrase rows of ../b1-extension/multiword.csv. The\n"
            "sibling volume is ../borodin-a2/.\n"
            "\n"
            "License: CC-BY-4.0 (the publication's own license). Attribute:\n"
            "Borodin, K. and Turkevych, O., \"1000 i 1 slovo. Leksychnyi minimum z\n"
            "ukrainskoi movy yak inozemnoi. Riven A1\". Machine-readable list provided\n"
            "by the authors, 2026-07-27. Frequency ranks CC-BY-4.0 (UberText 2.0,\n"
            "lang-uk); PULS levels CC-BY-NC-SA-4.0 by the authors' permission.\n\n"
            f"Snapshot: {SNAPSHOT_DATE}\n"
        )

    lib_dir = os.path.join(repo_root, "src", "lib", "ukrainian-frequency")
    slim = {**meta, "sample": sample}
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-borodin-a1.py - do not edit by hand.\n"
        "// Browser-safe tier of the Borodin A1 lexical-minimum join (thread 02): the\n"
        "// \"1000 i 1 slovo\" A1 minimum (Borodin, Turkevych; CC-BY-4.0, machine-readable\n"
        "// list provided by the authors) joined onto the top-12000 frequency list and\n"
        "// cross-referenced against the validated PULS CEFR map. The full per-entry table\n"
        "// is the committed src/data/ukrainian-frequency/borodin-a1.json and the public\n"
        "// CSV. See borodin-a1.SOURCE.md.\n"
        "export const BORODIN_A1 = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(lib_dir, "borodin-a1.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    print(f"raw lines: {len(raw['entries'])} (dupes {duplicate_lines}); unique entries: {len(unique_entries)}")
    print(f"word entries: {meta['wordEntries']}, phrase entries: {meta['phraseEntries']}")
    print(f"matched entries: {len(matched)} -> distinct lemmas: {n_distinct}; off-list word entries: {len(unmatched_words)}")
    print(f"median rank: {median_rank}, max rank: {ranks[-1]}, coverage: {coverage_pct}%")
    print(f"in top N: {in_top_n}")
    print(f"PULS consensus: n={n_puls}, A1={consensus['atA1Pct']}%, A1-A2={consensus['withinA2Pct']}%, dist={consensus['perLevel']}")
    print(f"open check: n={open_check['nBoth']}, A1={open_check['atA1Pct']}%, A1-A2={open_check['withinA2Pct']}%")
    print(f"off-list sample: {off_list_sample}")


if __name__ == "__main__":
    main()
