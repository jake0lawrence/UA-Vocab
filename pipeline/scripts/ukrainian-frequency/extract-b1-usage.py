#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 3: CASE GOVERNMENT, COLLOCATIONS,
# and ATTESTED EXAMPLES for the validated B1 set.
#
# Everything here is an aggregate over parsed sentences of UberText 2.0's
# Wikipedia subcorpus (parse-b1-corpus.py). Three products, all counts first:
#
#   government    verb + preposition + Case, with the share of that verb's
#                 nominal dependents. Shown above a threshold (SHOW_SHARE and
#                 SHOW_MIN), raw counts kept for every pattern.
#   collocations  dependency-linked lemma pairs ranked by logDice
#                 (14 + log2(2 f_xy / (f_x + f_y))), never raw surface bigrams,
#                 because surface bigrams surface function-word noise.
#   examples      attested Wikipedia sentences (CC-BY-SA, license-compatible
#                 with the validated overlay), kept verbatim with whitespace
#                 normalized. Nothing is generated.
#
# The parser is a parser, so its error on oblique dependents is estimated, not
# assumed: REFERENCE below is a maintainer-written list of textbook government
# for about 60 B1 verbs (not an independent annotator, and the page says so), and the
# builder reports how often the corpus's top pattern agrees with it.
#
# Two modes, same posture as extract-b1-aspect.py:
#   --snapshot --parsed FILE   slice the parse output down to the B1 set and
#                              commit that slice (b1-usage.snapshot.json)
#   (default)                  rebuild every derived artifact from the snapshot
#
# House rule: no em-dashes.
# ---------------------------------------------------------------------------

import argparse
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
LIB = os.path.join(ROOT, "src", "lib", "ukrainian-frequency")
DL = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "b1-extension")

SNAPSHOT_DATE = "2026-09-11"
SHOW_SHARE = 0.10   # a government pattern is displayed at >= 10 percent of the verb's dependents
SHOW_MIN = 3        # and at least 3 observations
GOV_MIN_TOTAL = 5   # a verb's government is reported at >= 5 observations
PAIR_MIN = 3        # a collocation needs >= 3 co-occurrences
PAIRS_PER_LEMMA = 8
PAIRS_KEPT = 20     # per lemma, in the snapshot (by raw count, before logDice)
EXAMPLES_PER_LEMMA = 2
MAX_EXAMPLE_CHARS = 220
RELATIONS = {"obl": "verb + oblique", "obj": "verb + object", "iobj": "verb + indirect object", "nsubj": "subject + verb",
             "amod": "adjective + noun", "nmod": "noun + noun", "advmod": "adverb + head"}
# Phonological variants of one preposition, merged before counting.
PREP_VARIANT = {"у": "в", "ув": "в", "уві": "в", "із": "з", "зі": "з", "зо": "з", "о": "об", "би": "б", "піді": "під", "наді": "над", "переді": "перед"}
CASES = {"Nom": "nominative", "Gen": "genitive", "Dat": "dative", "Acc": "accusative", "Ins": "instrumental", "Loc": "locative", "Voc": "vocative"}

