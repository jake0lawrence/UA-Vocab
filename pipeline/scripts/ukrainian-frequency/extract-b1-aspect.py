#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 3: the ASPECT RELATION TABLE.
#
# Aspect pairs as a relation table, not a column. Pairing in Ukrainian is
# lexical and often not one-to-one: suppletive pairs (брати / взяти), and
# perfectives that shift meaning (читати: прочитати against перечитати,
# дочитати). So this writes one row per (B1 verb, related verb), and each member
# keeps its own PULS level, which makes a split-level pair visible instead of
# averaging it away.
#
# The universe is every verb the validated PULS map labels B1 on thread 01's
# list (puls-cefr.json, pos VERB, level B1). Three sources, all open:
#   - PULS (by permission, CC-BY-NC-SA): the level and the aspect tag of each entry
#     (дієслово (недок.) / (док.) / unspecified).
#   - Wiktionary via kaikki.org (CC-BY-SA): the aspect PARTNER(S) each verb entry
#     lists in its headword line ("perfective X" / "imperfective Y").
#   - UberText 2.0's full lemma frequency dictionary (lang-uk, CC-BY): the
#     corpus attestation and count of every related form, on or off the list.
#
# Two kinds of relation row:
#   - partner:  a Wiktionary-listed aspect partner (pf or impf), with its own
#               level, rank, and corpus count.
#   - prefixed: a corpus-attested prefix + lemma derivative of an imperfective
#               B1 verb (the perfectives that shift meaning live here), with the
#               same columns. Attested means at least ATTEST_MIN occurrences in
#               UberText as a VERB lemma.
# And the MOTION-VERB GRID: prefix x root over the eight core pairs, generated,
# then kept only where the corpus attests the form.
#
# Two modes:
#   --snapshot   reads the raw dumps (not vendored) and writes the committed
#                snapshots: b1-aspect.wiktionary.json (the verb entries we
#                consulted, aspect partners only, no conjugation tables) and
#                b1-aspect.ubertext-counts.json (the counts of every lemma we
#                looked up, zero when absent). Then builds.
#   (default)    rebuilds every derived artifact from the committed snapshots,
#                so CI can re-derive the table without the dumps.
#
# Reproduce the snapshot:
#   curl -sS https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl \
#     | python3 scripts/ukrainian-frequency/extract-b1-aspect.py --snapshot --kaikki-stdin \
#         --freq /path/to/ubertext_freq.csv.xz
#
# House rule: no em-dashes in anything this writes.
# ---------------------------------------------------------------------------

import argparse
import csv
import json
import lzma
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
LIB = os.path.join(ROOT, "src", "lib", "ukrainian-frequency")
DL = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "b1-extension")

SNAPSHOT_DATE = "2026-09-11"
ATTEST_MIN = 100  # occurrences in UberText 2.0 (1.5 B tokens) for a form to count as attested
SAMPLE = 14
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_IDX = {l: i + 1 for i, l in enumerate(LEVELS)}

# Verbal prefixes, generous on purpose: attestation is the filter.
PREFIXES = ["в", "у", "ви", "від", "віді", "до", "з", "с", "зі", "за", "на", "над", "наді", "о", "об", "обі",
            "пере", "під", "піді", "по", "при", "про", "роз", "розі"]

# The grid's columns: one per prefix, allomorphs folded in (від/віді, з/зі/с,
# об/обі, над/наді, під/піді, роз/розі, в/у), so the same attested form is not
# counted under two spellings of one prefix.
CANON_PREFIXES = {
    "в": ["в", "у"], "ви": ["ви"], "від": ["від", "віді"], "до": ["до"], "з": ["з", "зі", "с"],
    "за": ["за"], "на": ["на"], "над": ["над", "наді"], "о": ["о"], "об": ["об", "обі"],
    "пере": ["пере"], "під": ["під", "піді"], "по": ["по"], "при": ["при"], "про": ["про"], "роз": ["роз", "розі"],
}
CANON_OF = {a: c for c, allo in CANON_PREFIXES.items() for a in allo}

