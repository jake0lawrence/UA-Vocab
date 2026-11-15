#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 4: the GAP-FILL MODEL.
#
# Predicted CEFR levels for the lemmas on thread 01's list that the validated
# PULS map does not cover, trained on the 6,207 validated labels and evaluated
# on held-out folds of them. Two rules the page and the release hold:
#
#   1. Predictions ship in a SEPARATE file (predicted-cefr/), never merged into
#      the validated level field. The validated CC-BY-SA list stays clean.
#   2. Every headline metric re-derives from the committed per-lemma held-out
#      file and the committed confusion matrix; CI checks the sums.
#
# Design (Pintard and Francois 2020 as the template; the 2026 Kazakh lexicon as
# the morphologically-rich reality check; first Ukrainian instance):
#
#   Two stages. Stage A, the out-of-scope gate, is a RULE here, not a learned
#   classifier, because no out-of-scope labels exist to learn from: PULS labels
#   no proper nouns and stops at C1, so unlabeled PROPN lemmas, non-lexical parts
#   of speech, and lemmas the lexicon does not know are classed out of scope and
#   kept off the ordinal scale. Stage B is the ordinal model over A1..C1.
#
#   Models. Primary: proportional-odds ORDINAL LOGISTIC regression (a cumulative
#   link model, pure numpy). Challenger: multinomial logistic regression.
#   Baseline models: ridge regression on the level index with fitted cut points
#   (regression-then-threshold), and a frequency-only ordinal logit (the
#   "onset of use" rule adapted to native frequency: does the model beat "just
#   use frequency"?). Naive baselines: majority class, and the modal validated
#   level of the lemma's thousand-rank band.
#
#   Features, ranked as the design ranks them: log frequency and log document
#   frequency (Laplace-smoothed), dispersion as documents per occurrence (Gries
#   DP across the five subcorpora needs the subcorpus counts, which the shipped
#   dictionary does not carry; stated, not faked), rank band, the derivational
#   family's lowest validated level (stem-mates, fold-safe), the aspect
#   partner's validated level (Wiktionary link, fold-safe), part of speech,
#   length, syllables, suffix and prefix indicators, reflexive and apostrophe
#   flags, and whether the lexicon (VESUM via pymorphy3) knows the lemma. Plus
#   the open resources the feature inventory found buildable now: Wiktionary
#   sense count (polysemy) and a borrowed-term flag (kaikki.org), subtitle-and-
#   web frequency (wordfreq, Zipf scale), the UniMorph 4.0 derivational family
#   (size, membership), and the Wiktionary derived-term family (size,
#   membership, and the family's lowest validated level computed fold-safe
#   from the training rows; extract-wiktionary-families.py). An LLM judgment
#   is reserved as at most one measured feature and is NOT in this version;
#   the slot is documented, not filled.
#
#   EXCLUDED on purpose (2026-09-13): membership in the two open A1 / A2
#   lexical minima (Borodin et al.). Until this date the shipped model carried
#   both flags and they were its two strongest weights, worth about nine
#   points of exact match. That lift was a readback of a graded word list,
#   not a prediction from frequency and form: the flags fire on 812 of the
#   labels (600 of the 823 validated A1 words) but on 56 of the 4,251 lemmas
#   the model exists to predict, and whether the Borodin volumes sit among
#   the textbooks the profile was validated on could not be established. The
#   columns are still computed so the run can REPORT what they would add
#   (`excludedFeatures` in the metadata, a labeled diagnostic), and they are
#   never in the shipped model, the ladder or the headline figures.
#
#   Splitting. GROUP-AWARE stratified folds: lemmas that share a lemma string,
#   a derivational stem, an aspect-pair link, a UniMorph family or a Wiktionary
#   family are one group and never straddle train and test. The same models are also scored under plain stratified
#   random folds, and the gap is reported: if grouped scores collapse relative
#   to random ones, leakage was the story.
#
#   Ablation ladder under grouped folds, primary model: A frequency only;
#   B + dispersion; C + morphology (family, partner, affixes, reflexive);
#   D + part of speech and length; E + lexicon flags and band; then one step
#   per open resource, F through J, the last being the Wiktionary family.
#
#   Metrics: exact match, within one level, macro-F1, MAE, quadratic weighted
#   kappa, Spearman. Calibration of the shipped probabilities: expected
#   calibration error with a reliability table, an accuracy-against-coverage
#   curve, and the abstention threshold chosen from it. MNAR and censoring:
#   the label-presence rate per rank band and held-out accuracy per band, so a
#   tail prediction ships flagged as thin support.
#
# Two modes, same posture as the other extractors:
#   --snapshot --kaikki FILE   read the Wiktionary verb dump (or the filtered
#                              verb file) for aspect partners of every list
#                              verb, and the lexicon for every list lemma;
#                              commit the slice (predicted-cefr.snapshot.json)
#   (default)                  train, evaluate, predict from the snapshot
#
# House rule: no em-dashes.
# ---------------------------------------------------------------------------

import argparse
import json
import math
import os
import re
import unicodedata

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
LIB = os.path.join(ROOT, "src", "lib", "ukrainian-frequency")
DL = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "predicted-cefr")

SNAPSHOT_DATE = "2026-09-23"
SEED = 20260911
FOLDS = 5
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
LEVEL_IDX = {l: i for i, l in enumerate(LEVELS)}
CONTENT_POS = ["NOUN", "VERB", "ADJ", "ADV"]
NONLEXICAL = {"ADP", "CCONJ", "SCONJ", "PART", "PRON", "DET", "NUM", "INTJ", "AUX", "X", "SYM", "PUNCT"}
STEM_LEN = 5
THIN_SUPPORT_BELOW = 0.35   # label-presence rate per band under which a prediction is flagged thin support
ABSTAIN_TARGET = 0.5        # the abstention threshold is the lowest one whose confident held-out exact accuracy reaches this (a coin flip on five classes)
THRESHOLDS = [0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8]
SUFFIXES = ["ння", "ття", "ість", "ство", "цтво", "ція", "зія", "изм", "ізм", "ник", "чик", "тель", "ач", "яч",
            "ець", "ка", "иця", "ина", "ок", "ик", "льник", "ізувати", "изувати", "увати", "ювати", "ити", "іти", "ати", "яти", "ти",
            "ся", "ський", "цький", "ичний", "ічний", "ний", "овий", "евий", "ливий", "истий", "уватий", "о", "ично", "ічно"]