# Textbook government for the reference check: verbs the validated map labels
# B1, each with the (preposition, Case) standard grammars give, alternatives
# listed where the textbooks give two (погодитися з + Ins / на + Acc). "" means
# no preposition. Maintainer-written, not an independent annotator; anyone can
# dispute a row, which is the point of committing it.
REFERENCE = [
    ("залежати", [("від", "Gen")]), ("користуватися", [("", "Ins")]), ("розповідати", [("про", "Acc")]),
    ("домовитися", [("про", "Acc"), ("з", "Ins")]), ("складатися", [("з", "Gen")]), ("входити", [("до", "Gen"), ("в", "Acc")]),
    ("належати", [("", "Dat"), ("до", "Gen")]), ("впливати", [("на", "Acc")]), ("свідчити", [("про", "Acc")]),
    ("відмовитися", [("від", "Gen")]), ("приєднатися", [("до", "Gen")]), ("звернутися", [("до", "Gen")]),
    ("звертатися", [("до", "Gen")]), ("ставитися", [("до", "Gen")]), ("потребувати", [("", "Gen")]),
    ("досягти", [("", "Gen")]), ("досягати", [("", "Gen")]), ("уникнути", [("", "Gen")]), ("дотримуватися", [("", "Gen")]),
    ("вимагати", [("", "Gen"), ("", "Acc")]), ("керувати", [("", "Ins")]), ("відрізнятися", [("", "Ins"), ("від", "Gen")]),
    ("служити", [("", "Ins"), ("", "Dat")]), ("боротися", [("з", "Ins"), ("за", "Acc"), ("проти", "Gen")]),
    ("познайомитися", [("з", "Ins")]), ("повідомити", [("про", "Acc"), ("", "Dat")]), ("повідомляти", [("про", "Acc"), ("", "Dat")]),
    ("дізнатися", [("про", "Acc")]), ("йтися", [("про", "Acc")]), ("дозволити", [("", "Dat"), ("", "Acc")]),
    ("дозволяти", [("", "Dat"), ("", "Acc")]), ("наказати", [("", "Dat")]), ("здаватися", [("", "Dat"), ("", "Ins")]),
    ("підійти", [("до", "Gen")]), ("дійти", [("до", "Gen")]), ("походити", [("від", "Gen"), ("з", "Gen")]),
    ("відходити", [("від", "Gen")]), ("закохатися", [("в", "Acc")]), ("погодитися", [("з", "Ins"), ("на", "Acc")]),
    ("вступити", [("до", "Gen"), ("в", "Acc")]), ("вступати", [("до", "Gen"), ("в", "Acc")]), ("потрапити", [("до", "Gen"), ("в", "Acc")]),
    ("звертати", [("на", "Acc"), ("", "Acc")]), ("зникнути", [("з", "Gen")]), ("переїхати", [("до", "Gen"), ("в", "Acc")]),
    ("виїхати", [("до", "Gen"), ("з", "Gen"), ("в", "Acc")]), ("навчатися", [("в", "Loc")]), ("проживати", [("в", "Loc")]),
    ("захищати", [("", "Acc"), ("від", "Gen")]), ("перебувати", [("в", "Loc"), ("під", "Ins")]),
    ("займати", [("", "Acc")]), ("створити", [("", "Acc")]), ("вважати", [("", "Acc"), ("", "Ins")]),
    ("виконувати", [("", "Acc")]), ("містити", [("", "Acc")]), ("включати", [("", "Acc")]), ("утворювати", [("", "Acc")]),
    ("виступити", [("проти", "Gen"), ("з", "Ins"), ("на", "Loc")]), ("дорівнювати", [("", "Dat")]), ("нагадувати", [("", "Acc"), ("", "Dat"), ("про", "Acc")]),
]


CYR = re.compile("[А-ЯІЇЄҐа-яіїєґ]")


def clean_sentence(s):
    # Whitespace normalized, and every dash-class character (the em dash Ukrainian
    # typography uses, the figure dash, the horizontal bar) normalized to a spaced
    # hyphen: the house rule bans em dashes in anything the repo ships, and the
    # download README says the sentences are verbatim up to this normalization.
    s = s.replace("\u00a0", " ")
    s = re.sub("[\u2014\u2015\u2012\u2013]", " - ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:!?)])", r"\1", s)
    return s


def r_half_up(x, places):
    # JavaScript's Math.round semantics, so the browser and CI recompute the same digits
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


def logdice(fxy, fx, fy):
    return r_half_up(14 + math.log2(2 * fxy / (fx + fy)), 2)


def load_b1():
    puls = json.load(open(os.path.join(DATA, "puls-cefr.json"), encoding="utf-8"))
    rows = [r for r in puls["rows"] if r["level"] == "B1"]
    by_lemma = {}
    for r in rows:
        by_lemma.setdefault(r["lemma"].lower(), []).append(r)
    verbs = {r["lemma"].lower(): r["rank"] for r in rows if r["pos"] == "VERB"}
    return rows, by_lemma, verbs


