#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02: the EXPERIMENTAL CEFR overlay extractor.
#
# One-time, reproducible. NOT run in the build or in CI. Two stages:
#
#  1. JOIN (needs --learn-ukrainian, a clone of the external course repo): the
#     one corpus-VALIDATED CEFR profile for Ukrainian (Synchak et al., profiled
#     in cefr.mjs) is browse-only and cannot be joined onto our list. This
#     overlay is the honest complement: an OPEN, joinable, but UNVALIDATED CEFR
#     signal from the learn-ukrainian open course (Krisztian Koos, CC-BY-SA 4.0),
#     whose per-lesson vocabulary lives under
#     curriculum/l2-uk-en/<level>/<module>/vocabulary.yaml with the CEFR level in
#     the path. Three deliberate choices raise the join's quality:
#       - CONCENTRATION, not first-occurrence: a lemma's level is the level where
#         it appears MOST across the course, not merely the earliest lesson (an
#         incidental early appearance no longer drags a word down).
#       - POS-AWARE join: a course entry only matches our lemma when their parts
#         of speech agree, so a homograph (кілька the fish vs the quantifier) is
#         not silently joined to the wrong word.
#       - GOLD-OVERRIDE: where Synchak et al. publish a validated level for a
#         lemma (src/data/.../cefr-gold.json), that level is used and the label is
#         marked "validated". This is a DELIVERY correction; it does not flatter
#         the accuracy number, which is measured on the heuristic BEFORE override.
#
#  2. ENRICH (no clone needed, reuses the committed join): measures the overlay
#     against the gold standard and grades each label. Computes (a) the HEURISTIC
#     agreement with Synchak's published per-lemma levels (exact / within-one,
#     with a 95% confidence interval, since the sample is small), (b) level-vs-
#     frequency COHERENCE (per-level median rank + Spearman rho), and (c) a
#     per-lemma CONFIDENCE tier (validated, frequency-typical, or outlier).
#
# Run stage 1+2 to refresh from the course; run stage 2 alone (omit
# --learn-ukrainian) to re-grade the committed join after editing the gold set.
# CI re-verifies the artifacts against each other and the gold set, never against
# the course clone.
#
# NOTE on a second source: Borodin and Turkevych's "1000+1 Words (A1)" (CC-BY-4.0)
# would corroborate A1 labels via consensus, but it is published only as a prose
# PDF behind an anti-bot wall, so it is not joined. The model leaves a seam for it.
#
# Provenance / licensing: the learn-ukrainian curriculum content is CC-BY-SA 4.0.
# We redistribute only the factual lemma-to-level assignment (never the
# translations, examples, or prose), attribute the source, and license these
# derived overlay artifacts CC-BY-SA 4.0. See cefr-overlay.SOURCE.md.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import argparse
import glob
import json
import math
import os
import re
from collections import Counter

LEVELS = ["a1", "a2", "b1", "b2", "c1", "c2"]
ORDER = {lvl: i for i, lvl in enumerate(LEVELS)}
LEVEL_IDX = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
CHECKPOINTS = [1000, 2000, 5000, 12000]
SAMPLE_PER_LEVEL = 6

# course POS string -> UD-ish tag
POS_MAP = {
    "noun": "NOUN", "n": "NOUN",
    "verb": "VERB", "v": "VERB",
    "adj": "ADJ", "adjective": "ADJ",
    "adv": "ADV", "adverb": "ADV",
    "num": "NUM", "numeral": "NUM",
    "pron": "PRON", "pronoun": "PRON",
    "part": "PART", "particle": "PART",
    "prep": "ADP", "preposition": "ADP",
    "conj": "CONJ", "conjunction": "CONJ",
    "intj": "INTJ", "interjection": "INTJ",
}
# a coarse family so seed UD tags and course tags compare fairly
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


def family(tag):
    return FAMILY.get(tag)