PREFIXES = ["без", "від", "ви", "до", "за", "з", "на", "над", "не", "о", "об", "пере", "перед", "під", "по", "при", "про", "роз", "с", "у", "спів", "між", "анти", "супер"]
VOWELS = set("аеиіоуюяєї")
MODELS = ["majority", "rankOnly", "freqOnly", "ridgeThreshold", "ordinalLogit", "softmax"]


def norm(s):
    return unicodedata.normalize("NFC", "".join(ch for ch in unicodedata.normalize("NFD", s) if ch != "́")).replace("’", "'").replace("ʼ", "'").strip().lower()


# ---------------------------------------------------------------- snapshot
def read_partners(stream, verbs):
    out = {}
    for line in stream:
        if '"pos"' in line and '"verb"' not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if "lang_code" in e and (e.get("lang_code") != "uk" or e.get("pos") != "verb"):
            continue
        w = norm(e.get("word", ""))
        if w not in verbs:
            continue
        parts = set()
        for f in e.get("forms", []):
            tags = f.get("tags", [])
            if f.get("source") == "conjugation" or f.get("form") in ("", "-"):
                continue
            if tags == ["perfective"] or tags == ["imperfective"]:
                for one in re.split(r"[,;/]", re.sub(r"<[^>]*>", "", f["form"])):
                    if norm(one) and norm(one) != w:
                        parts.add(norm(one))
        for h in e.get("head_templates") or [{"args": a} for a in e.get("heads", [])]:
            args = h.get("args", {})
            for k in ("pf", "pf2", "pf3", "impf", "impf2", "impf3"):
                v = args.get(k)
                if v:
                    for one in re.split(r"[,;/]", re.sub(r"<[^>]*>", "", v.replace("[[", "").replace("]]", ""))):
                        if norm(one) and norm(one) != w:
                            parts.add(norm(one))
        if parts:
            out.setdefault(w, set()).update(parts)
    return {k: sorted(v) for k, v in out.items()}


def lexicon(lemmas_pos):
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer(lang="uk")
    fam = {"NOUN": {"NOUN"}, "PROPN": {"NOUN"}, "VERB": {"VERB", "INFN"}, "ADJ": {"ADJF", "ADJS", "COMP"}, "ADV": {"ADVB"},
           "NUM": {"NUMR"}, "PRON": {"NPRO"}, "ADP": {"PREP"}, "CCONJ": {"CONJ"}, "SCONJ": {"CONJ"}, "PART": {"PRCL"}, "INTJ": {"INTJ"}}
    out = {}
    for lemma, pos in lemmas_pos:
        parses = [p for p in morph.parse(lemma) if p.is_known]
        known = bool(parses)
        same = any(p.normal_form == lemma for p in parses)
        pos_ok = any(p.normal_form == lemma and (p.tag.POS in fam.get(pos, set()) or pos not in fam) for p in parses)
        out[f"{lemma}\t{pos}"] = [int(known), int(same), int(pos_ok)]
    return out


def unimorph_families(path):
    """Union-find over UniMorph 4.0 derivation edges (source, target); returns
    lemma -> family id, stress stripped."""
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        a, b = norm(parts[0]), norm(parts[1])
        if not a or not b:
            continue
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    fam = {w: find(w) for w in list(parent)}
    return fam


KAIKKI_POS = {"NOUN": {"noun"}, "PROPN": {"name", "noun"}, "VERB": {"verb"}, "ADJ": {"adj"}, "ADV": {"adv"}, "NUM": {"num"}, "PRON": {"pron"},
              "ADP": {"prep"}, "CCONJ": {"conj"}, "SCONJ": {"conj"}, "PART": {"particle"}, "INTJ": {"intj"}, "DET": {"det"}}


def wiktionary_families(path):
    """rank -> (family id, family size) from the Wiktionary derived-term family
    graph (extract-wiktionary-families.py). Keyed by rank because the graph
    joins list members by rank, so homographs stay apart."""
    if not path:
        return {}
    graph = json.load(open(path, encoding="utf-8"))
    out = {}
    for f in graph["families"]:
        for m in f["listMembers"]:
            out[m["rank"]] = (f["id"], f["size"])
    return out


def resources(rows, kaikki_path, unimorph_path, wikt_families_path=None):
    """The open feature resources, per list lemma: Wiktionary senses and borrowed
    flag, wordfreq Zipf frequency, UniMorph family, the Wiktionary derived-term
    family, A1 / A2 list membership."""
    from wordfreq import zipf_frequency
    # accepts the raw kaikki jsonl (senses and categories as lists) as well as
    # the slimmed form an earlier run used (senses as a count, cats as names)
    def slim(e):
        senses = e.get("senses", 0)
        cats = e.get("cats")
        if cats is None:
            cats = [c.get("name", "") if isinstance(c, dict) else str(c) for c in e.get("categories", [])]
            if isinstance(senses, list):
                for s in senses:
                    cats += [c.get("name", "") if isinstance(c, dict) else str(c) for c in s.get("categories", [])]
        return {"word": e["word"], "pos": e.get("pos"), "senses": len(senses) if isinstance(senses, list) else int(senses or 0), "cats": cats}
    entries = {}
    for line in open(kaikki_path, encoding="utf-8"):
        e = slim(json.loads(line))
        # the same key the list lemmas are looked up by (apostrophe glyph and case folded)
        entries.setdefault(norm(e["word"]), []).append(e)
    fam = unimorph_families(unimorph_path)
    wfam = wiktionary_families(wikt_families_path)
    fam_size = {}
    for w, f in fam.items():
        fam_size[f] = fam_size.get(f, 0) + 1
    a1 = {norm(r["lemma"]) for r in json.load(open(os.path.join(DATA, "borodin-a1.json"), encoding="utf-8"))["rows"] if r.get("matched") and r.get("lemma")}
    a2 = {norm(r["lemma"]) for r in json.load(open(os.path.join(DATA, "borodin-a2.json"), encoding="utf-8"))["rows"] if r.get("matched") and r.get("lemma")}
    out = {}
    for r in rows:
        lemma = norm(r["lemma"])
        pos = r["pos"]
        ents = entries.get(lemma, [])
        match = [e for e in ents if e.get("pos") in KAIKKI_POS.get(pos, set())] or ents
        senses = sum(e["senses"] for e in match)
        borrowed = int(any(any("borrowed" in c.lower() for c in e["cats"]) for e in match))
        f = fam.get(lemma)
        wf, wsize = wfam.get(r["rank"], (None, 0))
        out[f"{lemma}\t{pos}"] = {"zipf": round(zipf_frequency(lemma, "uk"), 2), "senses": senses, "wikt": int(bool(ents)), "borrowed": borrowed,
                                   "family": f, "familySize": fam_size.get(f, 0) if f else 0, "wfamily": wf, "wfamilySize": wsize,
                                   "a1": int(lemma in a1), "a2": int(lemma in a2)}
    return out


