#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : thread 03, the derussification pass (extractor)
#
# Joins the thread-01 frequency list against the OPEN Ukrainian idiomatic-style
# tooling (LanguageTool's Ukrainian replacement tables, maintained by brown-uk /
# Andriy Rysin) and records, for every top-12,000 lemma the tooling flags, the
# native alternative it recommends. This is the open Pravopysnyk-style layer the
# thread names; VESUM (brown-uk/dict_uk) is the morphology behind the same
# project.
#
# This is NOT run in the build or CI (it needs the LanguageTool resource files,
# which are not vendored). It is documented and reproducible: it writes three
# artifacts, and CI re-verifies THEM against each other and against the seed
# (press/src/components/study/__tests__/derussification.test.js), never
# against this script's inputs. Same posture as extract-cefr-overlay.py.
#
# Honesty, front and center (surfaced on the page too):
#  - This flags forms the OPEN STYLE TOOLING would replace with a more idiomatic
#    Ukrainian one. That set is the derussification core (russianisms, surzhyk,
#    active-participle and other calques) but is broader than strictly-Russian
#    borrowings and reflects a prescriptive editorial opinion, not a settled
#    verdict. It is unvalidated in exactly the sense thread 02's overlay is.
#  - Proper-noun / orthographic normalizations (PROPN rows) are dropped: they are
#    not the "learn the idiomatic word" target.
#  - Every suggestion is the tooling's own, verbatim. Nothing is invented.
#
# Reproduce:
#   base=languagetool-language-modules/uk/src/main/resources/org/languagetool/rules/uk
#   git clone --depth 1 https://github.com/languagetool-org/languagetool.git /tmp/lt
#   python3 scripts/ukrainian-frequency/extract-derussification.py \
#     --replace   /tmp/lt/$base/replace.txt \
#     --replace-soft /tmp/lt/$base/replace_soft.txt
#
# House rule: no em-dashes.
# ============================================================
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SEED = os.path.join(ROOT, "src", "data", "ukrainian-frequency", "ubertext-lemmas-top12k.json")
OUT_JSON = os.path.join(ROOT, "src", "data", "ukrainian-frequency", "derussification.json")
OUT_DATA = os.path.join(ROOT, "src", "lib", "ukrainian-frequency", "derussification.data.mjs")
OUT_CSV_DIR = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "derussification")

SOURCE_URL = (
    "https://github.com/languagetool-org/languagetool/tree/master/"
    "languagetool-language-modules/uk/src/main/resources/org/languagetool/rules/uk"
)
LICENSE = "LGPL-2.1"

# The active-present-participle calque class: -ючий/-уючий/-аючий/-ячий adjectives
# that the tooling rewrites as a relative clause ("що " + verb). A well-known,
# mechanically-detectable russianism pattern (standard Ukrainian has no productive
# active present participle). Detected by suffix AND the tooling's own rewrite.
PARTICIPLE_SUFFIXES = ("ючий", "уючий", "аючий", "ячий", "лючий")


def parse_replace(path):
    table = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            sugg = [s.strip() for s in val.split("|") if s.strip()]
            if key and sugg and key not in table:
                table[key] = sugg
    return table