def lemmatizer_check(by_lemma):
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer(lang="uk")
    fam = {"NOUN": {"NOUN"}, "PROPN": {"NOUN"}, "VERB": {"VERB", "INFN"}, "ADJ": {"ADJF", "ADJS", "COMP"}, "ADV": {"ADVB"},
           "NUM": {"NUMR"}, "PRON": {"NPRO"}, "ADP": {"PREP"}, "CCONJ": {"CONJ"}, "SCONJ": {"CONJ"}, "PART": {"PRCL"}, "INTJ": {"INTJ"}}
    total = same = same_pos = unknown = 0
    failures = []
    for lemma, rows in by_lemma.items():
        # VESUM writes the apostrophe as U+0027, the list as U+2019: fold the
        # glyph before asking, so the check measures lemma convention, not
        # punctuation.
        probe = lemma.replace("\u2019", "'").replace("\u02bc", "'")
        for r in rows:
            total += 1
            parses = [p for p in morph.parse(probe) if p.is_known]
            if not parses:
                unknown += 1
                failures.append([lemma, r["pos"], "unknown"])
                continue
            if any(p.normal_form == probe for p in parses):
                same += 1
                if any(p.normal_form == probe and (p.tag.POS in fam.get(r["pos"], set()) or r["pos"] not in fam) for p in parses):
                    same_pos += 1
                else:
                    failures.append([lemma, r["pos"], "pos-mismatch"])
            else:
                failures.append([lemma, r["pos"], "different-normal-form:" + parses[0].normal_form])
    try:
        from importlib.metadata import version as _v
        dicts = f"pymorphy3-dicts-uk {_v('pymorphy3-dicts-uk')}"
    except Exception:
        dicts = "pymorphy3-dicts-uk (version not recorded)"
    return {"headwords": total, "normalFormMatches": same, "normalFormAndPosMatch": same_pos, "unknownToLexicon": unknown, "dictionary": dicts,
            "matchPct": round(same / total * 1000) / 10, "failPct": round((total - same) / total * 1000) / 10,
            "benchmark": "over about 1 percent of headwords failing to normalize to themselves means the lemmatizer or the VESUM version is mismatched",
            "failures": failures[:60]}


def load_lt_tables(lt_dir):
    """LanguageTool's Ukrainian replacement tables (VESUM's russianism register
    on the wire): word=suggestion1|suggestion2. Not vendored; read at snapshot
    time. Returns {flagged form: suggestions}."""
    out = {}
    for name in ("replace.txt", "replace_soft.txt"):
        path = os.path.join(lt_dir, name)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            left, right = line.split("=", 1)
            left = left.strip().lower()
            if " " in left:
                continue
            out.setdefault(left, right.split("#")[0].strip())
    return out


def russianism_gate(sentences_by_lemma, lt_dir):
    """The gate every published string passes: a token (or its lemma) in the
    LanguageTool replacement tables fails it; a token the lexicon does not
    know is counted as out-of-vocabulary (reported, not fatal, because names
    and rare inflections are legitimately unknown). Returns the surviving
    sentences and the report."""
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer(lang="uk")
    tables = load_lt_tables(lt_dir) if lt_dir else {}
    kept = {}
    report = {"tablesLoaded": len(tables), "sentencesChecked": 0, "sentencesDropped": 0, "flaggedHits": 0, "oovTokens": 0, "tokensChecked": 0, "dropped": []}
    for lem, sents in sentences_by_lemma.items():
        for s in sents:
            report["sentencesChecked"] += 1
            hit = None
            for tok in re.findall(r"[А-ЯІЇЄҐа-яіїєґ'ʼ’-]+", s):
                t = tok.lower().replace("’", "'").replace("ʼ", "'")
                if len(t) < 3:
                    continue
                report["tokensChecked"] += 1
                parses = morph.parse(t)
                lemma = parses[0].normal_form if parses else t
                # Homograph guards: a capitalized token is a name or a sentence
                # start (Сходу is the genitive of Схід, not the adverb сходу),
                # and a function-word reading (вона the pronoun) outranks the
                # table's dialect interjection of the same spelling.
                if tok[0].isupper():
                    continue
                if any(p.is_known and p.tag.POS in ("NPRO", "PREP", "CONJ", "PRCL") for p in parses):
                    continue
                if t in tables or lemma in tables:
                    hit = (tok, tables.get(t) or tables.get(lemma))
                    report["flaggedHits"] += 1
                    break
                if not any(p.is_known for p in parses):
                    report["oovTokens"] += 1
            if hit:
                report["sentencesDropped"] += 1
                if len(report["dropped"]) < 40:
                    report["dropped"].append({"lemma": lem, "token": hit[0], "suggestion": hit[1]})
            else:
                kept.setdefault(lem, []).append(s)
    return kept, report