# ---------------------------------------------------------------- features
def syllables(w):
    return sum(1 for ch in w if ch in VOWELS)


# No document-count feature since list v0.2.0: the source's doc_count exceeded
# the row's own count in a fifth of the rows and was defined nowhere upstream,
# so the list stopped carrying it and the model stopped reading it (the old
# logDocs and dispersion columns, and the "+ dispersion" ablation step).
BASE_NAMES = ["logCount", "logRank", "band", "length", "syllables", "lexKnown", "lexSameLemma", "lexPosOk",
              "hasApostrophe", "isReflexive", "familyMinLevel", "familyHasLabel", "partnerLevel", "partnerHasLabel"]


def feature_names():
    names = list(BASE_NAMES)
    names += [f"pos={p}" for p in CONTENT_POS + ["PROPN", "OTHER"]]
    names += [f"suffix={s}" for s in SUFFIXES]
    names += [f"prefix={p}" for p in PREFIXES]
    return names


RESOURCE_NAMES = ["zipf", "logSenses", "hasWiktionary", "borrowed", "unimorphFamilySize", "hasUnimorphFamily", "inA1List", "inA2List",
                  "wiktFamilySize", "hasWiktFamily", "wiktFamilyMinLevel", "wiktFamilyHasLabel"]
# Computed, reported, never shipped (see the header).
EXCLUDED_NAMES = ["inA1List", "inA2List"]
EXCLUDED_WHY = ("membership in the open A1 / A2 lexical minima (Borodin et al.): a graded word list read back as a feature; "
                "fires on most validated A1 labels and on almost none of the lemmas being predicted, and its independence "
                "from the profile's textbook base is not established")


def feature_names_all():
    return feature_names() + RESOURCE_NAMES


NAMES_CORE = feature_names()
NAMES = feature_names_all()  # the full matrix, excluded columns included
SHIPPED_NAMES = [n for n in NAMES if n not in EXCLUDED_NAMES]
SHIPPED_IDX = [NAMES.index(n) for n in SHIPPED_NAMES]
NAMES_THROUGH_H = NAMES_CORE + ["zipf", "logSenses", "hasWiktionary", "borrowed", "unimorphFamilySize", "hasUnimorphFamily"]
ABLATIONS = [
    ("A frequency only", ["logCount"]),
    ("B + morphology", ["logCount", "familyMinLevel", "familyHasLabel", "partnerLevel", "partnerHasLabel", "isReflexive", "hasApostrophe", "syllables"]
     + [n for n in NAMES if n.startswith("suffix=") or n.startswith("prefix=")]),
    ("C + part of speech and length", ["logCount", "familyMinLevel", "familyHasLabel", "partnerLevel", "partnerHasLabel", "isReflexive", "hasApostrophe", "syllables", "length"]
     + [n for n in NAMES if n.startswith("suffix=") or n.startswith("prefix=") or n.startswith("pos=")]),
    ("D + lexicon flags and band", NAMES_CORE),
    ("E + Wiktionary polysemy and loanword flag", NAMES_CORE + ["logSenses", "hasWiktionary", "borrowed"]),
    ("F + subtitle and web frequency (wordfreq)", NAMES_CORE + ["logSenses", "hasWiktionary", "borrowed", "zipf"]),
    ("G + UniMorph derivational family", NAMES_CORE + ["logSenses", "hasWiktionary", "borrowed", "zipf", "unimorphFamilySize", "hasUnimorphFamily"]),
    ("H + Wiktionary derived-term family (size, fold-safe lowest level)", SHIPPED_NAMES),
]


def base_features(rows, lex, res=None):
    X = []
    res = res or {}
    for r in rows:
        lemma = norm(r["lemma"])
        pos = r["pos"]
        lx = lex.get(f"{lemma}\t{pos}", [0, 0, 0])
        rs = res.get(f"{lemma}\t{pos}", {})
        f = [math.log10(r["count"] + 1), math.log10(r["rank"]),
             (r["rank"] - 1) // 1000, len(lemma), syllables(lemma), lx[0], lx[1], lx[2],
             int("'" in lemma), int(lemma.endswith("ся") or lemma.endswith("сь")), 0, 0, 0, 0]
        f += [int(pos == p) for p in CONTENT_POS] + [int(pos == "PROPN"), int(pos not in CONTENT_POS and pos != "PROPN")]
        f += [int(lemma.endswith(s)) for s in SUFFIXES]
        f += [int(lemma.startswith(p) and len(lemma) > len(p) + 2) for p in PREFIXES]
        f += [rs.get("zipf", 0.0), math.log10(rs.get("senses", 0) + 1), rs.get("wikt", 0), rs.get("borrowed", 0),
              math.log10(rs.get("familySize", 0) + 1), int(bool(rs.get("family"))), rs.get("a1", 0), rs.get("a2", 0),
              math.log10(rs.get("wfamilySize", 0) + 1), int(bool(rs.get("wfamily"))), 0, 0]
        X.append(f)
    return np.array(X, dtype=float)


def wfamily_of(r, res):
    return (res or {}).get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("wfamily")


def label_features(X, rows, train_idx, y, partners, res=None):
    """Fold-safe: the stem-family, partner and Wiktionary-family levels use
    ONLY the training rows, and never the row's own label."""
    X = X.copy()
    wmin_col, whas_col = NAMES.index("wiktFamilyMinLevel"), NAMES.index("wiktFamilyHasLabel")
    level_of = {}
    stem_rows = {}
    wfam_rows = {}
    for i in train_idx:
        lemma = norm(rows[i]["lemma"])
        level_of[lemma] = min(level_of.get(lemma, 9), int(y[i]))
        if len(lemma) >= STEM_LEN:
            stem_rows.setdefault(lemma[:STEM_LEN], []).append((i, int(y[i])))
        wf = wfamily_of(rows[i], res)
        if wf:
            wfam_rows.setdefault(wf, []).append((i, int(y[i])))
    for i, r in enumerate(rows):
        lemma = norm(r["lemma"])
        st = lemma[:STEM_LEN]
        others = [lv for j, lv in stem_rows.get(st, []) if j != i] if len(lemma) >= STEM_LEN else []
        if others:
            X[i, 12] = min(others) + 1
            X[i, 13] = 1
        if r["pos"] == "VERB":
            lv = [level_of[p] for p in partners.get(lemma, []) if p in level_of]
            if lv:
                X[i, 14] = min(lv) + 1
                X[i, 15] = 1
        wf = wfamily_of(r, res)
        wothers = [lv for j, lv in wfam_rows.get(wf, []) if j != i] if wf else []
        if wothers:
            X[i, wmin_col] = min(wothers) + 1
            X[i, whas_col] = 1
    return X


