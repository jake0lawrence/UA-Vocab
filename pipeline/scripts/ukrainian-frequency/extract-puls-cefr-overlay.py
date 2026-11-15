#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02: the VALIDATED CEFR overlay extractor.
#
# One-time, reproducible. NOT run in the build or in CI. Joins the corpus-based,
# expert-validated Ukrainian Vocabulary Profile (Synchak, Starko, Burak, Svystun;
# the PULS platform) onto thread 01's top-12000 frequency list, per lemma.
#
# WHY THIS EXISTS (and why it is the headline of thread 02 now): the validated
# profile used to be browse-only, so the thread could only PROFILE it and fell
# back to an OPEN but UNVALIDATED course overlay (extract-cefr-overlay.py) for the
# joinable signal. Vasyl Starko, a co-author, granted explicit permission to
# redistribute the per-lemma A1 to C1 levels, attributed, and pointed us at the
# public browse interface. scrape-puls-cefr.py harvested the full published list
# to src/data/ukrainian-frequency/puls-cefr.raw.csv; this script joins it.
#
# The join, kept honest and identical in spirit to the open overlay:
#   - PER-LEMMA ONSET LEVEL: a lemma can carry several senses at several levels.
#     Its level is the LOWEST (earliest onset of use), matching how the profile is
#     built ("significant onset of use"). Every raw sense is kept in the snapshot;
#     the collapse policy is explicit here.
#   - POS-AWARE join: a PULS entry only matches our lemma when their parts of
#     speech agree (Ukrainian POS mapped to the same coarse family as the seed's
#     UD tag), so a homograph is dropped, never mislabeled.
#   - CROSS-TAG rules (2026-09-13): the two tag sets draw some lines in different
#     places, and until this date those lines dropped 107 rows that are the same
#     lexeme under two conventions, not homographs (який, цей, той at ranks 12,
#     19 and 35 among them). Ten explicit rules in six groups recover them, each on
#     the row it recovered (the `join` field, also a CSV column) so a reader
#     can filter them back out. The rules are listed in CROSS_TAGS below with
#     the reason for each; the family match always takes precedence, and a
#     spelling PULS knows only at an unrelated family is still dropped.
#   - NO heuristic, NO gold-override: unlike the open overlay, every level here IS
#     the validated one, so every label's confidence is "validated". The rigor
#     layer is different: coverage, level-vs-frequency coherence, and a direct
#     cross-check of the free open overlay against this validated map.
#
# SNAPSHOT, NOT FINAL: Starko noted the profile "is not the final version; there
# will be changes." Everything this writes is stamped with SNAPSHOT_DATE and the
# page presents it as a dated snapshot, never as the final map.
#
# LICENSE: the per-lemma levels are (c) the PULS authors, redistributed with their
# permission, attribution required. Only the factual lemma-to-level assignment for
# lemmas already on thread 01's list is redistributed (never definitions, examples,
# or guidewords). See puls-cefr.SOURCE.md. The license (CC BY-NC-SA 4.0) and the
# citation string in META are the authors' own, confirmed 2026-09-24.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import argparse
import csv
import html
import json
import math
import os

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_IDX = {lvl: i + 1 for i, lvl in enumerate(LEVELS)}
CHECKPOINTS = [1000, 2000, 5000, 12000]
SAMPLE_PER_LEVEL = 6
SNAPSHOT_DATE = "2026-07-23"

# The rank distribution (B1 extension, stage 2). Where each validated level
# actually falls on thread 01's ranks, published as a finding of its own. The
# draft B1 plan proposed selecting B1 candidates from a hardcoded 2000 to 4500
# rank band; BAND_FILTER is that band, measured against the validated labels so
# the page can show what it would have kept and what it would have cut.
BAND_WIDTH = 1000
BANDS = 12
QUANTILES = [10, 25, 50, 75, 90]
BAND_FILTER = (2000, 4500)  # inclusive
SPREAD_SAMPLE = 12
# The shallowest / deepest B1 lists are restricted to content words so the
# reader sees vocabulary, not particles or the odd capitalized homograph.
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV"}

