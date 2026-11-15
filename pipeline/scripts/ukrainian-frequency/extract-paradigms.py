#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : thread 04, audio and paradigms (extractor)
#
# Joins the thread-01 frequency list against the open, machine-readable
# Wiktionary extraction (kaikki.org / wiktextract) and attaches, to each of the
# top-12,000 lemmas, its inflection paradigm (the declension / conjugation forms,
# stress-marked), its IPA, and a link to open native-speaker pronunciation audio
# on Wikimedia Commons. This is the source the thread names: open Wiktionary
# declension and conjugation tables plus open pronunciation audio.
#
# This is NOT run in the build or CI (it needs the ~255 MB kaikki Ukrainian dump,
# which is not vendored). It is documented and reproducible: it writes three
# artifacts, and CI re-verifies THEM against each other and against the seed
# (press/src/components/study/__tests__/paradigms.test.js), never
# against the dump. Same posture as extract-cefr-overlay.py / extract-derussification.py.
#
# Honesty (surfaced on the page):
#  - Coverage is graded, not assumed: Wiktionary does not have every lemma, and
#    the page reports the real percentages (paradigm / IPA / audio).
#  - Forms are Wiktionary's own, kept verbatim (stress marks included). Romanized
#    forms, placeholders ("-"), and template rows are dropped; nothing is generated.
#  - Audio is LINKED to Wikimedia Commons (CC BY-SA), never re-hosted.
#  - The measured finding (the inflection multiplier) is a fact about the data, a
#    morphology-level companion to thread 01's coverage curve.
#
# Reproduce (stream, no giant file on disk). The dump is served only in its
# current edition, so a re-run always picks up whatever kaikki publishes that
# day; --dump-date records which one, the same contract the sibling family
# extractor uses, so drift between runs is legible instead of silent:
#   curl -sSI https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl   # read Last-Modified
#   curl -sS https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl \
#     | python3 scripts/ukrainian-frequency/extract-paradigms.py --stdin --dump-date 2026-09-09
#
# Or recompute from the committed release with no dump (the stamping rule and
# every derived figure; the chosen entries are read back from the two CSVs):
#   python3 scripts/ukrainian-frequency/extract-paradigms.py --rebuild
#
# House rule: no em-dashes.
# ============================================================
import argparse
import gzip
import json
import math
import os
import re
import sys


def r1(x):
    # round half UP to one decimal, matching JS Math.round (Python's round() is
    # banker's rounding, which would disagree with the browser + the test recompute)
    return math.floor(x * 10 + 0.5) / 10

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SEED = os.path.join(ROOT, "src", "data", "ukrainian-frequency", "ubertext-lemmas-top12k.json")
OUT_DATA = os.path.join(ROOT, "src", "lib", "ukrainian-frequency", "paradigms.data.mjs")
# The two public CSVs double as the committed full record (an open-data release),
# so we do NOT also commit a multi-MB derived JSON that would just duplicate them.
OUT_DIR = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "paradigms")

TOP_N = 12000  # the release covers the whole thread-01 list (coverage graded, thins with rank)
SOURCE_URL = "https://kaikki.org/dictionary/Ukrainian/"
DUMP_URL = "https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl"
LICENSE = "CC-BY-SA-3.0"  # Wiktionary text; Wikimedia audio is CC-BY-SA too

POSMAP = {
    "noun": "NOUN", "verb": "VERB", "adj": "ADJ", "adv": "ADV", "pron": "PRON",
    "num": "NUM", "prep": "ADP", "conj": "CCONJ", "particle": "PART", "det": "DET",
    "name": "PROPN", "intj": "INTJ", "article": "DET", "postp": "ADP",
}
# part-of-speech families, so the join tolerates the UD/Wiktionary POS split
FAM = {
    "NOUN": "noun", "PROPN": "noun", "VERB": "verb", "ADJ": "adj", "DET": "adj",
    "ADV": "adv", "NUM": "num", "PRON": "pron", "PART": "part", "ADP": "adp",
    "CCONJ": "conj", "SCONJ": "conj", "INTJ": "intj",
}