def extract_course(course_root):
    """lemma(lowercased) -> {'levels': Counter, 'pos': Counter(UD tag)} across the core CEFR tracks."""
    out = {}
    for lvl in LEVELS:
        for vf in glob.glob(os.path.join(course_root, "curriculum", "l2-uk-en", lvl, "*", "vocabulary.yaml")):
            with open(vf, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            word = None
            pos = None
            items = []
            for ln in lines:
                m = re.match(r"\s*-\s*(?:word|lemma):\s*(.+?)\s*$", ln)
                if m:
                    if word is not None:
                        items.append((word, pos))
                    word = m.group(1).strip().strip('"').strip("'")
                    pos = None
                    continue
                mp = re.match(r"\s*pos:\s*(.+?)\s*$", ln)
                if mp and word is not None:
                    pos = mp.group(1).strip().strip('"').strip("'").lower()
            if word is not None:
                items.append((word, pos))
            for w, p in items:
                if not w or p == "phrase" or " " in w:
                    continue
                key = w.lower()
                rec = out.setdefault(key, {"levels": Counter(), "pos": Counter()})
                rec["levels"][lvl.upper()] += 1
                ud = POS_MAP.get(p)
                if ud:
                    rec["pos"][ud] += 1
    return out


def concentration_level(level_counter):
    """The level a lemma appears at MOST; ties break to the lower level."""
    return min(level_counter.items(), key=lambda kv: (-kv[1], LEVEL_IDX[kv[0]]))[0]


def first_occurrence_level(level_counter):
    """The lowest CEFR course level that introduces the lemma."""
    return min(level_counter.keys(), key=lambda l: LEVEL_IDX[l])


# Empirical note: concentration_level was evaluated against the gold standard and
# does NOT beat first-occurrence. On the expanded n=114 gold set it is clearly
# worse (52.6% vs 63.2% exact, a gap outside the +/-9pp interval; it was a wash at
# n=35). It moves words toward their frequency-natural level, which is often
# FURTHER from Synchak's deliberate beginner-priority overrides (furniture at A1),
# not closer. We keep the simpler first-occurrence rule and let gold-override
# carry the validated corrections.
ASSIGN_LEVEL = first_occurrence_level


def join_rows(course_root, seed):
    seed_by_key = {}
    for i, r in enumerate(seed["rows"]):
        key = r["lemma"].lower()
        if key not in seed_by_key:
            seed_by_key[key] = {"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"]}
    course = extract_course(course_root)
    rows = []
    dropped_pos = 0
    for key, rec in course.items():
        hit = seed_by_key.get(key)
        if not hit:
            continue
        course_ud = rec["pos"].most_common(1)[0][0] if rec["pos"] else None
        if course_ud and family(course_ud) and family(hit["pos"]) and family(course_ud) != family(hit["pos"]):
            dropped_pos += 1  # homograph: same spelling, different part of speech
            continue
        lvl = ASSIGN_LEVEL(rec["levels"])
        # heuristicLevel is the immutable course level; `level` is what we deliver
        # (it may be overridden to a validated level later). Agreement is always
        # measured against heuristicLevel so re-running enrich cannot inflate it.
        rows.append({"rank": hit["rank"], "lemma": hit["lemma"], "pos": hit["pos"], "heuristicLevel": lvl, "level": lvl})
    rows.sort(key=lambda r: r["rank"])
    return rows, dropped_pos


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