# Seed UD tag -> coarse family (identical to extract-cefr-overlay.py so the two
# overlays compare fairly).
FAMILY = {
    "NOUN": "noun", "PROPN": "noun",
    "VERB": "verb",
    "ADJ": "adj", "DET": "adj",
    "ADV": "adv",
    "NUM": "num",
    "PRON": "pron",
    "PART": "part",
    "ADP": "adp",
    "CCONJ": "conj", "SCONJ": "conj", "CONJ": "conj",
    "INTJ": "intj",
}
# PULS Ukrainian POS label -> the same coarse family. "незмінюване слово"
# (indeclinable word) has no clean UD family, so it stays a wildcard (matches on
# lemma alone, never dropped as a homograph).
PULS_FAMILY = {
    "іменник": "noun",
    "прикметник": "adj",
    "дієслово": "verb", "дієслово (недок.)": "verb", "дієслово (док.)": "verb",
    "прислівник": "adv",
    "числівник": "num",
    "вигук": "intj",
    "займенник": "pron",
    "частка": "part",
    "прийменник": "adp",
    "сполучник": "conj",
    "незмінюване слово": None,
}

# The cross-tag rules. Seed UD tag -> the PULS labels it may also match when
# no same-family entry exists. Each rule names its reason, which is the
# documentation the page and the source note carry.
#   DET <-> займенник: UD tags the possessive, demonstrative and quantifying
#     words (мій, цей, той, весь, який) as determiners; the Ukrainian tradition
#     PULS follows calls them pronouns. Same lexemes.
#   ADJ / DET / PRON <-> числівник: ordinals (перший, другий) are adjectives in
#     UD and numerals in PULS; один, кілька, багато likewise.
#   ADP <-> прислівник: words that serve as preposition and adverb (довкола,
#     позаду, всередині) are tagged by function in the corpus and by lexeme in
#     the profile.
#   PART <-> прислівник / сполучник: ще, щоб, хоч, тобто; particle in UD,
#     adverb or conjunction in PULS.
#   NOUN <-> прикметник and ADJ <-> іменник: substantivized adjectives
#     (військовий, дорослий, старий, вчений). The seed's rank belongs to one
#     reading and the profile's level to the lexeme; the row keeps both and
#     says so.
#   any <-> незмінюване слово: the profile's indeclinable-word class (можна,
#     треба, варто, шкода) has no UD family, so it matches whatever tag the
#     corpus gave the word.
CROSS_TAGS = {
    "DET": ["займенник", "числівник"],
    "ADJ": ["числівник", "іменник"],
    "PRON": ["числівник"],
    "ADP": ["прислівник"],
    "PART": ["прислівник", "сполучник"],
    "NOUN": ["прикметник"],
}
CROSS_TAGS_ANY = ["незмінюване слово"]
CROSS_TAG_RULES = [
    {"seedPos": "DET", "pulsPos": "займенник", "why": "UD determiners are pronouns in the Ukrainian tradition"},
    {"seedPos": "DET", "pulsPos": "числівник", "why": "quantifying determiners are numerals in PULS"},
    {"seedPos": "ADJ", "pulsPos": "числівник", "why": "ordinals are adjectives in UD and numerals in PULS"},
    {"seedPos": "PRON", "pulsPos": "числівник", "why": "pronominal readings of a numeral"},
    {"seedPos": "ADP", "pulsPos": "прислівник", "why": "preposition and adverb readings of one lexeme"},
    {"seedPos": "PART", "pulsPos": "прислівник", "why": "particle and adverb readings of one lexeme"},
    {"seedPos": "PART", "pulsPos": "сполучник", "why": "particle and conjunction readings of one lexeme"},
    {"seedPos": "NOUN", "pulsPos": "прикметник", "why": "substantivized adjective; rank is the nominal reading, level is the lexeme"},
    {"seedPos": "ADJ", "pulsPos": "іменник", "why": "substantivized adjective; rank is the adjectival reading, level is the lexeme"},
    {"seedPos": "*", "pulsPos": "незмінюване слово", "why": "the indeclinable-word class has no UD family"},
]