# ---------------------------------------------------------------- groups + folds
def make_groups(rows, partners, res=None):
    """Union-find: same lemma string, same derivational stem, an aspect-pair
    link, the same UniMorph derivational family, or the same Wiktionary
    derived-term family puts two labeled rows in one group."""
    res = res or {}
    n = len(rows)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    by_lemma = {}
    by_stem = {}
    for i, r in enumerate(rows):
        lemma = norm(r["lemma"])
        by_lemma.setdefault(lemma, []).append(i)
        if len(lemma) >= STEM_LEN:
            by_stem.setdefault(lemma[:STEM_LEN], []).append(i)
    for idxs in list(by_lemma.values()) + list(by_stem.values()):
        for j in idxs[1:]:
            union(idxs[0], j)
    for i, r in enumerate(rows):
        if r["pos"] != "VERB":
            continue
        for p in partners.get(norm(r["lemma"]), []):
            for j in by_lemma.get(p, []):
                union(i, j)
    by_family = {}
    for i, r in enumerate(rows):
        f = res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("family")
        if f:
            by_family.setdefault(f, []).append(i)
        wf = wfamily_of(r, res)
        if wf:
            by_family.setdefault(f"wikt:{wf}", []).append(i)
    for idxs in by_family.values():
        for j in idxs[1:]:
            union(idxs[0], j)
    return np.array([find(i) for i in range(n)])


def grouped_folds(groups, y, rng):
    """Whole groups go to one fold; groups are dealt largest first to the fold
    that is currently lightest, so folds stay balanced and every level is
    spread (the stratification is approximate, and reported)."""
    fold_of = np.zeros(len(y), dtype=int)
    members = {}
    for i, g in enumerate(groups):
        members.setdefault(g, []).append(i)
    order = sorted(members.values(), key=lambda m: (-len(m), rng.rand()))
    load = np.zeros(FOLDS)
    for m in order:
        f = int(load.argmin())
        for i in m:
            fold_of[i] = f
        load[f] += len(m)
    return fold_of


def random_folds(y, rng):
    fold_of = np.zeros(len(y), dtype=int)
    for k in range(len(LEVELS)):
        idx = np.where(y == k)[0]
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            fold_of[i] = j % FOLDS
    return fold_of


# ---------------------------------------------------------------- models
def standardize(Xtr, Xte):
    mu = Xtr.mean(0)
    sd = Xtr.std(0)
    sd[sd == 0] = 1
    return (Xtr - mu) / sd, (Xte - mu) / sd


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_ordinal_logit(X, y, K=5, l2=1e-2, iters=3000, lr=0.05):
    """Proportional-odds cumulative link model. P(y <= k) = sigmoid(theta_k - x.w),
    thresholds kept ordered through theta_k = theta_0 + cumsum(exp(delta))."""
    n, d = X.shape
    w = np.zeros(d)
    theta0 = 0.0
    delta = np.zeros(K - 2)
    Y = y.astype(int)
    for _ in range(iters):
        thetas = theta0 + np.concatenate([[0.0], np.cumsum(np.exp(delta))])  # K-1 thresholds
        eta = X @ w
        # cumulative probabilities at each threshold, with F(-inf)=0 and F(+inf)=1
        F = sigmoid(thetas[None, :] - eta[:, None])                            # n x (K-1)
        Fpad = np.hstack([np.zeros((n, 1)), F, np.ones((n, 1))])              # n x (K+1)
        p = Fpad[np.arange(n), Y + 1] - Fpad[np.arange(n), Y]                  # P(y = k)
        p = np.maximum(p, 1e-12)
        fpad = np.hstack([np.zeros((n, 1)), F * (1 - F), np.zeros((n, 1))])   # densities at thresholds
        f_hi = fpad[np.arange(n), Y + 1]
        f_lo = fpad[np.arange(n), Y]
        # d(-log p)/d eta = (f_hi - f_lo) / p ; eta = X w
        g_eta = (f_hi - f_lo) / p
        g_w = X.T @ g_eta / n + l2 * w
        # d(-log p)/d theta_j: -f_hi/p at j = Y (upper threshold), +f_lo/p at j = Y-1
        g_theta = np.zeros(K - 1)
        for k in range(K):
            mask = Y == k
            if k <= K - 2:
                g_theta[k] += (-f_hi[mask] / p[mask]).sum()
            if k >= 1:
                g_theta[k - 1] += (f_lo[mask] / p[mask]).sum()
        g_theta /= n
        g_theta0 = g_theta.sum()
        g_delta = np.array([g_theta[m + 1:].sum() * np.exp(delta[m]) for m in range(K - 2)])
        w -= lr * g_w
        theta0 -= lr * g_theta0
        delta -= lr * g_delta
    thetas = theta0 + np.concatenate([[0.0], np.cumsum(np.exp(delta))])
    return w, thetas


def predict_ordinal_logit(X, w, thetas):
    eta = X @ w
    F = sigmoid(thetas[None, :] - eta[:, None])
    Fpad = np.hstack([np.zeros((len(X), 1)), F, np.ones((len(X), 1))])
    P = np.diff(Fpad, axis=1)
    return P.argmax(1), P


def fit_ridge_threshold(X, y, lam=1.0):
    Xb = np.hstack([X, np.ones((len(X), 1))])
    A = Xb.T @ Xb + lam * np.eye(Xb.shape[1])
    A[-1, -1] -= lam
    w = np.linalg.solve(A, Xb.T @ y.astype(float))
    s = Xb @ w
    cuts = np.array([0.5, 1.5, 2.5, 3.5])
    grid = np.arange(-0.5, 4.5, 0.02)
    for _ in range(3):
        for k in range(4):
            best, best_acc = cuts[k], -1
            for c in grid:
                lo = cuts[k - 1] if k > 0 else -np.inf
                hi = cuts[k + 1] if k < 3 else np.inf
                if not (lo < c < hi):
                    continue
                trial = cuts.copy()
                trial[k] = c
                acc = (np.digitize(s, trial) == y).mean()
                if acc > best_acc:
                    best, best_acc = c, acc
            cuts[k] = best
    return w, cuts