# Tags that mark a row as NOT an inflected wordform (drop it outright).
NON_FORM_TAGS = {"romanization", "canonical", "table-tags", "inflection-template", "class",
                 "error-unknown-tag", "multiword-construction"}
# Inflectional feature tags we recognize (a form counts toward the paradigm only
# if it carries at least one of these). Derivational spin-offs (a relational
# adjective built off a noun, a diminutive) are kept in the table but NOT counted
# as inflection, so the multiplier measures declension/conjugation, not derivation.
CASE_TAGS = {"nominative", "genitive", "dative", "accusative", "instrumental", "locative", "vocative"}
VERB_TAGS = {"infinitive", "imperative", "first-person", "second-person", "third-person",
             "present", "past", "future", "active", "passive", "adverbial"}
INFLECT_TAGS = CASE_TAGS | VERB_TAGS | {"comparative", "superlative"}
DERIV_TAGS = {"adjective", "adverb", "relational", "diminutive", "augmentative",
              "abstract-noun", "pejorative", "endearing", "possessive-noun"}

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# Ukrainian writes the apostrophe with several glyphs and the two sides of this
# join disagree: the frequency list uses U+2019 while Wiktionary headwords use
# the modifier letter U+02BC or a plain ASCII quote. Keyed verbatim, the join
# silently missed every apostrophe lemma on the list (156 of 158: зв'язок, ім'я,
# здоров'я, з'явитися, сім'я, п'ять). Fold the glyph for the JOIN KEY ONLY; the
# emitted lemma stays the list's own string and the forms stay Wiktionary's own,
# verbatim, which is the thread's standing rule. The validated-CEFR join needed
# the same class of fix in 2026-09 (it folds three glyphs, after decoding the
# HTML entity PULS serves); this set is wider because a dump can carry any of
# them. See puls-cefr.SOURCE.md.
APOSTROPHES = re.compile(r"[\u0027\u02bc\u02b9\u0060\u00b4\u2018\u2032]")


def apos_key(s):
    return APOSTROPHES.sub("\u2019", s)


def is_cyrillic(s):
    # a real Ukrainian form is written in Cyrillic; romanizations that slipped the
    # tag filter (Latin letters) and bare placeholders are excluded
    return bool(s) and s != "-" and bool(CYRILLIC.search(s)) and not re.search(r"[a-zA-Z]", s)


def clean_forms(rec):
    seen = set()
    forms = []
    for f in rec.get("forms") or []:
        tags = f.get("tags") or []
        if not tags or any(t in NON_FORM_TAGS for t in tags):
            continue
        form = f.get("form")
        if not is_cyrillic(form):
            continue
        # order-independent identity: same string + same tag set is one form
        key = (form, tuple(sorted(tags)))
        if key in seen:
            continue
        seen.add(key)
        inflectional = any(t in INFLECT_TAGS for t in tags) and not (
            set(tags) & DERIV_TAGS and not (set(tags) & (CASE_TAGS | VERB_TAGS))
        )
        forms.append({"form": form, "tags": tags, "infl": inflectional})
    return forms


def stamp(meta, pos):
    """The list row a chosen Wiktionary entry belongs to.

    A spelling can sit on the list more than once (ніж is the conjunction at rank
    222 and the noun at 3855). The entry is chosen per spelling, preferring one
    whose part-of-speech family the list has, so it must be stamped with the rank
    and spelling of the list row of THAT family, not the spelling's best rank.
    Stamping the best rank handed the conjunction the noun's declension, and the
    profiler, which maps forms through this file, then read ножем as "than".
    Where no list row shares the entry's family (a participle Wiktionary files as
    a verb, a determiner it files as a pronoun), the best rank stands, as before.
    """
    fam = FAM.get(pos)
    same = [r for r in meta["rows"] if FAM.get(r["pos"]) == fam]
    best = min(same or meta["rows"], key=lambda r: r["rank"])
    return best["rank"], best["lemma"]


