#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02 / Plan B2: the gold-expansion worklist.
#
# The overlay's agreement with the validated gold standard is measured on only
# the ~35 lemmas that both (a) Synchak et al. print a level for and (b) appear in
# our list. To tighten that estimate (a wider n shrinks the +/-16pp interval) and
# to expand the `validated` override coverage, we need more per-lemma validated
# levels. The one place to get them is the PULS platform (puls.peremova.org),
# which is public but browse-only, so this is a HUMAN-in-the-loop task: this
# script emits a prioritized worklist of the highest-frequency lemmas we do NOT
# already have a gold level for; a person looks each up on PULS and records the
# published level. Then re-run the extractor's enrich stage with the expanded
# gold set. We do not bulk-scrape PULS; we look up specific cited entries.
#
# Output: docs/ukrainian-frequency/cefr-gold-worklist.csv (rank, lemma, pos,
# in_overlay, overlay_level, overlay_confidence, puls_level [blank], notes [blank]).
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import argparse
import json
import os

TOP_N = 150


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    ap.add_argument("--repo-root", default=repo_root)
    ap.add_argument("--n", type=int, default=TOP_N)
    args = ap.parse_args()

    data_dir = os.path.join(args.repo_root, "src", "data", "ukrainian-frequency")
    seed = json.load(open(os.path.join(data_dir, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    gold = json.load(open(os.path.join(data_dir, "cefr-gold.json"), encoding="utf-8"))
    overlay = json.load(open(os.path.join(data_dir, "cefr-overlay.json"), encoding="utf-8"))

    # Keyed by (lemma, pos): gold matching is POS-aware, so a different sense of a
    # lemma already in gold still deserves a worklist row.
    gold_keys = {(p["lemma"].lower(), p["pos"]) for p in gold["points"]}
    overlay_by_key = {(r["lemma"].lower(), r["pos"]): r for r in overlay["rows"]}

    rows = []
    for i, r in enumerate(seed["rows"]):
        rank = i + 1
        key = (r["lemma"].lower(), r["pos"])
        if key in gold_keys:
            continue  # already have a validated level for this lemma+pos
        # skip proper nouns and sub-3-letter tokens: rarely on PULS, low value
        if r["pos"] == "PROPN" or len(r["lemma"]) < 3:
            continue
        ov = overlay_by_key.get(key)
        rows.append({
            "rank": rank,
            "lemma": r["lemma"],
            "pos": r["pos"],
            "in_overlay": "yes" if ov else "no",
            "overlay_level": ov["level"] if ov else "",
            "overlay_confidence": ov["confidence"] if ov else "",
        })
        if len(rows) >= args.n:
            break

    out_dir = os.path.join(args.repo_root, "docs", "ukrainian-frequency")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "cefr-gold-worklist.csv")
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,in_overlay,overlay_level,overlay_confidence,puls_level,notes\n")
        for r in rows:
            fh.write(f"{r['rank']},{r['lemma']},{r['pos']},{r['in_overlay']},{r['overlay_level']},{r['overlay_confidence']},,\n")

    in_overlay = sum(1 for r in rows if r["in_overlay"] == "yes")
    print(f"wrote {len(rows)} rows to docs/ukrainian-frequency/cefr-gold-worklist.csv")
    print(f"  {in_overlay} are already in the overlay (looking these up tightens the agreement estimate)")
    print(f"  {len(rows) - in_overlay} are not (looking these up expands validated coverage)")
    print(f"  frequency range: rank {rows[0]['rank']} to {rows[-1]['rank']}")


if __name__ == "__main__":
    main()