def predict_ridge_threshold(X, w, cuts):
    s = np.hstack([X, np.ones((len(X), 1))]) @ w
    return np.digitize(s, cuts), s


def fit_softmax(X, y, K=5, l2=1e-3, iters=3000, lr=0.2):
    n, d = X.shape
    W = np.zeros((d, K))
    b = np.zeros(K)
    Y = np.eye(K)[y]
    for _ in range(iters):
        Z = X @ W + b
        Z -= Z.max(1, keepdims=True)
        P = np.exp(Z)
        P /= P.sum(1, keepdims=True)
        G = (P - Y) / n
        W -= lr * (X.T @ G + l2 * W)
        b -= lr * G.sum(0)
    return W, b


def predict_softmax(X, W, b):
    Z = X @ W + b
    Z -= Z.max(1, keepdims=True)
    P = np.exp(Z)
    P /= P.sum(1, keepdims=True)
    return P.argmax(1), P


# ---------------------------------------------------------------- metrics
def qwk(y, yhat, K=5):
    O = np.zeros((K, K))
    for a, p in zip(y, yhat):
        O[a, p] += 1
    W = np.array([[((i - j) ** 2) / ((K - 1) ** 2) for j in range(K)] for i in range(K)])
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    denom = (W * E).sum()
    return float(1 - (W * O).sum() / denom) if denom else 0.0


def spearman(a, b):
    def ranks(v):
        order = np.argsort(v, kind="stable")
        r = np.empty(len(v))
        i = 0
        sv = v[order]
        while i < len(v):
            j = i
            while j + 1 < len(v) and sv[j + 1] == sv[i]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(np.asarray(a, dtype=float)), ranks(np.asarray(b, dtype=float))
    ra -= ra.mean()
    rb -= rb.mean()
    d = math.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / d) if d else 0.0


def metrics(y, yhat):
    K = len(LEVELS)
    conf = np.zeros((K, K), dtype=int)
    for a, p in zip(y, yhat):
        conf[a, p] += 1
    f1s = []
    for k in range(K):
        tp = conf[k, k]
        fp = conf[:, k].sum() - tp
        fn = conf[k, :].sum() - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * p * r / (p + r) if p + r else 0.0)
    return {"exact": float((y == yhat).mean()), "within1": float((np.abs(y - yhat) <= 1).mean()), "macroF1": float(np.mean(f1s)),
            "perClassF1": [float(x) for x in f1s], "mae": float(np.abs(y - yhat).mean()), "qwk": qwk(y, yhat), "spearman": spearman(y, yhat),
            "confusion": conf.tolist()}


def r3(x):
    return round(float(x) * 1000) / 1000


def pct(x):
    return round(float(x) * 1000) / 10


# ---------------------------------------------------------------- the run
def run_cv(Xl, y, labeled, partners, fold_of, feature_idx=None, models=None, res=None):
    """Out-of-fold predictions for every model in `models` on the given folds."""
    models = models or MODELS
    oof = {m: np.zeros(len(y), dtype=int) for m in models}
    prob = {m: np.zeros((len(y), len(LEVELS))) for m in ("ordinalLogit", "softmax") if m in models}
    for f in range(FOLDS):
        tr = np.where(fold_of != f)[0]
        te = np.where(fold_of == f)[0]
        Xf = label_features(Xl, labeled, tr, y, partners, res)
        if feature_idx is not None:
            Xf = Xf[:, feature_idx]
        Xtr, Xte = standardize(Xf[tr], Xf[te])
        if "majority" in models:
            oof["majority"][te] = np.bincount(y[tr]).argmax()
        if "rankOnly" in models:
            band_mode = {}
            for i in tr:
                band_mode.setdefault(int(Xl[i, 4]), []).append(y[i])
            for i in te:
                oof["rankOnly"][i] = np.bincount(band_mode.get(int(Xl[i, 4]), [np.bincount(y[tr]).argmax()])).argmax()
        if "freqOnly" in models:
            col = Xl[:, [0]]
            a, b = standardize(col[tr], col[te])
            w, th = fit_ordinal_logit(a, y[tr])
            oof["freqOnly"][te], _ = predict_ordinal_logit(b, w, th)
        if "ridgeThreshold" in models:
            w, cuts = fit_ridge_threshold(Xtr, y[tr])
            oof["ridgeThreshold"][te], _ = predict_ridge_threshold(Xte, w, cuts)
        if "ordinalLogit" in models:
            w, th = fit_ordinal_logit(Xtr, y[tr])
            oof["ordinalLogit"][te], prob["ordinalLogit"][te] = predict_ordinal_logit(Xte, w, th)
        if "softmax" in models:
            W, b = fit_softmax(Xtr, y[tr])
            oof["softmax"][te], prob["softmax"][te] = predict_softmax(Xte, W, b)
    return oof, prob