def make_snapshot(parsed_path, by_lemma, verbs, lt_dir=None):
    p = json.load(open(parsed_path, encoding="utf-8"))
    b1 = set(by_lemma)
    gov = [g for g in p["gov"] if g[0] in verbs]
    verb_tot = {v: n for v, n in p["verbTot"].items() if v in verbs}
    per = {}
    for rel, hl, hp, cl, cp, n in p["pairs"]:
        if rel not in RELATIONS:
            continue
        if hl in b1:
            per.setdefault(hl, []).append([rel, hl, hp, cl, cp, n])
        if cl in b1 and cl != hl:
            per.setdefault(cl, []).append([rel, hl, hp, cl, cp, n])
    pairs = []
    for lem, rows in per.items():
        rows.sort(key=lambda x: -x[5])
        pairs.extend(rows[:PAIRS_KEPT])
    need = set()
    for rel, hl, hp, cl, cp, n in pairs:
        need.add((hl, hp))
        need.add((cl, cp))
    uni = {f"{l}\t{pos}": n for l, pos, n in p["uni"] if (l, pos) in need}
    examples = {}
    for lem, sents in p["examples"].items():
        if lem not in b1:
            continue
        keep = []
        for s in sents:
            s = clean_sentence(s)
            if 30 <= len(s) <= MAX_EXAMPLE_CHARS and not re.search(r"[|{}\[\]=]", s):
                keep.append(s)
            if len(keep) >= EXAMPLES_PER_LEMMA + 2:
                break
        if keep:
            examples[lem] = keep
    # Every published string passes the russianism gate; what it drops is counted.
    examples, gate = russianism_gate(examples, lt_dir)
    examples = {lem: sents[:EXAMPLES_PER_LEMMA] for lem, sents in examples.items()}
    # The lemmatizer convention check the plan requires: the join keys are the
    # PULS headwords (VESUM convention). The parser's lemmas come from pymorphy3,
    # whose Ukrainian dictionary is VESUM-derived, so the question is whether
    # the parser's normal form of each B1 headword IS that headword. The
    # dossier's benchmark: over about 1 percent failing means a mismatch.
    lemmatizer = lemmatizer_check(by_lemma)
    snap = {
        "source": "UberText 2.0, Wikipedia subcorpus (lang-uk), a 400000-line prefix parsed with spaCy uk_core_news_sm 3.8.0",
        "lemmatizerCheck": lemmatizer,
        "russianismGate": gate,
        "sourceUrl": "https://lang.org.ua/en/ubertext/",
        "textLicense": "CC-BY-SA (Wikipedia text; examples are kept verbatim)",
        "snapshot": SNAPSHOT_DATE,
        "parser": "spaCy uk_core_news_sm 3.8.0 (UD Ukrainian-IU; pymorphy3 lemmas)",
        "stats": p["stats"],
        "gov": gov,
        "verbTot": verb_tot,
        "pairs": pairs,
        "uni": uni,
        "examples": examples,
    }
    with open(os.path.join(DATA, "b1-usage.snapshot.json"), "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    return snap


def build(snap, rows, by_lemma, verbs):
    # ---- government
    per_verb = {}
    for v, prep, case, dep, n in snap["gov"]:
        d = per_verb.setdefault(v, {})
        key = (PREP_VARIANT.get(prep, prep), case)
        e = d.setdefault(key, {"n": 0, "deps": {}})
        e["n"] += n
        e["deps"][dep] = e["deps"].get(dep, 0) + n
    government = []
    gov_verbs = 0
    for v, rank in sorted(verbs.items(), key=lambda kv: kv[1]):
        total = sum(e["n"] for e in per_verb.get(v, {}).values())
        if total < GOV_MIN_TOTAL:
            continue
        gov_verbs += 1
        pats = sorted(per_verb[v].items(), key=lambda kv: -kv[1]["n"])
        for (prep, case), e in pats:
            share = r_half_up(e["n"] / total, 3)
            government.append({"verb": v, "rank": rank, "total": total, "prep": prep, "case": case,
                               "n": e["n"], "share": share, "shown": share >= SHOW_SHARE and e["n"] >= SHOW_MIN,
                               "deps": e["deps"]})
    # the reference check
    ref_rows = []
    for verb, expected in REFERENCE:
        exp = [list(e) for e in expected]
        if verb not in verbs:
            ref_rows.append({"verb": verb, "expected": exp, "inB1": False, "verdict": "not-b1"})
            continue
        pats = [g for g in government if g["verb"] == verb]
        if not pats:
            ref_rows.append({"verb": verb, "expected": exp, "inB1": True, "verdict": "too-few-observations", "total": sum(e["n"] for e in per_verb.get(verb, {}).values())})
            continue
        top = pats[:2]
        found = next((g for g in pats if [g["prep"], g["case"]] in exp), None)
        verdict = "top" if [pats[0]["prep"], pats[0]["case"]] in exp else ("top2" if found in top else ("present" if found else "absent"))
        ref_rows.append({"verb": verb, "expected": exp, "inB1": True, "verdict": verdict, "total": pats[0]["total"],
                         "found": [found["prep"], found["case"], found["n"], found["share"]] if found else None,
                         "top": [pats[0]["prep"], pats[0]["case"], pats[0]["n"], pats[0]["share"]]})
    ref_eval = [r for r in ref_rows if r["verdict"] in ("top", "top2", "present", "absent")]
    ref_summary = {
        "listed": len(REFERENCE),
        "inB1": sum(1 for r in ref_rows if r["inB1"]),
        "evaluated": len(ref_eval),
        "top": sum(1 for r in ref_eval if r["verdict"] == "top"),
        "top2": sum(1 for r in ref_eval if r["verdict"] in ("top", "top2")),
        "present": sum(1 for r in ref_eval if r["verdict"] in ("top", "top2", "present")),
        "absent": sum(1 for r in ref_eval if r["verdict"] == "absent"),
    }
    ref_summary["topPct"] = round(ref_summary["top"] / ref_summary["evaluated"] * 1000) / 10 if ref_eval else 0
    ref_summary["top2Pct"] = round(ref_summary["top2"] / ref_summary["evaluated"] * 1000) / 10 if ref_eval else 0

    # ---- collocations
    uni = snap["uni"]
    per_lemma = {}
    for rel, hl, hp, cl, cp, n in snap["pairs"]:
        if n < PAIR_MIN or not (CYR.search(hl) and CYR.search(cl)):  # no numerals or stray Latin tokens
            continue
        fx = uni.get(f"{hl}\t{hp}", n)
        fy = uni.get(f"{cl}\t{cp}", n)
        ld = logdice(n, fx, fy)
        for anchor, other, opos, side in ((hl, cl, cp, "head"), (cl, hl, hp, "child")):
            if anchor in by_lemma and anchor != other:
                per_lemma.setdefault(anchor, []).append({"lemma": anchor, "rel": rel, "relLabel": RELATIONS[rel], "side": side,
                                                         "other": other, "otherPos": opos, "n": n, "logDice": ld})
    collocations = []
    for lem in sorted(per_lemma, key=lambda l: by_lemma[l][0]["rank"]):
        rows_ = per_lemma[lem]
        seen = set()
        uniq = []
        for r in sorted(rows_, key=lambda x: -x["logDice"]):
            k = (r["rel"], r["other"], r["side"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        collocations.extend(uniq[:PAIRS_PER_LEMMA])

    # ---- examples
    examples = snap["examples"]

    st = snap["stats"]
    meta = {
        "snapshot": SNAPSHOT_DATE,
        "source": snap["source"], "sourceUrl": snap["sourceUrl"], "textLicense": snap["textLicense"], "parser": snap["parser"],
        "corpus": {"sentences": st["sentences"], "tokens": st["tokens"], "contentTokens": st["content"],
                   "contentOnList": st["content_on_list"], "contentOnListPct": round(st["content_on_list"] / st["content"] * 1000) / 10,
                   "contentOnListPosPct": round(st["content_on_list_pos"] / st["content"] * 1000) / 10},
        "thresholds": {"showShare": SHOW_SHARE, "showMin": SHOW_MIN, "govMinTotal": GOV_MIN_TOTAL, "pairMin": PAIR_MIN, "pairsPerLemma": PAIRS_PER_LEMMA},
        "lemmatizerCheck": snap.get("lemmatizerCheck"),
        "russianismGate": snap.get("russianismGate"),
        "b1Lemmas": len(by_lemma), "b1Verbs": len(verbs),
        "government": {"verbs": gov_verbs, "verbsWith20": sum(1 for v in verbs if sum(e["n"] for e in per_verb.get(v, {}).values()) >= 20),
                       "verbsZero": sum(1 for v in verbs if v not in per_verb), "patterns": len(government),
                       "shown": sum(1 for g in government if g["shown"])},
        "referenceCheck": ref_summary,
        "referenceNote": "A maintainer-written list of textbook government for 50 verbs, not an independent annotator. It estimates how often the parser's top pattern matches the textbook one; it is not a gold standard.",
        "collocations": {"lemmas": len(per_lemma), "rows": len(collocations)},
        "examples": {"lemmas": len(examples), "sentences": sum(len(v) for v in examples.values()),
                     "b1LemmasWithout": len([l for l in by_lemma if l not in examples])},
        "downloads": {"government": "/downloads/ukrainian-frequency/b1-extension/government.csv",
                      "collocations": "/downloads/ukrainian-frequency/b1-extension/collocations.csv",
                      "examples": "/downloads/ukrainian-frequency/b1-extension/examples.csv"},
    }
    full = dict(meta)
    full["governmentRows"] = government
    full["referenceRows"] = ref_rows
    full["collocationRows"] = collocations
    full["exampleRows"] = examples
    return full


def write_outputs(full, by_lemma):
    # The example sentences live in the snapshot and the public CSV; the derived
    # JSON does not duplicate them.
    derived = {k: v for k, v in full.items() if k != "exampleRows"}
    with open(os.path.join(DATA, "b1-usage.json"), "w", encoding="utf-8") as fh:
        json.dump(derived, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    os.makedirs(DL, exist_ok=True)
    with open(os.path.join(DL, "government.csv"), "w", encoding="utf-8") as fh:
        fh.write("verb,rank,total_dependents,preposition,case,n,share,shown\n")
        for g in full["governmentRows"]:
            fh.write(f"{g['verb']},{g['rank']},{g['total']},{g['prep']},{g['case']},{g['n']},{g['share']},{'yes' if g['shown'] else 'no'}\n")
    with open(os.path.join(DL, "collocations.csv"), "w", encoding="utf-8") as fh:
        fh.write("lemma,relation,side,collocate,collocate_pos,n,logdice\n")
        for c in full["collocationRows"]:
            fh.write(f"{c['lemma']},{c['rel']},{c['side']},{c['other']},{c['otherPos']},{c['n']},{c['logDice']}\n")
    with open(os.path.join(DL, "examples.csv"), "w", encoding="utf-8") as fh:
        fh.write("lemma,rank,sentence\n")
        for lem, sents in full["exampleRows"].items():
            rank = by_lemma[lem][0]["rank"]
            for s in sents:
                fh.write(f"{lem},{rank},\"{s.replace(chr(34), chr(34) * 2)}\"\n")

    # browser tier: aggregates, the reference rows, and a sample of each product
    sample_verbs = []
    seen = set()
    for g in full["governmentRows"]:
        if g["verb"] in seen or not g["shown"]:
            continue
        seen.add(g["verb"])
        if len(seen) > 12:
            break
        sample_verbs.append(g["verb"])
    gov_sample = [{k: g[k] for k in ("verb", "rank", "total", "prep", "case", "n", "share", "shown")} for g in full["governmentRows"] if g["verb"] in sample_verbs]
    coll_lemmas = []
    for c in full["collocationRows"]:
        if c["lemma"] not in coll_lemmas:
            coll_lemmas.append(c["lemma"])
        if len(coll_lemmas) >= 10:
            break
    coll_sample = [c for c in full["collocationRows"] if c["lemma"] in coll_lemmas]
    ex_sample = {}
    seen_sentences = set()
    for lem, sents in full["exampleRows"].items():
        fresh = [x for x in sents if x not in seen_sentences]
        if not fresh:
            continue
        ex_sample[lem] = fresh[:2]
        seen_sentences.update(fresh[:2])
        if len(ex_sample) >= 10:
            break
    slim = {k: v for k, v in full.items() if k not in ("governmentRows", "referenceRows", "collocationRows", "exampleRows")}
    slim["referenceRows"] = full["referenceRows"]
    slim["governmentSample"] = gov_sample
    slim["collocationSample"] = coll_sample
    slim["exampleSample"] = ex_sample
    slim["cases"] = CASES
    slim["relations"] = RELATIONS
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-b1-usage.py - do not edit by hand.\n"
        "// Browser-safe tier of the B1 extension's USAGE layer (stage 3): case government as\n"
        "// counts, dependency-linked collocations ranked by logDice, and attested Wikipedia\n"
        "// example sentences for the validated B1 set, all aggregated over a parsed prefix of\n"
        "// UberText 2.0's Wikipedia subcorpus. The full tables are\n"
        "// src/data/ukrainian-frequency/b1-usage.json and the public CSVs.\n"
        "export const B1_USAGE = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(LIB, "b1-usage.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--parsed", help="parse-b1-corpus.py output (needed with --snapshot)")
    ap.add_argument("--lt-dir", help="directory holding LanguageTool's uk replace.txt and replace_soft.txt (the russianism gate; with --snapshot)")
    ap.add_argument("--recheck-lemmatizer", action="store_true",
                    help="no corpus: re-run only the lemmatizer convention check over the CURRENT B1 set (pymorphy3) and "
                         "write it back into the committed snapshot; the corpus slice itself is left as cut")
    args = ap.parse_args()
    rows, by_lemma, verbs = load_b1()
    if args.snapshot:
        snap = make_snapshot(args.parsed, by_lemma, verbs, args.lt_dir)
    else:
        snap = json.load(open(os.path.join(DATA, "b1-usage.snapshot.json"), encoding="utf-8"))
        if args.recheck_lemmatizer:
            # The check is a property of the B1 headword set, not of the corpus
            # slice, so it can move when the validated overlay does.
            snap["lemmatizerCheck"] = lemmatizer_check(by_lemma)
            with open(os.path.join(DATA, "b1-usage.snapshot.json"), "w", encoding="utf-8") as fh:
                json.dump(snap, fh, ensure_ascii=False, indent=0)
                fh.write("\n")
    full = build(snap, rows, by_lemma, verbs)
    write_outputs(full, by_lemma)
    print(f"corpus: {full['corpus']}")
    print(f"government: {full['government']}; reference check: {full['referenceCheck']}")
    print(f"collocations: {full['collocations']}; examples: {full['examples']}")


if __name__ == "__main__":
    main()
