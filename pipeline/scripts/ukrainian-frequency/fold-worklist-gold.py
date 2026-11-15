#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02 / Plan B2: fold the filled worklist into gold.
#
# Reads the PULS-filled docs/ukrainian-frequency/cefr-gold-worklist.csv and adds
# each confirmed single-level lemma to src/data/ukrainian-frequency/cefr-gold.json
# as a new gold point with ref "PULS". Skips rows with puls_level "none" (not in
# PULS) and rows flagged with a multi-level value like "A2|B1" (a homograph we
# will not disambiguate blindly). POS is our seed UD tag, so POS-aware gold
# matching still works. Idempotent: a lemma already in the gold set is skipped.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import csv
import json
import os

VALID = {"A1", "A2", "B1", "B2", "C1", "C2"}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    data_dir = os.path.join(repo_root, "src", "data", "ukrainian-frequency")
    gold_path = os.path.join(data_dir, "cefr-gold.json")
    wl_path = os.path.join(repo_root, "docs", "ukrainian-frequency", "cefr-gold-worklist.csv")

    gold = json.load(open(gold_path, encoding="utf-8"))
    # Keyed by (lemma, pos): gold matching is POS-aware, so a different sense of a
    # lemma already in gold is not wrongly skipped, and re-folding stays idempotent.
    existing = {(p["lemma"].lower(), p["pos"]) for p in gold["points"]}

    with open(wl_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    added = skipped_none = skipped_multi = 0
    for r in rows:
        lvl = (r.get("puls_level") or "").strip()
        key = (r["lemma"].lower(), r["pos"])
        if key in existing:
            continue
        if lvl == "none" or lvl == "":
            skipped_none += 1
            continue
        if lvl not in VALID:  # e.g. "A2|B1" multi-sense
            skipped_multi += 1
            continue
        gold["points"].append({"lemma": r["lemma"], "pos": r["pos"], "level": lvl, "ref": "PULS"})
        existing.add(key)
        added += 1

    gold["note"] = (
        "Per-lemma CEFR level assignments from Synchak, Starko, Burak and Svystun "
        "(eLex 2025) and the PULS platform they published (puls.peremova.org). "
        "Points with a ref of Table N or Section N are transcribed verbatim from "
        "the paper; points with ref PULS were looked up individually on the public "
        "PULS entries interface (an exact-headword match, one lookup per lemma, its "
        "own robots.txt permitting /entries). pos is the sense's part of speech (UD "
        "tag) so gold matching is POS-aware. This is the closest thing to a "
        "validated gold standard for Ukrainian CEFR vocabulary; the experimental "
        "overlay is measured against it. Levels above what a source states are "
        "never inferred, and homographs listed at more than one PULS level are "
        "excluded rather than guessed."
    )

    with open(gold_path, "w", encoding="utf-8") as fh:
        json.dump(gold, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    puls = sum(1 for p in gold["points"] if p.get("ref") == "PULS")
    print(f"added {added} PULS points; skipped {skipped_none} none, {skipped_multi} multi-sense")
    print(f"gold set now {len(gold['points'])} points ({puls} from PULS, {len(gold['points']) - puls} from the paper)")


if __name__ == "__main__":
    main()