def calibration(y, yhat, P, bins=10):
    conf = P.max(1)
    correct = (y == yhat).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    ece = 0.0
    for i in range(bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1]) if i else (conf >= edges[i]) & (conf <= edges[i + 1])
        if m.sum() == 0:
            continue
        acc = float(correct[m].mean())
        avg = float(conf[m].mean())
        ece += m.sum() / len(y) * abs(acc - avg)
        rows.append({"lo": round(float(edges[i]), 2), "hi": round(float(edges[i + 1]), 2), "n": int(m.sum()), "confidence": r3(avg), "accuracy": r3(acc)})
    coverage = []
    for t in THRESHOLDS:
        m = conf >= t
        coverage.append({"threshold": t, "coverage": r3(m.mean()), "accuracy": r3(correct[m].mean()) if m.sum() else None, "n": int(m.sum())})
    chosen = next((c["threshold"] for c in coverage if c["accuracy"] is not None and c["accuracy"] >= ABSTAIN_TARGET), None)
    return {"ece": r3(ece), "bins": rows, "coverage": coverage, "abstainTarget": ABSTAIN_TARGET, "abstainThreshold": chosen}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--kaikki", help="Wiktionary verb entries (aspect partners)")
    ap.add_argument("--kaikki-lemmas", help="Wiktionary entries for every list lemma (senses, etymology categories)")
    ap.add_argument("--unimorph", help="UniMorph 4.0 ukr.derivations")
    ap.add_argument("--wiktionary-families", default=os.path.join(DATA, "wiktionary-families.json"),
                    help="the Wiktionary derived-term family graph (extract-wiktionary-families.py)")
    args = ap.parse_args()

    seed = json.load(open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    puls = json.load(open(os.path.join(DATA, "puls-cefr.json"), encoding="utf-8"))
    rows = [dict(r, rank=i + 1) for i, r in enumerate(seed["rows"])]
    label_by_rank = {r["rank"]: r["level"] for r in puls["rows"] if r["level"] in LEVEL_IDX}
    snap_path = os.path.join(DATA, "predicted-cefr.snapshot.json")

    if args.snapshot:
        verbs = {norm(r["lemma"]) for r in rows if r["pos"] == "VERB"}
        partners = read_partners(open(args.kaikki, encoding="utf-8"), verbs)
        lex = lexicon([(norm(r["lemma"]), r["pos"]) for r in rows])
        res = resources(rows, args.kaikki_lemmas, args.unimorph, args.wiktionary_families)
        with open(snap_path, "w", encoding="utf-8") as fh:
            json.dump({"snapshot": SNAPSHOT_DATE,
                       "resourcesSource": "per list lemma: Wiktionary (kaikki.org, CC-BY-SA) sense count and 'borrowed' category flag; wordfreq Zipf frequency (subtitles, web, books; MIT/CC-BY-SA data); UniMorph 4.0 ukr.derivations family (union-find over edges; CC BY-NC 4.0 release, Wiktionary-derived, verify per file); the Wiktionary derived-term family (wiktionary-families.json: derived terms, single-base affix etymologies and aspect partners, compounds excluded; CC-BY-SA); Borodin A1 and A2 list membership (CC-BY-4.0)",
                       "resources": res,
                       "partnersSource": "Wiktionary via kaikki.org (wiktextract): headword-listed aspect partners of every VERB lemma on the list; CC-BY-SA-3.0",
                       "lexiconSource": "VESUM via pymorphy3 (pymorphy3-dicts-uk): [known, same lemma as normal form, POS agrees] per list lemma. Derived from VESUM; regenerable with --snapshot; not part of the public release",
                       "partners": partners, "lexicon": lex}, fh, ensure_ascii=False, indent=0)
            fh.write("\n")
        print(f"snapshot: partners for {len(partners)} verbs; lexicon for {len(lex)} lemmas")

    snap = json.load(open(snap_path, encoding="utf-8"))
    partners, lex, res = snap["partners"], snap["lexicon"], snap.get("resources", {})

    labeled = [r for r in rows if r["rank"] in label_by_rank]
    unlabeled = [r for r in rows if r["rank"] not in label_by_rank]
    y = np.array([LEVEL_IDX[label_by_rank[r["rank"]]] for r in labeled])
    Xl = base_features(labeled, lex, res)
    rng = np.random.RandomState(SEED)

    groups = make_groups(labeled, partners, res)
    fold_g = grouped_folds(groups, y, rng)
    fold_r = random_folds(y, np.random.RandomState(SEED + 1))
    n_groups = len(set(groups.tolist()))
    fold_sizes = [int((fold_g == f).sum()) for f in range(FOLDS)]
    fold_levels = [[int(((fold_g == f) & (y == k)).sum()) for k in range(len(LEVELS))] for f in range(FOLDS)]

    # grouped folds: every model, on the shipped feature set
    oof_g, prob_g = run_cv(Xl, y, labeled, partners, fold_g, feature_idx=SHIPPED_IDX, res=res)
    evaluation = {m: metrics(y, oof_g[m]) for m in MODELS}
    # random folds: the two candidate models, for the leakage comparison
    oof_r, _ = run_cv(Xl, y, labeled, partners, fold_r, feature_idx=SHIPPED_IDX, models=["ordinalLogit", "softmax"], res=res)
    # the excluded columns, measured and reported, never shipped: the primary
    # model on the same grouped folds with the two minima flags added back
    oof_x, _ = run_cv(Xl, y, labeled, partners, fold_g, feature_idx=None, models=["ordinalLogit"], res=res)
    with_excluded = metrics(y, oof_x["ordinalLogit"])
    evaluation_random = {m: {k: v for k, v in metrics(y, oof_r[m]).items() if k != "confusion"} for m in ("ordinalLogit", "softmax")}

    # The primary is the ordinal model; the challenger displaces it only by
    # winning the ordinal-distance metric (MAE), not by a tenth of a point of
    # exact match on a task where adjacent errors are the common case.
    shipped = "ordinalLogit" if evaluation["ordinalLogit"]["mae"] <= evaluation["softmax"]["mae"] else "softmax"
    challenger = "softmax" if shipped == "ordinalLogit" else "ordinalLogit"
    agree = float((oof_g["ordinalLogit"] == oof_g["softmax"]).mean())
    calib = calibration(y, oof_g[shipped], prob_g[shipped])
    abstain = calib["abstainThreshold"] if calib["abstainThreshold"] is not None else 0.45

    # ablation ladder, primary model, grouped folds
    ablation = []
    for name, feats in ABLATIONS:
        idx = [NAMES.index(f) for f in feats]
        o, _ = run_cv(Xl, y, labeled, partners, fold_g, feature_idx=idx, models=["ordinalLogit"], res=res)
        m = metrics(y, o["ordinalLogit"])
        ablation.append({"step": name, "features": len(idx), "exact": r3(m["exact"]), "within1": r3(m["within1"]), "macroF1": r3(m["macroF1"]), "mae": r3(m["mae"])})

    # MNAR and censoring: label presence per band, held-out accuracy per band
    per_band = []
    for b in range(12):
        m = (Xl[:, NAMES.index("band")] == b)
        n_lab = int(m.sum())
        present = n_lab / 1000
        per_band.append({"band": b + 1, "labeled": n_lab, "labelPresence": r3(present),
                         "exact": r3((oof_g[shipped][m] == y[m]).mean()) if n_lab else None,
                         "within1": r3((np.abs(oof_g[shipped][m] - y[m]) <= 1).mean()) if n_lab else None,
                         "thinSupport": present < THIN_SUPPORT_BELOW})
    core = Xl[:, NAMES.index("band")] < 5
    core_tail = {"core": {"ranks": "1 to 5000", "n": int(core.sum()), "exact": r3((oof_g[shipped][core] == y[core]).mean()), "within1": r3((np.abs(oof_g[shipped][core] - y[core]) <= 1).mean())},
                 "tail": {"ranks": "5001 to 12000", "n": int((~core).sum()), "exact": r3((oof_g[shipped][~core] == y[~core]).mean()), "within1": r3((np.abs(oof_g[shipped][~core] - y[~core]) <= 1).mean())}}
    thin_bands = {p["band"] for p in per_band if p["thinSupport"]}

    # the final models on every label, then the unlabeled lemmas
    Xf = label_features(Xl, labeled, np.arange(len(labeled)), y, partners, res)
    Xu = base_features(unlabeled, lex, res)
    wmin_col, whas_col = NAMES.index("wiktFamilyMinLevel"), NAMES.index("wiktFamilyHasLabel")
    level_of, stem_min, wfam_min = {}, {}, {}
    for i, r in enumerate(labeled):
        lemma = norm(r["lemma"])
        level_of[lemma] = min(level_of.get(lemma, 9), int(y[i]))
        if len(lemma) >= STEM_LEN:
            stem_min[lemma[:STEM_LEN]] = min(stem_min.get(lemma[:STEM_LEN], 9), int(y[i]))
        wf = wfamily_of(r, res)
        if wf:
            wfam_min[wf] = min(wfam_min.get(wf, 9), int(y[i]))
    for i, r in enumerate(unlabeled):
        lemma = norm(r["lemma"])
        if len(lemma) >= STEM_LEN and lemma[:STEM_LEN] in stem_min:
            Xu[i, 12] = stem_min[lemma[:STEM_LEN]] + 1
            Xu[i, 13] = 1
        if r["pos"] == "VERB":
            lv = [level_of[p] for p in partners.get(lemma, []) if p in level_of]
            if lv:
                Xu[i, 14] = min(lv) + 1
                Xu[i, 15] = 1
        wf = wfamily_of(r, res)
        if wf in wfam_min:
            Xu[i, wmin_col] = wfam_min[wf] + 1
            Xu[i, whas_col] = 1
    Xtr, Xte = standardize(Xf[:, SHIPPED_IDX], Xu[:, SHIPPED_IDX])
    w_ol, th_ol = fit_ordinal_logit(Xtr, y)
    W_sm, b_sm = fit_softmax(Xtr, y)
    pred_ol, P_ol = predict_ordinal_logit(Xte, w_ol, th_ol)
    pred_sm, P_sm = predict_softmax(Xte, W_sm, b_sm)
    pred_main, P_main = (pred_ol, P_ol) if shipped == "ordinalLogit" else (pred_sm, P_sm)
    pred_other = pred_sm if shipped == "ordinalLogit" else pred_ol
    weights = sorted(((SHIPPED_NAMES[i], r3(w_ol[i])) for i in range(len(SHIPPED_NAMES))), key=lambda kv: -abs(kv[1]))[:20]

    predictions = []
    scope_counts = {}
    for i, r in enumerate(unlabeled):
        lemma = norm(r["lemma"])
        lx = lex.get(f"{lemma}\t{r['pos']}", [0, 0, 0])
        if r["pos"] == "PROPN":
            scope = "out-of-scope: proper noun"
        elif r["pos"] in NONLEXICAL:
            scope = "out-of-scope: non-lexical"
        elif not lx[0]:
            scope = "out-of-scope: not in lexicon"
        else:
            scope = "predicted"
        scope_counts[scope] = scope_counts.get(scope, 0) + 1
        row = {"rank": r["rank"], "lemma": r["lemma"], "pos": r["pos"], "scope": scope}
        if scope == "predicted":
            pred = int(pred_main[i])
            prob = round(float(P_main[i].max()), 3)  # the shipped digits decide the flags
            band = (r["rank"] - 1) // 1000 + 1
            notes = []
            if LEVELS[pred] == "C1":
                notes.append("C1 or beyond (the validated map stops at C1)")
            if band in thin_bands:
                notes.append("thin support (label presence in this rank band below the threshold)")
            row.update({"predicted": LEVELS[pred], "probability": prob, "modelsAgree": pred == int(pred_other[i]),
                        "abstain": prob < abstain, "uncertain": prob < abstain or pred != int(pred_other[i]),
                        "thinSupport": band in thin_bands, "note": "; ".join(notes) or None})
        predictions.append(row)
    pred_rows = [p for p in predictions if p["scope"] == "predicted"]
    fires_on_predicted = sum(1 for r in unlabeled if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a1") or res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a2"))
    per_level = {l: sum(1 for p in pred_rows if p["predicted"] == l) for l in LEVELS}
    uncertain = sum(1 for p in pred_rows if p["uncertain"])
    confident = sum(1 for p in pred_rows if not p["uncertain"])

    meta = {
        "snapshot": SNAPSHOT_DATE, "seed": SEED, "folds": FOLDS,
        "labeled": len(labeled), "unlabeled": len(unlabeled),
        "features": len(SHIPPED_NAMES), "featureNames": SHIPPED_NAMES,
        "excludedFeatures": {"names": EXCLUDED_NAMES, "why": EXCLUDED_WHY, "since": "2026-09-13",
                             "withThem": {"exact": r3(with_excluded["exact"]), "within1": r3(with_excluded["within1"]), "macroF1": r3(with_excluded["macroF1"]), "mae": r3(with_excluded["mae"]), "qwk": r3(with_excluded["qwk"])},
                             "gap": {"exact": r3(with_excluded["exact"] - evaluation["ordinalLogit"]["exact"]), "within1": r3(with_excluded["within1"] - evaluation["ordinalLogit"]["within1"])},
                             "firesOnLabeled": int(sum(1 for r in labeled if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a1") or res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a2"))),
                             "firesOnPredicted": None},
        "resources": {"wiktionaryCovered": sum(1 for r in rows if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("wikt")),
                      "borrowed": sum(1 for r in rows if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("borrowed")),
                      "unimorphCovered": sum(1 for r in rows if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("family")),
                      "wiktionaryFamilyCovered": sum(1 for r in rows if wfamily_of(r, res)),
                      "inA1List": sum(1 for r in rows if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a1")),
                      "inA2List": sum(1 for r in rows if res.get(f"{norm(r['lemma'])}\t{r['pos']}", {}).get("a2"))},
        "dispersionNote": "no dispersion feature since list v0.2.0: the shipped dictionary doc count exceeded the row count in a fifth of the rows and was defined nowhere upstream, so the list stopped carrying it; Gries DP across the five subcorpora needs per-subcorpus counts the dictionary does not carry",
        "llmFeature": "reserved, not included in this version",
        "stageA": "rule, not learned: no out-of-scope labels exist (PULS labels no proper nouns and stops at C1)",
        "grouping": {"groups": n_groups, "rule": "same lemma string, same derivational stem (first 5 characters), an aspect-pair link, the same UniMorph derivational family, or the same Wiktionary derived-term family", "foldSizes": fold_sizes, "foldLevels": fold_levels},
        "models": MODELS, "shipped": shipped, "challenger": challenger, "modelsAgreeOnHeldOut": r3(agree),
        "evaluation": evaluation,
        "evaluationRandomSplit": evaluation_random,
        "leakageGap": {m: {"exact": r3(evaluation_random[m]["exact"] - evaluation[m]["exact"]), "within1": r3(evaluation_random[m]["within1"] - evaluation[m]["within1"])} for m in evaluation_random},
        "lift": {"exactOverRankOnly": r3(evaluation[shipped]["exact"] - evaluation["rankOnly"]["exact"]),
                 "within1OverRankOnly": r3(evaluation[shipped]["within1"] - evaluation["rankOnly"]["within1"]),
                 "exactOverFreqOnly": r3(evaluation[shipped]["exact"] - evaluation["freqOnly"]["exact"]),
                 "exactOverMajority": r3(evaluation[shipped]["exact"] - evaluation["majority"]["exact"])},
        "ablation": ablation,
        "calibration": calib, "abstainThreshold": abstain,
        "perBand": per_band, "coreTail": core_tail, "thinSupportBelow": THIN_SUPPORT_BELOW,
        "ordinalWeights": weights, "thresholds": [r3(t) for t in th_ol],
        "scopeCounts": scope_counts, "predictedPerLevel": per_level, "uncertain": uncertain, "confident": confident,
        "coverage": {"confidentOfPredicted": r3(confident / len(pred_rows)) if pred_rows else 0, "confidentOfList": r3(confident / len(rows))},
        "download": "/downloads/ukrainian-frequency/predicted-cefr/predictions.csv",
        "heldOutDownload": "/downloads/ukrainian-frequency/predicted-cefr/held-out.csv",
        "license": "CC-BY-NC-SA-4.0 (the model is trained on the validated PULS overlay, CC BY-NC-SA 4.0 by permission, and the predictions carry its terms; they are ours, never the profile's)",
    }
    meta["excludedFeatures"]["firesOnPredicted"] = int(fires_on_predicted)
    full = dict(meta)
    full["rows"] = predictions
    held_out = [{"rank": labeled[i]["rank"], "lemma": labeled[i]["lemma"], "level": LEVELS[y[i]], "fold": int(fold_g[i]), "group": int(groups[i]),
                 **{m: LEVELS[oof_g[m][i]] for m in MODELS if m != "majority"},
                 "probability": round(float(prob_g[shipped][i].max()), 3)} for i in range(len(labeled))]
    with open(os.path.join(DATA, "predicted-cefr.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    os.makedirs(DL, exist_ok=True)
    with open(os.path.join(DL, "predictions.csv"), "w", encoding="utf-8") as fh:
        fh.write("rank,lemma,pos,scope,predicted_level,probability,models_agree,abstain,thin_support,uncertain,note\n")
        for p in predictions:
            yn = lambda k: "" if k not in p else ("yes" if p[k] else "no")
            fh.write(",".join(str(x) for x in [p["rank"], p["lemma"], p["pos"], p["scope"].replace(",", ";"), p.get("predicted", ""), p.get("probability", ""),
                                             yn("modelsAgree"), yn("abstain"), yn("thinSupport"), yn("uncertain"), (p.get("note") or "").replace(",", ";")]) + "\n")
    with open(os.path.join(DL, "held-out.csv"), "w", encoding="utf-8") as fh:
        cols = [m for m in MODELS if m != "majority"]
        fh.write("rank,lemma,validated_level,fold,group," + ",".join(cols) + ",probability\n")
        for h in held_out:
            fh.write(f"{h['rank']},{h['lemma']},{h['level']},{h['fold']},{h['group']}," + ",".join(h[m] for m in cols) + f",{h['probability']}\n")

    slim = dict(meta)
    slim["sample"] = sorted(pred_rows, key=lambda p: p["rank"])[:16]
    slim["uncertainSample"] = [p for p in pred_rows if p["uncertain"]][:8]
    body = (
        "// GENERATED by scripts/ukrainian-frequency/gapfill-model.py - do not edit by hand.\n"
        "// Browser-safe tier of the B1 extension's GAP-FILL MODEL (stage 4): predicted CEFR\n"
        "// levels for the list lemmas the validated PULS map does not cover, with the grouped\n"
        "// held-out evaluation, the ablation ladder, calibration, and the per-band support.\n"
        "// Predictions are OURS, shipped separately from the validated overlay and never merged\n"
        "// into it. Full rows: src/data/ukrainian-frequency/predicted-cefr.json and the public CSVs.\n"
        "export const PREDICTED_CEFR = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(LIB, "predicted-cefr.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    for name in MODELS:
        e = evaluation[name]
        print(f"{name:15s} exact {pct(e['exact'])}%  within1 {pct(e['within1'])}%  macroF1 {r3(e['macroF1'])}  mae {r3(e['mae'])}  qwk {r3(e['qwk'])}")
    print("random split:", {m: (pct(v["exact"]), pct(v["within1"])) for m, v in evaluation_random.items()})
    print("ablation:", [(a["step"], a["exact"], a["within1"], a["macroF1"]) for a in ablation])
    print("excluded (A1/A2 minima) would give:", meta["excludedFeatures"]["withThem"], "gap", meta["excludedFeatures"]["gap"], "fires on labeled", meta["excludedFeatures"]["firesOnLabeled"], "predicted", meta["excludedFeatures"]["firesOnPredicted"])
    print(f"groups {n_groups}; folds {fold_sizes}; shipped {shipped}; agree {pct(agree)}%; ece {calib['ece']}; abstain {abstain}; core/tail {core_tail}")
    print(f"scope {scope_counts}; per level {per_level}; uncertain {uncertain}; confident {confident}")


if __name__ == "__main__":
    main()