def is_clean_swap(s):
    # A single-token suggestion (no space, parenthetical, or list) is a clean
    # lemma-for-lemma swap; anything else is a construction to learn ("phrase").
    return (" " not in s) and ("(" not in s) and ("," not in s) and (";" not in s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", required=True, help="path to LanguageTool uk replace.txt")
    ap.add_argument("--replace-soft", required=True, help="path to LanguageTool uk replace_soft.txt")
    args = ap.parse_args()

    hard = parse_replace(args.replace)
    soft = parse_replace(args.replace_soft)

    seed = json.load(open(SEED, encoding="utf-8"))
    rows = seed["rows"]
    list_size = len(rows)
    # lowest rank a lemma-string appears at (for "is the native form on the list?")
    lemma_rank = {}
    for i, r in enumerate(rows):
        lemma_rank.setdefault(r["lemma"], i + 1)

    out_rows = []
    seen = set()
    for i, r in enumerate(rows):
        lemma, pos, rank = r["lemma"], r["pos"], i + 1
        if pos == "PROPN":  # orthographic normalizations, not derussification content
            continue
        tier = suggestions = None
        if lemma in hard:
            tier, suggestions = "hard", hard[lemma]
        elif lemma in soft:
            tier, suggestions = "soft", soft[lemma]
        else:
            continue
        key = (lemma, pos)
        if key in seen:
            continue
        seen.add(key)

        primary = suggestions[0]
        clean = is_clean_swap(primary)
        alt_rank = lemma_rank.get(primary) if clean else None
        if not clean:
            swap = "phrase"
        elif alt_rank is None:
            swap = "off-list"
        elif alt_rank > rank:
            swap = "rarer"
        else:
            swap = "commoner"

        participle = (
            pos == "ADJ"
            and lemma.endswith(PARTICIPLE_SUFFIXES)
            and primary.startswith("що ")
        )
        out_rows.append(
            {
                "rank": rank,
                "lemma": lemma,
                "pos": pos,
                "tier": tier,
                "suggestion": primary,
                "suggestions": suggestions,
                "swap": swap,
                "altRank": alt_rank,
                "participle": participle,
            }
        )

    out_rows.sort(key=lambda x: x["rank"])
    count = len(out_rows)

    # ---- aggregates for the browser tier ----
    tier_counts = {"hard": 0, "soft": 0}
    pos_counts = {}
    per_band = {}
    swap_counts = {"rarer": 0, "commoner": 0, "off-list": 0, "phrase": 0}
    participle_count = 0
    for r in out_rows:
        tier_counts[r["tier"]] += 1
        pos_counts[r["pos"]] = pos_counts.get(r["pos"], 0) + 1
        band = (r["rank"] - 1) // 1000 + 1
        per_band[band] = per_band.get(band, 0) + 1
        swap_counts[r["swap"]] += 1
        if r["participle"]:
            participle_count += 1

    clean_swaps = swap_counts["rarer"] + swap_counts["commoner"] + swap_counts["off-list"]
    alt_on_list = swap_counts["rarer"] + swap_counts["commoner"]
    # The measured finding: among clean single-word swaps, how often the flagged
    # form is at least as common as its native replacement (native rarer or absent).
    native_rarer_or_absent = swap_counts["rarer"] + swap_counts["off-list"]
    native_rarer_or_absent_pct = round(native_rarer_or_absent / clean_swaps * 1000) / 10

    flagged_in_top_n = {}
    for n in (1000, 2000, 5000, 12000):
        flagged_in_top_n[str(n)] = sum(1 for r in out_rows if r["rank"] <= n)

    # Deterministic sample: the lowest-rank flagged lemma in each populated band,
    # so the sample spans the whole list and never depends on ordering luck.
    sample_by_band = {}
    for r in out_rows:
        band = (r["rank"] - 1) // 1000 + 1
        if band not in sample_by_band:
            sample_by_band[band] = {
                "rank": r["rank"],
                "lemma": r["lemma"],
                "pos": r["pos"],
                "tier": r["tier"],
                "suggestion": r["suggestion"],
                "swap": r["swap"],
                "altRank": r["altRank"],
            }
    sample = [sample_by_band[b] for b in sorted(sample_by_band)]

    coverage_pct = round(count / list_size * 1000) / 10

    full = {
        "generator": "scripts/ukrainian-frequency/extract-derussification.py",
        "generatedNote": (
            "Thread 03, the derussification pass. Top-12,000 lemmas the open "
            "LanguageTool Ukrainian style tooling flags, each with the native "
            "alternative it recommends. Unvalidated (a prescriptive editorial "
            "signal), CC/LGPL source, proper nouns dropped. Not run in CI."
        ),
        "source": "languagetool_uk",
        "sourceLabel": "LanguageTool Ukrainian replacement tables (brown-uk)",
        "sourceUrl": SOURCE_URL,
        "license": LICENSE,
        "validated": False,
        "listSize": list_size,
        "count": count,
        "coveragePct": coverage_pct,
        "tierCounts": tier_counts,
        "posCounts": pos_counts,
        "perBand": {str(k): per_band[k] for k in sorted(per_band)},
        "swapCounts": swap_counts,
        "cleanSwaps": clean_swaps,
        "altOnList": alt_on_list,
        "participleCount": participle_count,
        "finding": {
            "cleanSwaps": clean_swaps,
            "nativeRarerOrAbsent": native_rarer_or_absent,
            "nativeRarerOrAbsentPct": native_rarer_or_absent_pct,
        },
        "flaggedInTopN": flagged_in_top_n,
        "rows": out_rows,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ---- generated browser tier ----
    browser = {
        "source": full["sourceLabel"],
        "sourceUrl": SOURCE_URL,
        "license": LICENSE,
        "method": (
            "join the frequency list against LanguageTool's Ukrainian replacement "
            "tables (replace.txt = hard, replace_soft.txt = soft); keep the "
            "tooling's recommended native form verbatim; drop proper-noun "
            "orthographic fixes; classify the rank movement of each single-word swap"
        ),
        "validated": False,
        "listSize": list_size,
        "count": count,
        "coveragePct": coverage_pct,
        "tierCounts": tier_counts,
        "posCounts": pos_counts,
        "perBand": {str(k): per_band[k] for k in sorted(per_band)},
        "swapCounts": swap_counts,
        "cleanSwaps": clean_swaps,
        "altOnList": alt_on_list,
        "participleCount": participle_count,
        "finding": full["finding"],
        "flaggedInTopN": flagged_in_top_n,
        "sample": sample,
        "download": "/downloads/ukrainian-frequency/derussification/lemmas.csv",
    }
    header = (
        "// GENERATED by scripts/ukrainian-frequency/extract-derussification.py - do not edit by hand.\n"
        "// Browser-safe tier of the derussification pass (thread 03): aggregates, the\n"
        "// swap-direction finding, and a small sample. The full per-lemma table is the\n"
        "// committed src/data/ukrainian-frequency/derussification.json and the public\n"
        "// CSV. UNVALIDATED: a prescriptive open-tooling signal, see derussification.SOURCE.md.\n"
    )
    with open(OUT_DATA, "w", encoding="utf-8") as fh:
        fh.write(header)
        fh.write("export const DERUSSIFICATION = " + json.dumps(browser, ensure_ascii=False, indent=2) + ";\n")

    # ---- public CSV download ----
    os.makedirs(OUT_CSV_DIR, exist_ok=True)
    with open(os.path.join(OUT_CSV_DIR, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,tier,suggestion,swap\n")
        for r in out_rows:
            fh.write(f"{r['rank']},{r['lemma']},{r['pos']},{r['tier']},{r['suggestion']},{r['swap']}\n")

    print(f"wrote {count} flagged lemmas")
    print(f"  tiers: {tier_counts}")
    print(f"  swaps: {swap_counts}")
    print(f"  clean single-word swaps: {clean_swaps}; native rarer-or-absent: "
          f"{native_rarer_or_absent} ({native_rarer_or_absent_pct}%)")
    print(f"  active-participle calques: {participle_count}")
    print(f"  per band: {full['perBand']}")


if __name__ == "__main__":
    main()