def family(tag):
    return FAMILY.get(tag)


def fold_apostrophe(s):
    """The list writes the apostrophe as U+2019, PULS as U+0027 (once decoded),
    and some sources as U+02BC. One join key for all three."""
    return s.replace("\u2019", "'").replace("\u02bc", "'")


def load_puls(raw_path):
    """(lemma_lower, family) -> lowest level; lemma_lower -> lowest level; and
    (lemma_lower, PULS label) -> lowest level for the cross-tag rules."""
    by_key = {}
    by_lemma = {}
    by_tag = {}
    with open(raw_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lvl = r["level"]
            if lvl not in LEVEL_IDX:
                continue
            fam = PULS_FAMILY.get(r["pos_uk"], None)
            # The harvest kept the server-rendered text verbatim, and the platform
            # renders the apostrophe as the HTML entity &#39; (ім&#39;я). Decode it
            # here, at the join, so the 125 apostrophe lemmas match the list.
            for variant in [v.strip() for v in html.unescape(r["lemma"]).split(",")]:
                if not variant or " " in variant:  # phrase/idiom, not a single lemma
                    continue
                v = fold_apostrophe(variant.lower())
                if v not in by_lemma or LEVEL_IDX[lvl] < LEVEL_IDX[by_lemma[v]]:
                    by_lemma[v] = lvl
                t = (v, r["pos_uk"])
                if t not in by_tag or LEVEL_IDX[lvl] < LEVEL_IDX[by_tag[t]]:
                    by_tag[t] = lvl
                if fam is not None:
                    k = (v, fam)
                    if k not in by_key or LEVEL_IDX[lvl] < LEVEL_IDX[by_key[k]]:
                        by_key[k] = lvl
    return by_key, by_lemma, by_tag


def join_rows(puls_by_key, puls_by_lemma, seed, puls_by_tag=None):
    """Three ways a seed row joins, recorded on the row as `join`:
    `pos-family` (the parts of speech agree), `lemma-only` (the seed POS has no
    family to compare), or `cross-tag:<seed UD tag>-><PULS label>` (one of the
    CROSS_TAGS rules). A spelling PULS knows only at an unrelated family is
    dropped and counted, never mislabeled."""
    puls_by_tag = puls_by_tag or {}
    rows = []
    dropped_pos = 0
    dropped = []
    recovered = {}
    for i, r in enumerate(seed["rows"]):
        lem = fold_apostrophe(r["lemma"].lower())
        fam = family(r["pos"])
        lvl = None
        via = None
        if fam is not None and (lem, fam) in puls_by_key:
            lvl = puls_by_key[(lem, fam)]
            via = "pos-family"
        elif fam is None and lem in puls_by_lemma:
            lvl = puls_by_lemma[lem]  # seed POS unmappable: match on lemma alone
            via = "lemma-only"
        else:
            # The cross-tag rules: the same lexeme under the other convention.
            # Lowest level across the rules that fire, the rule recorded.
            for tag in CROSS_TAGS.get(r["pos"], []) + CROSS_TAGS_ANY:
                if (lem, tag) in puls_by_tag:
                    cand = puls_by_tag[(lem, tag)]
                    if lvl is None or LEVEL_IDX[cand] < LEVEL_IDX[lvl]:
                        lvl = cand
                        via = f"cross-tag:{r['pos']}->{tag}"
            if via is not None:
                recovered[via] = recovered.get(via, 0) + 1
        if lvl is None:
            # PULS knows the spelling but only at an unrelated POS family: homograph.
            if lem in puls_by_lemma:
                dropped_pos += 1
                dropped.append({"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"]})
            continue
        rows.append({"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"],
                     "level": lvl, "validated": True, "confidence": "validated", "join": via})
    return rows, dropped_pos, {"recovered": recovered, "dropped": dropped}


def _rankdata(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def _median(nums):
    s = sorted(nums)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _quantile(sorted_vals, p):
    """Linear-interpolation quantile (p in [0, 1]) on a pre-sorted list, rounded
    half-up to a whole rank. The CI test re-derives it in JavaScript with the
    same arithmetic, so keep this exactly this simple."""
    n = len(sorted_vals)
    if n == 0:
        return None
    i = (n - 1) * p
    lo = math.floor(i)
    hi = math.ceil(i)
    v = sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)
    return int(math.floor(v + 0.5))