# Suppletive and irregular pairs, hand-curated: the closed set no dictionary
# link can be trusted to carry (PULS added its aspect counterparts by hand for
# the same reason). Each is asserted as a partner row even when Wiktionary
# lists nothing, and marked suppletive.
SUPPLETIVE = [
    ("брати", "взяти"), ("говорити", "сказати"), ("класти", "покласти"), ("ловити", "піймати"), ("ловити", "спіймати"),
    ("шукати", "знайти"), ("сідати", "сісти"), ("лягати", "лягти"), ("ставати", "стати"), ("іти", "піти"), ("йти", "піти"),
    ("їхати", "поїхати"), ("бачити", "побачити"), ("робити", "зробити"), ("давати", "дати"), ("казати", "сказати"),
    ("приходити", "прийти"), ("виходити", "вийти"), ("заходити", "зайти"), ("знаходити", "знайти"), ("вибирати", "вибрати"),
]

# The eight core motion pairs (indeterminate / determinate). плисти and пливти
# are both standard, so the determinate root carries both.
MOTION = [
    {"gloss": "go on foot", "indet": ["ходити"], "det": ["іти", "йти"]},
    {"gloss": "go by vehicle", "indet": ["їздити"], "det": ["їхати"]},
    {"gloss": "carry", "indet": ["носити"], "det": ["нести"]},
    {"gloss": "convey by vehicle", "indet": ["возити"], "det": ["везти"]},
    {"gloss": "lead", "indet": ["водити"], "det": ["вести"]},
    {"gloss": "run", "indet": ["бігати"], "det": ["бігти"]},
    {"gloss": "fly", "indet": ["літати"], "det": ["летіти"]},
    {"gloss": "swim, sail", "indet": ["плавати"], "det": ["плисти", "пливти"]},
]


def strip_stress(s):
    # Decompose, drop the combining acute (U+0301), recompose: й and ї must come
    # back as single code points or no join downstream matches.
    return unicodedata.normalize("NFC", "".join(ch for ch in unicodedata.normalize("NFD", s) if ch != "́"))


def norm(s):
    # One apostrophe: UberText writes U+2019, Wiktionary and PULS vary, the
    # candidates use ASCII. Every key goes through here.
    return strip_stress(s).replace("’", "'").replace("ʼ", "'").strip().lower()


VOWELS = "аеиіоуюяєї"


def split_forms(s):
    """A Wiktionary partner field can read "створювати,творити" or
    "відзначати<l:rare>"; keep each bare lemma."""
    import re
    s = re.sub(r"<[^>]*>", "", s.replace("[[", "").replace("]]", ""))
    return [norm(x) for x in re.split(r"[,;/]", s) if norm(x)]


def lexicon(wanted):
    """VESUM as the reference lexicon, through pymorphy3's Ukrainian dictionary
    (derived from VESUM): for every lemma we can mention, whether the lexicon
    knows it as an infinitive under that very lemma, and its aspect."""
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer(lang="uk")
    out = {}
    for w in sorted(wanted):
        # is_known: a dictionary hit, not pymorphy's suffix-based guess for an
        # out-of-vocabulary string (which would "know" almost any candidate).
        # A verb's normal form IS its infinitive, and the Ukrainian dictionary
        # tags some infinitives without the infn grammeme, so match on that.
        infn = [p for p in morph.parse(w) if p.tag.POS == "VERB" and p.normal_form == w and p.is_known]
        if not infn:
            continue
        aspects = {p.tag.aspect for p in infn if p.tag.aspect}
        asp = "both" if aspects == {"perf", "impf"} else ("pf" if aspects == {"perf"} else "impf" if aspects == {"impf"} else "")
        out[w] = asp
    return out