def entry_of(rec, forms):
    ipa = None
    audio = None
    for s in rec.get("sounds") or []:
        if ipa is None and s.get("ipa"):
            ipa = s["ipa"]
        if audio is None and s.get("audio"):
            audio = s.get("mp3_url") or s.get("ogg_url")
    return {
        "pos": POSMAP.get(rec.get("pos"), (rec.get("pos") or "").upper()),
        "ipa": ipa,
        "audio": audio,
        "forms": [{"form": f["form"], "tags": f["tags"], "infl": f["infl"]} for f in forms],
    }


def chosen_from_dump(stream, top):
    """Pick Wiktionary entries per spelling: one per part-of-speech family the
    list holds that spelling in, so лютий is declined once as the month (the
    NOUN at 271) and once as "fierce" (the ADJ at 4502), and the profiler can
    map лютого to both, most frequent first. A family with no Wiktionary entry
    gets none. A spelling none of whose families Wiktionary has falls back to
    its richest entry of any part of speech, stamped on the best rank.
    """
    by_word = {}
    for line in stream:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        w = d.get("word")
        if not w:
            continue
        key = apos_key(w)
        if key in top:
            by_word.setdefault(key, []).append(d)

    chosen = {}
    for key, meta in top.items():
        recs = by_word.get(key, [])
        best = {}  # family -> (rec, forms, score); the entry with the most inflected forms
        for rec in recs:
            rfam = FAM.get(POSMAP.get(rec.get("pos")), None)
            forms = clean_forms(rec)
            score = sum(1 for f in forms if f["infl"])
            if rfam not in best or score > best[rfam][2]:
                best[rfam] = (rec, forms, score)
        picked = [best[f] for f in sorted(meta["fams"], key=str) if f in best]
        if not picked and best:
            picked = [max(best.values(), key=lambda x: x[2])]
        if picked:
            chosen[key] = [entry_of(rec, forms) for rec, forms, _ in picked]
    return chosen