def _quartile(sorted_nums, q):
    n = len(sorted_nums)
    pos = q * (n - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < n:
        return sorted_nums[lo] + frac * (sorted_nums[lo + 1] - sorted_nums[lo])
    return sorted_nums[lo]


def enrich(rows, gold, seed, dropped_pos):
    """Grade the join: gold agreement BEFORE override, then override + tier + coherence."""
    gold_by_key = {}
    for p in gold["points"]:
        gold_by_key[p["lemma"].lower()] = p
    overlay_by_key = {r["lemma"].lower(): r for r in rows}
    seed_keys = {r["lemma"].lower() for r in seed["rows"]}

    # (a) HEURISTIC agreement, measured on the concentration join BEFORE any override.
    gold_rows = []
    for p in gold["points"]:
        r = overlay_by_key.get(p["lemma"].lower())
        if not r:
            continue
        if family(p["pos"]) and family(r["pos"]) and family(p["pos"]) != family(r["pos"]):
            continue  # POS-aware: different sense, not a fair comparison
        delta = LEVEL_IDX[r["heuristicLevel"]] - LEVEL_IDX[p["level"]]
        gold_rows.append({
            "lemma": r["lemma"], "rank": r["rank"], "pos": r["pos"], "gold": p["level"],
            "overlay": r["heuristicLevel"], "exact": delta == 0, "delta": delta, "ref": p["ref"],
        })
    gold_rows.sort(key=lambda r: r["rank"])
    n = len(gold_rows)
    exact = sum(1 for r in gold_rows if r["exact"])
    within1 = sum(1 for r in gold_rows if abs(r["delta"]) <= 1)
    exact_pct = round(exact / n * 1000) / 10 if n else 0
    p_hat = exact / n if n else 0
    ci_half = round(1.96 * math.sqrt(p_hat * (1 - p_hat) / n) * 1000) / 10 if n else 0  # percentage points

    # (b) GOLD-OVERRIDE delivery: matched gold lemmas take the validated level.
    overridden = 0
    for gr in gold_rows:
        r = overlay_by_key[gr["lemma"].lower()]
        r["level"] = gr["gold"]
        r["validated"] = True
        overridden += 1

    # (c) CONFIDENCE tiers, on the delivered levels. Validated wins; the rest are
    #     graded frequency-typical or outlier by a Tukey fence on each level's ranks.
    levels_present = [lvl.upper() for lvl in LEVELS if any(r["level"] == lvl.upper() for r in rows)]
    fences = {}
    for lvl in levels_present:
        ranks = sorted(r["rank"] for r in rows if r["level"] == lvl)
        q1 = _quartile(ranks, 0.25)
        q3 = _quartile(ranks, 0.75)
        iqr = q3 - q1
        fences[lvl] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    for r in rows:
        if r.get("validated"):
            r["confidence"] = "validated"
        else:
            lo, hi = fences[r["level"]]
            r["confidence"] = "typical" if lo <= r["rank"] <= hi else "frequency-outlier"
    tier_counts = {}
    for r in rows:
        tier_counts[r["confidence"]] = tier_counts.get(r["confidence"], 0) + 1

    # (d) coherence on delivered levels. Median rank is reported only for levels
    # with a meaningful sample (>= 5 lemmas): a single high-level outlier (a
    # frequency-common but pedagogically advanced word like заявити at C1) cannot
    # establish a trend, and would otherwise distort the median-by-level display.
    # Spearman uses every labeled row.
    COHERENCE_MIN_N = 5
    median_rank = {}
    for lvl in levels_present:
        lvl_ranks = [r["rank"] for r in rows if r["level"] == lvl]
        if len(lvl_ranks) >= COHERENCE_MIN_N:
            median_rank[lvl] = int(_median(lvl_ranks))
    xs = [LEVEL_IDX[r["level"]] for r in rows]
    ys = [r["rank"] for r in rows]
    spearman = round(_pearson(_rankdata(xs), _rankdata(ys)) * 1000) / 1000

    gold_summary = {
        "nGold": len(gold["points"]),
        "nInList": sum(1 for pt in gold["points"] if pt["lemma"].lower() in seed_keys),
        "nLabeled": n,
        "exact": exact,
        "within1": within1,
        "exactPct": exact_pct,
        "within1Pct": round(within1 / n * 1000) / 10 if n else 0,
        "ciHalfPct": ci_half,
        "measuredBeforeOverride": True,
        "overridden": overridden,
        "droppedHomographs": dropped_pos,
    }
    return {
        "levelsPresent": levels_present,
        "tierCounts": tier_counts,
        "gold": {"source": gold["source"], "summary": gold_summary, "rows": gold_rows},
        "coherence": {"medianRankByLevel": median_rank, "spearman": spearman},
    }


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    ap.add_argument("--learn-ukrainian", default=None, help="path to a learn-ukrainian.github.io clone (stage 1); omit to re-grade the committed join")
    ap.add_argument("--repo-root", default=repo_root)
    args = ap.parse_args()

    data_dir = os.path.join(args.repo_root, "src", "data", "ukrainian-frequency")
    seed = json.load(open(os.path.join(data_dir, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    gold = json.load(open(os.path.join(data_dir, "cefr-gold.json"), encoding="utf-8"))

    if args.learn_ukrainian:
        rows, dropped_pos = join_rows(args.learn_ukrainian, seed)
    else:
        prev = json.load(open(os.path.join(data_dir, "cefr-overlay.json"), encoding="utf-8"))
        # Re-key the committed join onto the current seed by lemma and part of
        # speech, the join's own key, so a list refresh (v0.1.0 -> v0.2.0) moves
        # every row to its new rank without the course clone and keeps the dated
        # course snapshot as it was. A row whose lemma left the list is dropped.
        seed_by_key = {}
        for i, r in enumerate(seed["rows"]):
            seed_by_key.setdefault((r["lemma"].lower(), r["pos"]), {"rank": i + 1, "lemma": r["lemma"]})
        rows = []
        left_list = 0
        for r in prev["rows"]:
            hit = seed_by_key.get((r["lemma"].lower(), r["pos"]))
            if hit is None:
                left_list += 1
                continue
            # Reset `level` to the immutable heuristic on load, so a prior
            # override in the committed file cannot leak into the agreement
            # measurement.
            rows.append({"rank": hit["rank"], "lemma": hit["lemma"], "pos": r["pos"],
                         "heuristicLevel": r.get("heuristicLevel", r["level"]),
                         "level": r.get("heuristicLevel", r["level"])})
        rows.sort(key=lambda r: r["rank"])
        if left_list:
            print(f"re-keyed the committed join onto the current seed: {left_list} row(s) whose lemma left the list dropped")
        dropped_pos = prev.get("gold", {}).get("summary", {}).get("droppedHomographs", 0)

    enr = enrich(rows, gold, seed, dropped_pos)

    per_level = {}
    per_band = {}
    for r in rows:
        per_level[r["level"]] = per_level.get(r["level"], 0) + 1
        band = (r["rank"] - 1) // 1000 + 1
        per_band[band] = per_band.get(band, 0) + 1
    labeled_in_top_n = {n: sum(1 for r in rows if r["rank"] <= n) for n in CHECKPOINTS}
    levels_present = enr["levelsPresent"]

    sample = []
    for lvl in levels_present:
        sample.extend([r for r in rows if r["level"] == lvl][:SAMPLE_PER_LEVEL])
    sample.sort(key=lambda r: r["rank"])

    meta = {
        "source": "learn-ukrainian (Krisztian Koos)",
        "sourceUrl": "https://github.com/learn-ukrainian/learn-ukrainian.github.io",
        "license": "CC-BY-SA-4.0",
        "basis": "Ukraine State Standard for Ukrainian as a Foreign Language (2024)",
        "method": "first-occurrence: a lemma's level is the lowest CEFR course level that introduces it; POS-aware join (homographs dropped); validated levels overridden from Synchak et al. where published",
        "validated": False,
        "listSize": len(seed["rows"]),
        "count": len(rows),
        "coveragePct": round(len(rows) / len(seed["rows"]) * 1000) / 10,
        "levelsPresent": levels_present,
        "perLevel": {lvl: per_level[lvl] for lvl in levels_present},
        "perBand": {str(b): per_band.get(b, 0) for b in range(1, 13)},
        "labeledInTopN": {str(n): labeled_in_top_n[n] for n in CHECKPOINTS},
        "tierCounts": enr["tierCounts"],
        "gold": enr["gold"],
        "coherence": enr["coherence"],
        "download": "/downloads/ukrainian-frequency/cefr-overlay/lemmas.csv",
    }

    full = dict(meta)
    full["rows"] = rows
    with open(os.path.join(data_dir, "cefr-overlay.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    dl_dir = os.path.join(args.repo_root, "public", "downloads", "ukrainian-frequency", "cefr-overlay")
    os.makedirs(dl_dir, exist_ok=True)
    with open(os.path.join(dl_dir, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,heuristic_level,level,confidence\n")
        for r in rows:
            fh.write(f"{r['rank']},{r['lemma']},{r['pos']},{r['heuristicLevel']},{r['level']},{r['confidence']}\n")

    lib_dir = os.path.join(args.repo_root, "src", "lib", "ukrainian-frequency")
    slim = {**meta, "sample": [dict(r) for r in sample]}
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-cefr-overlay.py - do not edit by hand.\n"
        "// Browser-safe tier of the EXPERIMENTAL CEFR overlay (thread 02): aggregates,\n"
        "// the gold-standard agreement check (measured on the heuristic before override),\n"
        "// the level-vs-frequency coherence stat, and a small sample. The full per-lemma\n"
        "// table is the committed src/data/ukrainian-frequency/cefr-overlay.json and the\n"
        "// public CSV. UNVALIDATED overall: see cefr-overlay.SOURCE.md and the page fencing.\n"
        "export const CEFR_OVERLAY = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(lib_dir, "cefr-overlay.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    g = meta["gold"]["summary"]
    print(f"overlay rows: {len(rows)} ({meta['coveragePct']}%); dropped homographs (POS): {dropped_pos}")
    print(f"tiers: {meta['tierCounts']}")
    print(f"HEURISTIC gold agreement (pre-override): {g['exact']}/{g['nLabeled']} exact = {g['exactPct']}% +/- {g['ciHalfPct']}pp, within-one {g['within1Pct']}%")
    print(f"gold-override delivered: {g['overridden']} labels set to validated")
    print(f"coherence: spearman={meta['coherence']['spearman']}, median rank by level={meta['coherence']['medianRankByLevel']}")


if __name__ == "__main__":
    main()