def candidates(prefix, root):
    """Orthographic variants of prefix + root. Generous on the consonant-initial
    roots (the corpus and the lexicon decide); explicit on the two vowel-initial
    motion roots, where plain concatenation makes non-words or homographs."""
    out = set()
    if root in ("іти", "йти"):
        if prefix == "по":
            out.add("піти")                        # suppletive
        elif prefix[-1] in VOWELS:
            out.add(prefix + "йти")                # прийти, зайти, вийти, перейти, пройти
        elif prefix == "до":
            out.add("дійти")
        elif prefix.endswith("і"):
            out.add(prefix + "йти")                # обійти, підійти, відійти, зійти, розійти(ся), наді
        else:
            out.add(prefix + "ійти")               # з + і -> зійти, в -> війти? (attestation decides)
    elif root[0] in "їєяю":
        if prefix[-1] in VOWELS or prefix.endswith("і"):
            out.add(prefix + root)                 # виїхати, переїхати, доїхати, приїхати
        else:
            out.add(prefix + "'" + root)           # об'їхати, від'їхати, з'їхати, під'їхати
    else:
        out.add(prefix + root)
    res = set()
    for c in out:
        res.add(c)
        res.add(c + "ся")
    return sorted(res)


# ---------------------------------------------------------------- raw readers
def read_kaikki(stream, wanted):
    """Keep, for every verb entry in `wanted`, its aspect (canonical tag) and the
    partner forms its headword lists. Nothing else from the dump is kept."""
    out = {}
    for line in stream:
        if '"pos"' in line and '"verb"' not in line:  # cheap skip on the raw dump only
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        # The raw dump carries lang_code + pos; a pre-filtered verb file (the
        # streaming helper keeps word / forms / heads only) carries neither.
        if "lang_code" in e and (e.get("lang_code") != "uk" or e.get("pos") != "verb"):
            continue
        word = norm(e.get("word", ""))
        if word not in wanted:
            continue
        head_templates = e.get("head_templates") or [{"args": a} for a in e.get("heads", [])]
        aspect = set()
        partners = []
        for f in e.get("forms", []):
            tags = f.get("tags", [])
            if f.get("source") == "conjugation" or f.get("form") in ("", "-"):
                continue
            form = norm(f.get("form", ""))
            if "canonical" in tags:
                if "imperfective" in tags:
                    aspect.add("impf")
                if "perfective" in tags:
                    aspect.add("pf")
                continue
            if tags == ["perfective"] or tags == ["imperfective"]:
                for one in split_forms(form):
                    partners.append({"form": one, "aspect": "pf" if tags == ["perfective"] else "impf"})
        for h in head_templates:
            args = h.get("args", {})
            for k, asp in (("pf", "pf"), ("pf2", "pf"), ("pf3", "pf"), ("impf", "impf"), ("impf2", "impf"), ("impf3", "impf")):
                v = args.get(k)
                if v:
                    for one in split_forms(norm(v)):
                        partners.append({"form": one, "aspect": asp})
            if args.get("2") in ("impf", "pf") and not aspect:
                aspect.add(args["2"])
            if args.get("2") == "both":
                aspect.update({"impf", "pf"})
        seen = set()
        uniq = []
        for p in partners:
            key = (p["form"], p["aspect"])
            if p["form"] and p["form"] != word and key not in seen:
                seen.add(key)
                uniq.append(p)
        prev = out.get(word)
        entry = {"aspect": sorted(aspect), "partners": uniq}
        if prev:  # several etymology sections: union
            prev["aspect"] = sorted(set(prev["aspect"]) | set(entry["aspect"]))
            for p in uniq:
                if p not in prev["partners"]:
                    prev["partners"].append(p)
        else:
            out[word] = entry
    return out