def chosen_from_published():
    """Read the chosen entries back out of the committed release.

    lemmas.csv + forms.csv.gz record everything the dump pass decided per
    spelling (the entry's POS, IPA, audio link, and every kept form with its tags
    and inflectional flag), so the stamping and every derived figure can be
    recomputed without re-downloading a dump that kaikki serves only in its
    current edition. The drift contract: --rebuild on an unchanged rule
    reproduces all three artifacts byte for byte.
    """
    import csv
    import io
    chosen = {}
    by_rank = {}
    with open(os.path.join(OUT_DIR, "lemmas.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            entry = {"pos": r["pos"], "ipa": r["ipa"] or None, "audio": r["audio_url"] or None, "forms": []}
            chosen.setdefault(apos_key(r["lemma"]), []).append(entry)
            by_rank[r["rank"]] = entry
    with gzip.open(os.path.join(OUT_DIR, "forms.csv.gz"), "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(io.StringIO(fh.read())):
            by_rank[r["rank"]]["forms"].append({"form": r["form"], "tags": r["tags"].split(" "), "infl": r["inflectional"] == "1"})
    return chosen


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--stdin", action="store_true", help="read the kaikki jsonl dump from stdin")
    src.add_argument("--kaikki", help="path to the kaikki Ukrainian jsonl dump")
    src.add_argument("--rebuild", action="store_true", help="recompute from the committed lemmas.csv + forms.csv.gz, no dump")
    ap.add_argument("--dump-date", help="the dump's Last-Modified date, yyyy-mm-dd (required with a dump; --rebuild keeps the committed one)")
    args = ap.parse_args()
    if args.rebuild:
        m = re.search(r'"dumpDate": "([^"]+)"', open(OUT_DATA, encoding="utf-8").read())
        args.dump_date = m.group(1) if m else None
    elif not args.dump_date:
        ap.error("--dump-date is required with --stdin / --kaikki")

    seed = json.load(open(SEED, encoding="utf-8"))
    rows = seed["rows"]
    # apostrophe-folded lemma key -> every list row with that spelling, and the
    # set of UD pos families they cover
    top = {}
    for i, r in enumerate(rows[:TOP_N]):
        key = apos_key(r["lemma"])
        e = top.setdefault(key, {"rows": [], "fams": set()})
        e["rows"].append({"rank": i + 1, "lemma": r["lemma"], "pos": r["pos"]})
        e["fams"].add(FAM.get(r["pos"], r["pos"]))

    if args.rebuild:
        chosen = chosen_from_published()
    else:
        chosen = chosen_from_dump(sys.stdin if args.stdin else open(args.kaikki, encoding="utf-8"), top)

    out_rows = []
    for key, meta in top.items():
        for c in chosen.get(key, []):
            rank, lemma = stamp(meta, c["pos"])
            # the multiplier measures distinct wordform STRINGS a learner must
            # recognize, so syncretic and alternate-stress rows collapse by string
            form_count = len({f["form"] for f in c["forms"] if f["infl"]})
            out_rows.append({
                "rank": rank,
                "lemma": lemma,
                "pos": c["pos"],
                "ipa": c["ipa"],
                "audio": c["audio"],
                "formCount": form_count,
                "forms": c["forms"],
            })

    out_rows.sort(key=lambda x: x["rank"])
    count = len(out_rows)

    # ---- aggregates for the browser tier ----
    from collections import Counter
    with_para = sum(1 for r in out_rows if r["formCount"] > 0)
    with_ipa = sum(1 for r in out_rows if r["ipa"])
    with_audio = sum(1 for r in out_rows if r["audio"])
    fam_forms = Counter()
    fam_lemmas = Counter()
    for r in out_rows:
        fam = FAM.get(r["pos"], "other")
        if r["formCount"] > 0:
            fam_forms[fam] += r["formCount"]
            fam_lemmas[fam] += 1
    per_fam = {}
    for fam in fam_lemmas:
        per_fam[fam] = {"lemmas": fam_lemmas[fam], "avgForms": r1(fam_forms[fam] / fam_lemmas[fam])}
    tot_forms = sum(fam_forms.values())
    tot_infl = sum(fam_lemmas.values())
    multiplier = r1(tot_forms / tot_infl) if tot_infl else 0

    # coverage of the top-N target (the honest denominator is the whole slice)
    def pct(n):
        return r1(n / TOP_N * 100)

    # A canonical case order for the noun grid + a compact verb key-form set, used
    # by the sample paradigms the page renders. Best-effort: shows what is present.
    def grid_for(r):
        fam = FAM.get(r["pos"], "other")
        cases = ["nominative", "genitive", "dative", "accusative", "instrumental", "locative", "vocative"]
        if fam in ("noun", "adj", "pron", "num"):
            g = []
            for c in cases:
                sg = next((f["form"] for f in r["forms"] if c in f["tags"] and "plural" not in f["tags"]), None)
                pl = next((f["form"] for f in r["forms"] if c in f["tags"] and "plural" in f["tags"]), None)
                if sg or pl:
                    g.append({"case": c, "sg": sg, "pl": pl})
            return {"kind": "case", "rows": g}
        if fam == "verb":
            def pick(*need):
                need = set(need)
                return next((f["form"] for f in r["forms"] if need.issubset(set(f["tags"]))), None)
            g = [
                {"label": "infinitive", "form": pick("infinitive")},
                {"label": "1sg present", "form": pick("first-person", "present", "singular")},
                {"label": "2sg present", "form": pick("second-person", "present", "singular")},
                {"label": "3sg present", "form": pick("third-person", "present", "singular")},
                {"label": "3pl present", "form": pick("third-person", "present", "plural")},
                {"label": "past m", "form": pick("past", "masculine", "singular")},
                {"label": "past f", "form": pick("past", "feminine", "singular")},
                {"label": "imperative 2sg", "form": pick("imperative", "second-person", "singular")},
            ]
            return {"kind": "verb", "rows": [x for x in g if x["form"]]}
        return {"kind": "other", "rows": []}

    # deterministic sample: a few recognizable high-frequency lemmas with rich
    # paradigms + IPA + audio, one noun / verb / adjective at least
    def sample_pick():
        picks = []
        for fam in ("noun", "verb", "adj", "num", "pron"):
            best = None
            for r in out_rows:
                if FAM.get(r["pos"]) != fam or not r["ipa"] or not r["audio"]:
                    continue
                if r["formCount"] < 6:
                    continue
                if best is None or r["rank"] < best["rank"]:
                    best = r
            if best:
                picks.append(best)
        picks.sort(key=lambda r: r["rank"])
        return [{
            "rank": r["rank"], "lemma": r["lemma"], "pos": r["pos"], "ipa": r["ipa"],
            "audio": r["audio"], "formCount": r["formCount"], "grid": grid_for(r),
        } for r in picks[:5]]

    coverage = {
        "paradigm": with_para, "paradigmPct": pct(with_para),
        "ipa": with_ipa, "ipaPct": pct(with_ipa),
        "audio": with_audio, "audioPct": pct(with_audio),
    }
    browser = {
        "source": "Wiktionary via kaikki.org (wiktextract)",
        "sourceUrl": SOURCE_URL,
        "dumpDate": args.dump_date,
        "license": LICENSE,
        "method": (
            "join the top-%d frequency lemmas to the open Wiktionary extraction "
            "(kaikki.org); keep the inflected forms verbatim (stress marks included), "
            "drop romanizations / placeholders / templates; link Wikimedia audio, "
            "never re-host; grade coverage honestly" % TOP_N
        ),
        "targetN": TOP_N,
        "count": count,
        "coverage": coverage,
        "inflectedLemmas": tot_infl,
        "totalForms": tot_forms,
        "multiplier": multiplier,
        "perFamily": per_fam,
        "audioAttribution": "Pronunciation audio: Wikimedia Commons contributors, CC BY-SA",
        "sample": sample_pick(),
        "downloads": {
            "lemmas": "/downloads/ukrainian-frequency/paradigms/lemmas.csv",
            "forms": "/downloads/ukrainian-frequency/paradigms/forms.csv.gz",
        },
    }
    with open(OUT_DATA, "w", encoding="utf-8") as fh:
        fh.write(
            "// GENERATED by scripts/ukrainian-frequency/extract-paradigms.py - do not edit by hand.\n"
            "// Browser-safe tier of thread 04 (audio and paradigms): coverage grades, the\n"
            "// inflection-multiplier finding, per-family averages, and a few sample paradigms\n"
            "// (IPA + a Wikimedia audio link). The full record is the committed public\n"
            "// lemmas.csv + forms.csv.gz (which double as the open-data release). Wiktionary\n"
            "// text + Wikimedia audio, CC BY-SA; see paradigms.SOURCE.md.\n"
        )
        fh.write("export const PARADIGMS = " + json.dumps(browser, ensure_ascii=False, indent=2) + ";\n")

    # ---- public downloads ----
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "lemmas.csv"), "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,ipa,form_count,audio_url\n")
        for r in out_rows:
            ipa = (r["ipa"] or "").replace(",", " ")
            fh.write(f"{r['rank']},{r['lemma']},{r['pos']},{ipa},{r['formCount']},{r['audio'] or ''}\n")
    # forms.csv is large at the full list (~14 MB), so it ships gzipped, the same
    # posture as the repo's other big committed data file (uk-lexicon-dict_uk.txt.gz).
    # mtime=0 keeps the gzip byte-identical across re-runs (the drift-guard contract).
    forms_lines = ["rank,lemma,pos,form,tags,inflectional\n"]
    for r in out_rows:
        for f in r["forms"]:
            tags = " ".join(f["tags"])
            forms_lines.append(f"{r['rank']},{r['lemma']},{r['pos']},{f['form']},{tags},{int(f['infl'])}\n")
    forms_bytes = "".join(forms_lines).encode("utf-8")
    with open(os.path.join(OUT_DIR, "forms.csv.gz"), "wb") as fh:
        fh.write(gzip.compress(forms_bytes, compresslevel=9, mtime=0))

    print(f"wrote {count} lemmas of top-{TOP_N}")
    print(f"  coverage: paradigm {coverage['paradigmPct']}% / IPA {coverage['ipaPct']}% / audio {coverage['audioPct']}%")
    print(f"  inflection multiplier: {multiplier} forms per inflected lemma")
    print(f"  per family: {per_fam}")
    print(f"  sample lemmas: {[s['lemma'] for s in browser['sample']]}")


if __name__ == "__main__":
    main()