def rank_distribution(rows, levels_present):
    """Where each validated level falls on the frequency ranks. Per level: the
    rank quantiles and the per-thousand-band counts. Plus what the draft plan's
    hardcoded rank band would have kept, and the B1 shallowest / deepest content
    words, which are the concrete face of the finding."""
    by_level = {}
    for lvl in levels_present:
        ranks = sorted(r["rank"] for r in rows if r["level"] == lvl)
        per_band = [0] * BANDS
        for k in ranks:
            per_band[(k - 1) // BAND_WIDTH] += 1
        by_level[lvl] = {
            "count": len(ranks),
            "quantiles": {f"p{q}": _quantile(ranks, q / 100) for q in QUANTILES},
            "perBand": per_band,
            "bandsSpanned": sum(1 for n in per_band if n > 0),
        }

    lo, hi = BAND_FILTER
    in_band = [r for r in rows if lo <= r["rank"] <= hi]
    per_level_in_band = {lvl: sum(1 for r in in_band if r["level"] == lvl) for lvl in levels_present}
    b1_total = by_level.get("B1", {}).get("count", 0)
    b1_kept = per_level_in_band.get("B1", 0)
    band_filter = {
        "lo": lo,
        "hi": hi,
        "size": hi - lo + 1,
        "labeled": len(in_band),
        "unlabeled": (hi - lo + 1) - len(in_band),
        "perLevel": per_level_in_band,
        "b1Kept": b1_kept,
        "b1KeptPct": round(b1_kept / b1_total * 1000) / 10 if b1_total else 0,
        "b1ShareOfLabeledPct": round(b1_kept / len(in_band) * 1000) / 10 if in_band else 0,
    }

    b1_rows = [r for r in rows if r["level"] == "B1"]
    pos_split = {}
    for r in b1_rows:
        pos_split[r["pos"]] = pos_split.get(r["pos"], 0) + 1
    pos_split = dict(sorted(pos_split.items(), key=lambda kv: (-kv[1], kv[0])))
    content = [r for r in b1_rows if r["pos"] in CONTENT_POS]
    pick = lambda r: {"rank": r["rank"], "lemma": r["lemma"], "pos": r["pos"]}
    b1 = {
        "contentPos": sorted(CONTENT_POS),
        "posSplit": pos_split,
        "shallowest": [pick(r) for r in content[:SPREAD_SAMPLE]],
        "deepest": [pick(r) for r in content[-SPREAD_SAMPLE:]],
    }

    return {
        "bandWidth": BAND_WIDTH,
        "bands": BANDS,
        "quantiles": QUANTILES,
        "byLevel": by_level,
        "bandFilter": band_filter,
        "b1": b1,
    }


def cross_check(rows, overlay_path):
    """Direct agreement of the free, UNVALIDATED open overlay against this
    validated map, on the lemmas both cover. Measured against the open overlay's
    immutable heuristicLevel (the pure course first-occurrence, BEFORE any
    gold-override), so the comparison is not circular. This supersedes the tiny
    hand-curated n=114 gold sample the open overlay reports: it is now measured on
    the full overlap."""
    if not os.path.exists(overlay_path):
        return None
    prev = json.load(open(overlay_path, encoding="utf-8"))
    open_heur = {r["lemma"].lower(): r.get("heuristicLevel", r["level"]) for r in prev["rows"]}
    valid_by_lemma = {r["lemma"].lower(): r["level"] for r in rows}
    both = [(open_heur[l], valid_by_lemma[l]) for l in valid_by_lemma if l in open_heur]
    n = len(both)
    if n == 0:
        return None
    exact = sum(1 for o, v in both if o == v)
    within1 = sum(1 for o, v in both if abs(LEVEL_IDX[o] - LEVEL_IDX[v]) <= 1)
    return {
        "source": "learn-ukrainian open overlay (heuristic, pre-override) vs PULS validated",
        "nBoth": n,
        "exact": exact,
        "exactPct": round(exact / n * 1000) / 10,
        "within1": within1,
        "within1Pct": round(within1 / n * 1000) / 10,
    }


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    ap.add_argument("--repo-root", default=repo_root)
    args = ap.parse_args()

    data_dir = os.path.join(args.repo_root, "src", "data", "ukrainian-frequency")
    seed = json.load(open(os.path.join(data_dir, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    raw_path = os.path.join(data_dir, "puls-cefr.raw.csv")

    puls_by_key, puls_by_lemma, puls_by_tag = load_puls(raw_path)
    rows, dropped_pos, join_report = join_rows(puls_by_key, puls_by_lemma, seed, puls_by_tag)
    cross = [r for r in rows if r["join"].startswith("cross-tag:")]
    by_rule = {}
    for r in cross:
        by_rule.setdefault(r["join"], []).append(r)
    # A spelling the overlay carries at two ranks (the seed's tagger split one
    # word into two readings): counted so the doubling is a published number.
    spelled = {}
    for r in rows:
        spelled.setdefault(fold_apostrophe(r["lemma"].lower()), []).append(r["rank"])
    doubled = sum(1 for v in spelled.values() if len(v) > 1)

    levels_present = [lvl for lvl in LEVELS if any(r["level"] == lvl for r in rows)]
    per_level = {lvl: sum(1 for r in rows if r["level"] == lvl) for lvl in levels_present}
    per_band = {}
    for r in rows:
        band = (r["rank"] - 1) // 1000 + 1
        per_band[band] = per_band.get(band, 0) + 1
    labeled_in_top_n = {n: sum(1 for r in rows if r["rank"] <= n) for n in CHECKPOINTS}

    # Coherence with native-usage frequency. Median rank per well-sampled level
    # (>= 5) should rise A1 -> C1 if the validated level tracks frequency at all;
    # Spearman over every row quantifies how weakly.
    COHERENCE_MIN_N = 5
    median_rank = {}
    for lvl in levels_present:
        lvl_ranks = [r["rank"] for r in rows if r["level"] == lvl]
        if len(lvl_ranks) >= COHERENCE_MIN_N:
            median_rank[lvl] = int(_median(lvl_ranks))
    xs = [LEVEL_IDX[r["level"]] for r in rows]
    ys = [r["rank"] for r in rows]
    spearman = round(_pearson(_rankdata(xs), _rankdata(ys)) * 1000) / 1000

    xcheck = cross_check(rows, os.path.join(data_dir, "cefr-overlay.json"))
    spread = rank_distribution(rows, levels_present)

    sample = []
    for lvl in levels_present:
        sample.extend([r for r in rows if r["level"] == lvl][:SAMPLE_PER_LEVEL])
    sample.sort(key=lambda r: r["rank"])

    meta = {
        "source": "Ukrainian Vocabulary Profile (PULS): Synchak, O., Starko, V., Burak, M., Svystun, M.",
        "citation": "Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026",
        "sourceUrl": "https://puls.peremova.org/",
        "paperUrl": "https://elex.link/elex2025/wp-content/uploads/eLex2025-29-Synchak_etal.pdf",
        "license": "CC-BY-NC-SA-4.0",
        "permission": "Per-lemma levels redistributed with the authors' permission (V. Starko, 2026-07); licensed CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24). Attribution required; NonCommercial.",
        "snapshot": SNAPSHOT_DATE,
        "final": False,
        "basis": "corpus-based, expert-validated CEFR vocabulary profile (21 UFL textbooks, cross-checked against BRUK and GRAC-17a)",
        "method": "per-lemma onset level (lowest across senses); POS-aware join onto the top-12000 frequency list, with six explicit cross-tag rules for the same lexeme under the two tag conventions (recorded per row); unrelated homographs dropped",
        "validated": True,
        "listSize": len(seed["rows"]),
        "count": len(rows),
        "coveragePct": round(len(rows) / len(seed["rows"]) * 1000) / 10,
        "levelsPresent": levels_present,
        "perLevel": per_level,
        "perBand": {str(b): per_band.get(b, 0) for b in range(1, 13)},
        "labeledInTopN": {str(n): labeled_in_top_n[n] for n in CHECKPOINTS},
        "droppedHomographs": dropped_pos,
        "droppedSample": join_report["dropped"][:12],
        "crossTag": {
            "since": "2026-09-13",
            "rules": CROSS_TAG_RULES,
            "recovered": len(cross),
            "perRule": {k: len(v) for k, v in sorted(by_rule.items(), key=lambda kv: -len(kv[1]))},
            "perLevel": {lvl: sum(1 for r in cross if r["level"] == lvl) for lvl in levels_present},
            "inTop1000": sum(1 for r in cross if r["rank"] <= 1000),
            "sample": {k: [{"rank": r["rank"], "lemma": r["lemma"], "pos": r["pos"], "level": r["level"]} for r in v[:6]] for k, v in by_rule.items()},
        },
        "joinCounts": {via: sum(1 for r in rows if r["join"] == via) for via in ["pos-family", "lemma-only"]},
        "doubledSpellings": doubled,
        "coherence": {"medianRankByLevel": median_rank, "spearman": spearman},
        "crossCheck": xcheck,
        "rankDistribution": spread,
        "download": "/downloads/ukrainian-frequency/validated-cefr/lemmas.csv",
        "distributionDownload": "/downloads/ukrainian-frequency/validated-cefr/rank-distribution.csv",
    }

    full = dict(meta)
    full["rows"] = rows
    with open(os.path.join(data_dir, "puls-cefr.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    dl_dir = os.path.join(args.repo_root, "public", "downloads", "ukrainian-frequency", "validated-cefr")
    os.makedirs(dl_dir, exist_ok=True)
    with open(os.path.join(dl_dir, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,level,confidence,join\n")
        for r in rows:
            fh.write(f"{r['rank']},{r['lemma']},{r['pos']},{r['level']},{r['confidence']},{r['join']}\n")
    # The rank distribution as open data: one row per (level, thousand-rank band).
    with open(os.path.join(dl_dir, "rank-distribution.csv"), "w", encoding="utf-8") as fh:
        fh.write("level,band,rank_from,rank_to,count\n")
        for lvl in levels_present:
            for b, n in enumerate(spread["byLevel"][lvl]["perBand"]):
                fh.write(f"{lvl},{b + 1},{b * BAND_WIDTH + 1},{(b + 1) * BAND_WIDTH},{n}\n")

    lib_dir = os.path.join(args.repo_root, "src", "lib", "ukrainian-frequency")
    slim = {**meta, "sample": [dict(r) for r in sample]}
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-puls-cefr-overlay.py - do not edit by hand.\n"
        "// Browser-safe tier of the VALIDATED CEFR overlay (thread 02): the corpus-based,\n"
        "// expert-validated Ukrainian Vocabulary Profile (PULS; Synchak, Starko, Burak,\n"
        "// Svystun) joined onto the top-12000 frequency list, per lemma, A1 to C1. Redistributed\n"
        "// with the authors' permission as a DATED SNAPSHOT (not the final map). The full\n"
        "// per-lemma table is the committed src/data/ukrainian-frequency/puls-cefr.json and the\n"
        "// public CSV. See puls-cefr.SOURCE.md.\n"
        "export const PULS_CEFR = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(lib_dir, "puls-cefr.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    print(f"validated overlay rows: {len(rows)} ({meta['coveragePct']}%); dropped homographs (POS): {dropped_pos}; cross-tag recovered: {len(cross)} {meta['crossTag']['perRule']}; doubled spellings: {doubled}")
    print(f"levels present: {levels_present}")
    print(f"per level: {per_level}")
    print(f"coherence: spearman={spearman}, median rank by level={median_rank}")
    if xcheck:
        print(f"cross-check (open heuristic vs validated): n={xcheck['nBoth']}, "
              f"exact={xcheck['exactPct']}%, within-one={xcheck['within1Pct']}%")


if __name__ == "__main__":
    main()