def read_freq(path, wanted):
    """Counts for the wanted lemmas as VERB rows. A lemma absent from the
    dictionary is simply absent here (read as zero downstream), so the snapshot
    stays small; `lookedUp` records how many were queried."""
    counts = {}
    opener = lzma.open if path.endswith(".xz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["pos"] != "VERB":
                continue
            w = norm(r["lemma"])
            if w in wanted:
                c = counts.setdefault(w, [0, 0])
                c[0] += int(r["count"])
                c[1] += int(r["doc_count"])
    return counts


# ---------------------------------------------------------------- inputs
def load_inputs():
    seed = json.load(open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    puls = json.load(open(os.path.join(DATA, "puls-cefr.json"), encoding="utf-8"))
    rank = {}
    for i, r in enumerate(seed["rows"]):
        if r["pos"] == "VERB":
            rank.setdefault(norm(r["lemma"]), i + 1)
    validated = {norm(r["lemma"]): r["level"] for r in puls["rows"] if r["pos"] == "VERB"}
    b1 = [dict(r, lemma=norm(r["lemma"])) for r in puls["rows"] if r["pos"] == "VERB" and r["level"] == "B1"]

    raw_level, raw_aspect = {}, {}
    with open(os.path.join(DATA, "puls-cefr.raw.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["pos_uk"].startswith("дієслово") or r["level"] not in LEVEL_IDX:
                continue
            asp = "impf" if "недок" in r["pos_uk"] else "pf" if "док" in r["pos_uk"] else "unspecified"
            for v in [norm(x) for x in r["lemma"].split(",")]:
                if not v or " " in v:
                    continue
                if v not in raw_level or LEVEL_IDX[r["level"]] < LEVEL_IDX[raw_level[v]]:
                    raw_level[v] = r["level"]
                raw_aspect.setdefault(v, set()).add(asp)
    # Thread 03's derussification pass: forms the open style tooling flags
    # (LanguageTool replacement tables), with the native suggestion. A grid cell
    # or a prefixed derivative that is attested but flagged is shown as such.
    flagged = {}
    deruss_path = os.path.join(DATA, "derussification.json")
    if os.path.exists(deruss_path):
        for r in json.load(open(deruss_path, encoding="utf-8"))["rows"]:
            flagged[r["lemma"].lower()] = r.get("suggestion")
    return seed, puls, rank, validated, b1, raw_level, raw_aspect, flagged


def wanted_set(rank, raw_level, b1, wikt=None):
    """Every verb lemma the table can mention: the B1 verbs, their prefixed
    candidates, the motion grid, and (once Wiktionary has been read) the listed
    partners. Levels come from PULS directly, so the rest of the list is not
    looked up here."""
    w = {r["lemma"].lower() for r in b1}
    for a, b in SUPPLETIVE:
        w.add(a)
        w.add(b)
    for r in b1:
        for p in PREFIXES:
            w.update(candidates(p, r["lemma"].lower()))
    for m in MOTION:
        for root in m["indet"] + m["det"]:
            w.add(root)
            for p in PREFIXES:
                w.update(candidates(p, root))
    if wikt:
        for e in wikt.values():
            for p in e["partners"]:
                w.add(p["form"])
    return w


# ---------------------------------------------------------------- build
def level_of(lemma, validated, raw_level):
    if lemma in validated:
        return validated[lemma], True
    if lemma in raw_level:
        return raw_level[lemma], False
    return None, False


def puls_aspect(lemma, raw_aspect):
    a = raw_aspect.get(lemma)
    if not a:
        return None
    a = a - {"unspecified"} or a
    if a == {"impf"}:
        return "impf"
    if a == {"pf"}:
        return "pf"
    if a == {"unspecified"}:
        return "unspecified"
    return "both"


def build(wikt, counts, lex, flagged, seed, puls, rank, validated, b1, raw_level, raw_aspect):
    verbs, relations = [], []
    for r in b1:
        lemma = r["lemma"].lower()
        w = wikt.get(lemma)
        pa = puls_aspect(lemma, raw_aspect)
        wa = None
        if w:
            wa = "both" if set(w["aspect"]) == {"impf", "pf"} else (w["aspect"][0] if w["aspect"] else None)
        va = lex.get(lemma) or None  # VESUM, the reference lexicon
        # PULS first (it is the level's own source), then Wiktionary, then VESUM.
        aspect = pa if pa in ("impf", "pf", "both") else (wa or va)
        agree = None if (pa in (None, "unspecified") or wa is None) else (pa == wa)
        agree_vesum = None if (pa in (None, "unspecified") or va is None) else (pa == va)
        partners = list(w["partners"]) if w else []
        # the hand-curated suppletive pairs, asserted whether or not Wiktionary lists them
        supp = set()
        for a, b in SUPPLETIVE:
            if lemma == a:
                supp.add((b, "pf"))
            elif lemma == b:
                supp.add((a, "impf"))
        for form, asp in sorted(supp):
            if not any(p["form"] == form for p in partners):
                partners.append({"form": form, "aspect": asp})
        rel_rows = []
        for p in partners:
            lvl, on_list = level_of(p["form"], validated, raw_level)
            c = counts.get(p["form"], [0, 0])
            rel_rows.append({
                "b1": lemma, "related": p["form"], "kind": "partner", "relatedAspect": p["aspect"],
                "relatedLevel": lvl, "relatedOnList": p["form"] in rank, "relatedValidated": on_list,
                "relatedRank": rank.get(p["form"]), "count": c[0], "docs": c[1],
                "attested": c[0] >= ATTEST_MIN, "splitLevel": (lvl is not None and lvl != "B1"),
                "suppletive": (p["form"], p["aspect"]) in supp,
            })
        if aspect in ("impf", "both", None):
            seen = {x["related"] for x in rel_rows}
            for pfx in PREFIXES:
                for cand in candidates(pfx, lemma):
                    if cand in seen:
                        continue
                    c = counts.get(cand, [0, 0])
                    if c[0] < ATTEST_MIN or cand not in lex:  # corpus AND lexicon must both know it
                        continue
                    seen.add(cand)
                    lvl, on_list = level_of(cand, validated, raw_level)
                    rel_rows.append({
                        "b1": lemma, "related": cand, "kind": "prefixed", "relatedAspect": "pf",
                        "relatedLevel": lvl, "relatedOnList": cand in rank, "relatedValidated": on_list,
                        "relatedRank": rank.get(cand), "count": c[0], "docs": c[1],
                        "attested": True, "splitLevel": (lvl is not None and lvl != "B1"), "prefix": pfx,
                        "flagged": cand in flagged, "suggestion": flagged.get(cand),
                    })
        rel_rows.sort(key=lambda x: (0 if x["kind"] == "partner" else 1, -x["count"]))
        if w is None:
            status = "not-in-wiktionary"
        elif aspect == "both":
            status = "biaspectual"
        elif partners:
            status = "paired"
        else:
            status = "no-partner-listed"
        verbs.append({
            "lemma": lemma, "rank": r["rank"], "level": "B1", "aspect": aspect,
            "aspectPuls": pa, "aspectWiktionary": wa, "aspectVesum": va,
            "aspectAgree": agree, "aspectAgreeVesum": agree_vesum, "inLexicon": lemma in lex,
            "status": status, "partners": len(partners),
            "prefixed": sum(1 for x in rel_rows if x["kind"] == "prefixed"),
            "count": counts.get(lemma, [0, 0])[0],
        })
        relations.extend(rel_rows)

    # the motion grid
    grid = []
    for m in MOTION:
        for side in ("indet", "det"):
            for pfx, allomorphs in CANON_PREFIXES.items():
                cands = []
                for root in m[side]:
                    for a in allomorphs:
                        cands.extend(candidates(a, root))
                cands = sorted(set(cands))
                attested = [(c, counts.get(c, [0, 0])) for c in cands if counts.get(c, [0, 0])[0] >= ATTEST_MIN and c in lex]
                attested.sort(key=lambda x: -x[1][0])
                forms = []
                for c, cnt in attested:
                    lvl, on_list = level_of(c, validated, raw_level)
                    forms.append({"form": c, "count": cnt[0], "docs": cnt[1], "rank": rank.get(c), "level": lvl, "validated": on_list,
                                  "flagged": c in flagged, "suggestion": flagged.get(c)})
                grid.append({"pair": m["gloss"], "root": "/".join(m[side]), "side": side, "prefix": pfx,
                             "checked": len(cands), "attested": len(forms), "forms": forms})
    bare = []
    for m in MOTION:
        for side in ("indet", "det"):
            for root in m[side]:
                lvl, on_list = level_of(root, validated, raw_level)
                bare.append({"pair": m["gloss"], "side": side, "form": root, "count": counts.get(root, [0, 0])[0],
                             "rank": rank.get(root), "level": lvl, "validated": on_list})

    # aggregates
    statuses = {}
    for v in verbs:
        statuses[v["status"]] = statuses.get(v["status"], 0) + 1
    aspects = {}
    for v in verbs:
        k = v["aspect"] or "unknown"
        aspects[k] = aspects.get(k, 0) + 1
    partner_rows = [x for x in relations if x["kind"] == "partner"]
    prefixed_rows = [x for x in relations if x["kind"] == "prefixed"]
    split = [x for x in partner_rows if x["splitLevel"]]
    split_levels = {}
    for x in split:
        split_levels[x["relatedLevel"]] = split_levels.get(x["relatedLevel"], 0) + 1
    disagree = [v for v in verbs if v["aspectAgree"] is False]
    prefixed_levels = {}
    for x in prefixed_rows:
        k = x["relatedLevel"] or "none"
        prefixed_levels[k] = prefixed_levels.get(k, 0) + 1
    per_prefix = {}
    for x in prefixed_rows:
        c = CANON_OF.get(x["prefix"], x["prefix"])
        per_prefix[c] = per_prefix.get(c, 0) + 1
    grid_attested = sum(1 for g in grid if g["attested"])
    per_pair = {}
    for g in grid:
        per_pair.setdefault(g["pair"], {"indet": 0, "det": 0})[g["side"]] += 1 if g["attested"] else 0

    meta = {
        "snapshot": SNAPSHOT_DATE,
        "universe": "every verb the validated PULS map labels B1 on the top-12000 list",
        "sources": {
            "levelsAndAspect": {"name": "Ukrainian Vocabulary Profile (PULS)", "url": "https://puls.peremova.org/", "license": "CC-BY-NC-SA-4.0", "permission": "by permission (V. Starko, 2026-07); CC BY-NC-SA 4.0 at the authors' decision (O. Synchak, 2026-09-24)"},
            "partners": {"name": "Wiktionary via kaikki.org (wiktextract)", "url": "https://kaikki.org/dictionary/Ukrainian/", "license": "CC-BY-SA-3.0"},
            "attestation": {"name": "UberText 2.0 lemma frequency dictionary (lang-uk)", "url": "https://lang.org.ua/en/ubertext/", "license": "CC-BY-4.0"},
        },
        "attestMin": ATTEST_MIN,
        "prefixes": PREFIXES,
        "b1Verbs": len(verbs),
        "aspects": aspects,
        "statuses": statuses,
        "partnerRows": len(partner_rows),
        "suppletiveRows": sum(1 for x in partner_rows if x.get("suppletive")),
        "suppletiveTable": [list(p) for p in SUPPLETIVE],
        "partnerAttested": sum(1 for x in partner_rows if x["attested"]),
        "partnerOnList": sum(1 for x in partner_rows if x["relatedOnList"]),
        "partnerLeveled": sum(1 for x in partner_rows if x["relatedLevel"]),
        "splitLevel": len(split),
        "splitLevels": split_levels,
        "aspectDisagree": len(disagree),
        "aspectDisagreeVesum": sum(1 for v in verbs if v["aspectAgreeVesum"] is False),
        "inLexicon": sum(1 for v in verbs if v["inLexicon"]),
        "aspectFromVesumOnly": sum(1 for v in verbs if v["aspect"] and v["aspectPuls"] not in ("impf", "pf", "both") and v["aspectWiktionary"] is None),
        "prefixedRows": len(prefixed_rows),
        "prefixedLevels": prefixed_levels,
        "prefixedPerPrefix": dict(sorted(per_prefix.items(), key=lambda kv: -kv[1])),
        "prefixedFlagged": sum(1 for x in prefixed_rows if x["flagged"]),
        "motion": {"pairs": len(MOTION), "cells": len(grid), "attested": grid_attested,
                   "checked": sum(g["checked"] for g in grid), "perPair": per_pair,
                   "forms": sum(len(g["forms"]) for g in grid),
                   "flagged": sum(1 for g in grid for f in g["forms"] if f["flagged"])},
        "download": "/downloads/ukrainian-frequency/b1-extension/aspect-relations.csv",
        "motionDownload": "/downloads/ukrainian-frequency/b1-extension/motion-grid.csv",
    }
    full = dict(meta)
    full["verbs"] = verbs
    full["relations"] = relations
    full["motionBare"] = bare
    full["motionGrid"] = grid
    return full


def write_outputs(full):
    with open(os.path.join(DATA, "b1-aspect.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    os.makedirs(DL, exist_ok=True)
    with open(os.path.join(DL, "aspect-relations.csv"), "w", encoding="utf-8") as fh:
        # csv.writer, not a bare join: a field holding a comma (the motion gloss
        # "swim, sail") must be quoted or every column after it shifts.
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["b1_verb", "b1_rank", "b1_aspect", "related", "kind", "related_aspect", "related_level", "related_validated", "related_rank", "ubertext_count", "attested", "split_level"])
        by = {v["lemma"]: v for v in full["verbs"]}
        for x in full["relations"]:
            v = by[x["b1"]]
            w.writerow([x["b1"], v["rank"], v["aspect"] or "", x["related"], x["kind"], x["relatedAspect"],
                        x["relatedLevel"] or "", "yes" if x["relatedValidated"] else "no",
                        x["relatedRank"] or "", x["count"], "yes" if x["attested"] else "no",
                        "yes" if x["splitLevel"] else "no"])
    with open(os.path.join(DL, "motion-grid.csv"), "w", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["pair", "side", "root", "prefix", "candidates_checked", "attested_form", "ubertext_count", "rank", "level"])
        for g in full["motionGrid"]:
            if not g["forms"]:
                w.writerow([g["pair"], g["side"], g["root"], g["prefix"], g["checked"], "", "", "", ""])
            for f in g["forms"]:
                w.writerow([g["pair"], g["side"], g["root"], g["prefix"], g["checked"], f["form"], f["count"], f["rank"] or "", f["level"] or ""])

    # browser tier: aggregates + the split-level rows + the motion grid + a sample
    partner_rows = [x for x in full["relations"] if x["kind"] == "partner"]
    split = [x for x in partner_rows if x["splitLevel"]]
    split.sort(key=lambda x: (LEVEL_IDX.get(x["relatedLevel"], 9), -x["count"]))
    by = {v["lemma"]: v for v in full["verbs"]}
    sample = sorted(partner_rows, key=lambda x: by[x["b1"]]["rank"])[:SAMPLE]
    prefixed_sample = sorted([x for x in full["relations"] if x["kind"] == "prefixed" and x["relatedLevel"]], key=lambda x: -x["count"])[:SAMPLE]
    disagree = [v for v in full["verbs"] if v["aspectAgree"] is False]
    slim = {k: v for k, v in full.items() if k not in ("verbs", "relations", "motionBare", "motionGrid")}
    slim["splitRows"] = [{"b1": x["b1"], "b1Rank": by[x["b1"]]["rank"], "related": x["related"], "relatedAspect": x["relatedAspect"],
                          "relatedLevel": x["relatedLevel"], "relatedValidated": x["relatedValidated"], "relatedRank": x["relatedRank"], "count": x["count"]} for x in split]
    slim["sample"] = [{"b1": x["b1"], "b1Rank": by[x["b1"]]["rank"], "b1Aspect": by[x["b1"]]["aspect"], "related": x["related"], "relatedAspect": x["relatedAspect"],
                       "relatedLevel": x["relatedLevel"], "relatedRank": x["relatedRank"], "count": x["count"]} for x in sample]
    slim["prefixedSample"] = [{"b1": x["b1"], "related": x["related"], "prefix": x["prefix"], "relatedLevel": x["relatedLevel"], "relatedRank": x["relatedRank"], "count": x["count"]} for x in prefixed_sample]
    slim["aspectDisagreeRows"] = [{"lemma": v["lemma"], "rank": v["rank"], "aspectPuls": v["aspectPuls"], "aspectWiktionary": v["aspectWiktionary"], "aspectVesum": v["aspectVesum"]} for v in disagree]
    slim["motionBare"] = full["motionBare"]
    # attested cells only; the empty cells are implied by the prefix list x the roots
    slim["motionGrid"] = [{"pair": g["pair"], "side": g["side"], "root": g["root"], "prefix": g["prefix"],
                           "forms": [{"form": f["form"], "count": f["count"], "rank": f["rank"], "level": f["level"], "flagged": f["flagged"], "suggestion": f["suggestion"]} for f in g["forms"]]}
                          for g in full["motionGrid"] if g["forms"]]
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-b1-aspect.py - do not edit by hand.\n"
        "// Browser-safe tier of the B1 extension's ASPECT RELATION TABLE (stage 3): every verb\n"
        "// the validated PULS map labels B1 on the top-12000 list, related to its Wiktionary-\n"
        "// listed aspect partner(s) and its corpus-attested prefixed derivatives, each member\n"
        "// keeping its own PULS level so a split-level pair is visible. Plus the motion-verb\n"
        "// grid (prefix x root over the eight core pairs, corpus-attested cells only). The full\n"
        "// table is src/data/ukrainian-frequency/b1-aspect.json and the public CSVs.\n"
        "export const B1_ASPECT = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(LIB, "b1-aspect.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="read the raw dumps and rewrite the committed snapshots first")
    ap.add_argument("--kaikki", help="path to the (filtered or full) kaikki Ukrainian jsonl")
    ap.add_argument("--kaikki-stdin", action="store_true", help="read the kaikki jsonl from stdin")
    ap.add_argument("--freq", help="path to ubertext_freq.csv(.xz)")
    args = ap.parse_args()

    seed, puls, rank, validated, b1, raw_level, raw_aspect, flagged = load_inputs()
    wikt_path = os.path.join(DATA, "b1-aspect.wiktionary.json")
    counts_path = os.path.join(DATA, "b1-aspect.ubertext-counts.json")

    if args.snapshot:
        wanted = wanted_set(rank, raw_level, b1)
        stream = sys.stdin if args.kaikki_stdin else open(args.kaikki, encoding="utf-8")
        wikt = read_kaikki(stream, wanted)
        wanted = wanted_set(rank, raw_level, b1, wikt)
        counts = read_freq(args.freq, wanted)
        lex = lexicon(wanted)
        with open(wikt_path, "w", encoding="utf-8") as fh:
            json.dump({"source": "Wiktionary via kaikki.org (wiktextract), Ukrainian verb entries", "url": "https://kaikki.org/dictionary/Ukrainian/",
                       "license": "CC-BY-SA-3.0", "snapshot": SNAPSHOT_DATE, "kept": "aspect (canonical tag) and headword-listed aspect partners only, for the verbs consulted",
                       "entries": dict(sorted(wikt.items()))}, fh, ensure_ascii=False, indent=0)
            fh.write("\n")
        with open(counts_path, "w", encoding="utf-8") as fh:
            json.dump({"source": "UberText 2.0 lemma frequency dictionary (lang-uk), VERB rows", "url": "https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz",
                       "license": "CC-BY-4.0", "snapshot": SNAPSHOT_DATE, "fields": "[count, doc_count]; a lemma absent here was looked up and is absent from the dictionary as a VERB",
                       "lookedUp": len(wanted), "found": len(counts),
                       "lexiconSource": "VESUM via pymorphy3 (pymorphy3-dicts-uk); value is the aspect the lexicon gives the infinitive (pf / impf / both / empty), keyed only for lemmas it knows as an infinitive under that lemma",
                       "lexicon": lex,
                       "counts": dict(sorted(counts.items()))}, fh, ensure_ascii=False, indent=0)
            fh.write("\n")
        print(f"snapshot: {len(wikt)} wiktionary verb entries, {len(counts)} of {len(wanted)} lemmas found in UberText, {len(lex)} known to the lexicon")

    wikt = json.load(open(wikt_path, encoding="utf-8"))["entries"]
    snap = json.load(open(counts_path, encoding="utf-8"))
    counts, lex = snap["counts"], snap["lexicon"]
    full = build(wikt, counts, lex, flagged, seed, puls, rank, validated, b1, raw_level, raw_aspect)
    write_outputs(full)
    print(f"B1 verbs: {full['b1Verbs']}; statuses {full['statuses']}; aspects {full['aspects']}")
    print(f"partner rows {full['partnerRows']} (attested {full['partnerAttested']}, leveled {full['partnerLeveled']}), split-level {full['splitLevel']} {full['splitLevels']}")
    print(f"prefixed rows {full['prefixedRows']} {full['prefixedLevels']}; aspect disagreements {full['aspectDisagree']}")
    print(f"motion grid: {full['motion']['attested']} of {full['motion']['cells']} cells attested; {full['motion']['perPair']}")


if __name__ == "__main__":
    main()
