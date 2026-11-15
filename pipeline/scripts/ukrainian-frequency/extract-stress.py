#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : thread 07, word stress (extractor)
#
# Rebuilds src/data/ukrainian-frequency/stress.json, the reviewed per-lemma
# stress snapshot, from the open sources, as ONE deterministic pass. It is the
# consolidation of the nine exploratory stages the column was first built with
# (handover of 2026-10-01); the committed snapshot is the artifact of record and
# the pure builder (src/lib/ukrainian-frequency/stress.mjs) applies the manual
# ledger (stress-overrides.json) LAST, so this script never needs to know a
# single manual decision.
#
# NOT run in the build or CI: it needs the ukrainian-word-stress dictionary
# (pip, 12 MB trie), the ~300 MB kaikki en.wiktionary dump and the ~16 MB
# uk.wiktionary dump, none vendored, plus the network for the names stage.
# CI holds the snapshot to the list and the release to the snapshot
# (__tests__/stress.test.js), never to these inputs.
#
# Status of this consolidation: the dictionary stage (stage 2) has been replayed
# over all 12,000 lemmas against the snapshot (it reproduces every dictionary
# row except the 39 the snapshot labels library_context / compound, see
# stress.SOURCE.md). Stages 3 to 9 are ported from the handover scripts and
# have not yet been re-run end to end from the dumps; the acceptance test for a
# full re-run is `--check`: the rebuilt rows must equal the committed snapshot
# row for row, except rows changed on purpose, which --check prints.
#
# Stages, in order (each later stage only touches rows the earlier ones left
# unresolved or flagged):
#   1. monosyllables: no mark needed.
#   2. the lang-uk dictionary, read straight from the trie and filtered by the
#      list's own UD part of speech and lemma features (Nom, Inf). No stanza:
#      the library's tagger guesses the part of speech of a bare lemma and gets
#      homographs wrong (брати́ "brothers" for the verb бра́ти). A lemma the
#      trie leaves ambiguous for its part of speech is carried as
#      `library_context` only when the library's full stressify() settles it.
#   3. en.wiktionary (kaikki JSONL): separates a true free variant (one entry,
#      "X or Y"), a homograph (separate entries) and a minor variant (every
#      sense archaic/dated/dialectal); fills lemmas the dictionary lacks; and
#      cross-checks the singles.
#   4. uk.wiktionary (the dump): the stress in each entry's headword line.
#   5. the vote: the dictionary (one voice, however it was read), en.wikt and
#      uk.wikt; two of three decide.
#   6. rules for conflicts that only look like conflicts: en.wikt marks every
#      part of a compound while the dictionary marks the main stress; doubled
#      acutes; a stanza guess against the POS-filtered lookup loses.
#   7. (goroh tiebreaks live in stress-overrides.json, applied by the builder.)
#   8. rules for lemmas no source covers: standard spelling, compounds,
#      acronyms, -енко surnames.
#   9. uk.wikipedia lead sentences for the proper nouns still missing
#      (resumable; results cached in --names-cache; a mark that does not sit
#      on a vowel is refused).
#
# Usage:
#   pip install --no-deps ukrainian-word-stress marisa-trie     # no torch/stanza needed
#   python3 scripts/ukrainian-frequency/extract-stress.py \
#     --kaikki /path/kaikki.org-dictionary-Ukrainian.jsonl \
#     --ukwikt /path/ukwiktionary-latest-pages-articles.xml.bz2 \
#     [--names] [--names-cache build/ukwiki-names.json] [--check]
#
# Gotchas (all handled here): the list writes the apostrophe as U+2019 and the
# trie as U+0027; stress is the combining acute U+0301, Wiktionary writes a
# secondary stress with the grave U+0300 and sometimes doubles the acute;
# positions are counted on the string with the marks removed; Wikimedia APIs
# return 429 to shared addresses, so dumps are used where they exist and
# Retry-After is honored where they do not.
#
# House rule: no em-dashes.
# ============================================================

import argparse
import bz2
import collections
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
SEED = os.path.join(DATA, "ubertext-lemmas-top12k.json")
OUT = os.path.join(DATA, "stress.json")

ACUTE = "\u0301"
GRAVE = "\u0300"
VOWELS = "аеєиіїоуюяАЕЄИІЇОУЮЯ"
APOS_IN = str.maketrans({"\u2019": "'", "\u02bc": "'", "`": "'"})
APOS_OUT = str.maketrans({"'": "\u2019", "\u02bc": "\u2019", "`": "\u2019"})


def nfc(s):
    return unicodedata.normalize("NFC", s)


def clean(s):
    return re.sub(ACUTE + "+", ACUTE, nfc(s)).replace(GRAVE, "")


def strip(s):
    return clean(s).replace(ACUTE, "")


def positions(s):
    out, i = [], 0
    for c in clean(s):
        if c == ACUTE:
            out.append(i)
        else:
            i += 1
    return tuple(out)


def mark(word, pos):
    w = word
    for i in sorted(pos, reverse=True):
        w = w[:i] + ACUTE + w[i:]
    return w


def nvow(w):
    return sum(c in VOWELS for c in w)


def last_vowel(w):
    for i in range(len(w) - 1, -1, -1):
        if w[i] in VOWELS:
            return i + 1
    return None


def marks_on_vowels(s):
    for i, c in enumerate(s):
        if c == ACUTE and (i == 0 or s[i - 1] not in VOWELS):
            return False
    return True


# ------------------------------------------------------------------ stage 2
UP = {"NOUN": {"NOUN"}, "PROPN": {"NOUN", "PROPN"}, "VERB": {"VERB"}, "ADJ": {"ADJ"}, "ADV": {"ADV"},
      "DET": {"DET", "PRON", "ADJ"}, "PRON": {"PRON", "DET"}, "NUM": {"NUM"}, "ADP": {"ADP"}, "CCONJ": {"CCONJ"},
      "SCONJ": {"SCONJ"}, "PART": {"PART"}, "INTJ": {"INTJ"}, "AUX": {"VERB", "AUX"}}
LEMMA_FEATS = {"NOUN": ["Case=Nom"], "PROPN": ["Case=Nom"], "VERB": ["VerbForm=Inf"], "ADJ": ["Case=Nom", "Gender=Masc"],
               "DET": ["Case=Nom", "Gender=Masc"], "PRON": ["Case=Nom"], "NUM": ["Case=Nom"]}


class Dictionary:
    """The lang-uk trie, read directly. resolve() returns (accents, how)."""

    def __init__(self):
        from ukrainian_word_stress.stressify_ import _load_dictionary, _trie_value, _parse_dictionary_value
        self._trie = _load_dictionary()
        self._value = _trie_value
        self._parse = _parse_dictionary_value
        self._stressify = None

    def readings(self, lemma):
        v = self._value(self._trie, lemma.translate(APOS_IN))
        return None if v is None else self._parse(v[0])

    def resolve(self, lemma, pos):
        rd = self.readings(lemma)
        if rd is None:
            return None, "absent"
        every = {tuple(a) for _, a in rd}
        if len(every) == 1:
            return tuple(rd[0][1]), "unique"
        want = {f"upos={u}" for u in UP.get(pos, {pos})}

        def uposof(t):
            return [x for x in t if x.startswith("upos=")]

        m = [(t, a) for t, a in rd if not uposof(t) or set(uposof(t)) & want]
        if not m:
            return None, "no_pos_match"
        feats = LEMMA_FEATS.get(pos, [])
        m2 = [(t, a) for t, a in m if all(f in t for f in feats if any(x.split("=")[0] == f.split("=")[0] for x in t))]
        m = m2 or m
        acc = {tuple(a) for _, a in m}
        if len(acc) == 1:
            a = next(iter(acc))
            return a, ("pos_unique" if len(a) == 1 else "pos_multi")
        return None, "pos_ambiguous"

    def accent_sets(self, lemma):
        """Every stress the trie allows for the lemma, one position per set
        member. A single reading carrying two accents on a plain word (та́ко́ж)
        is the trie's notation for a doublet, so it is split; on a hyphenated
        compound the two accents are main and secondary stress and stay
        together."""
        out = set()
        for _, a in self.readings(lemma) or []:
            a = tuple(a)
            if len(a) > 1 and "-" not in lemma:
                out.update((p,) for p in a)
            else:
                out.add(a)
        return out

    def _make(self, stanza):
        from ukrainian_word_stress import Stressifier, StressSymbol
        if stanza:
            # the library's default: its stanza tagger guesses the part of
            # speech of the bare lemma. Needs the stanza package and models.
            return Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent)
        from ukrainian_word_stress.stressify_ import Disambiguation
        return Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent, disambiguation=Disambiguation.Dictionary)

    def context(self, lemma):
        """The library's own full pass WITH its stanza tagger: what the 22
        `library_context` rows carry when the trie alone is ambiguous for the
        part of speech. Dictionary mode cannot reproduce them (it skips an
        ambiguity), so --library-context needs stanza installed."""
        if self._stressify is None:
            self._stressify = self._make(stanza=True)
        out = clean(self._stressify(lemma.translate(APOS_IN))).translate(APOS_OUT)
        return out if ACUTE in out else None

    def compound(self, lemma):
        """The library's own handling of a hyphenated word the trie has no
        entry for (dictionary mode, no tagger): each part stressed on its own.
        This is what the 25 `compound` rows carry."""
        if getattr(self, "_dict_only", None) is None:
            self._dict_only = self._make(stanza=False)
        out = clean(self._dict_only(lemma.translate(APOS_IN))).translate(APOS_OUT)
        return out if ACUTE in out else None


# ------------------------------------------------------------------ stage 3
EPOS = {"NOUN": {"noun"}, "PROPN": {"name", "noun"}, "VERB": {"verb"}, "ADJ": {"adj"}, "ADV": {"adv"}, "DET": {"pron", "det", "adj"},
        "PRON": {"pron", "det"}, "NUM": {"num"}, "ADP": {"prep"}, "CCONJ": {"conj"}, "SCONJ": {"conj"}, "PART": {"particle"}, "INTJ": {"intj"}}
MARGINAL = {"archaic", "dated", "dialectal", "obsolete", "rare", "regional", "slang", "nonstandard", "proscribed", "poetic"}


def read_kaikki(path, wanted):
    """Stream the kaikki JSONL; keep, per lemma, the entries whose canonical
    form is one of the list's lemmas. Returns norm(lemma) -> [entry]."""
    idx = collections.defaultdict(list)
    opener = bz2.open if path.endswith(".bz2") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            w = nfc(e.get("word", "")).translate(APOS_OUT)
            if w not in wanted:
                continue
            idx[w].append({
                "pos": e.get("pos"),
                "senses": [{"tags": s.get("tags", [])} for s in e.get("senses", [])],
                "forms": [{"form": f.get("form", ""), "tags": f.get("tags", [])} for f in e.get("forms", []) if "canonical" in f.get("tags", [])],
            })
    return idx


def en_readings(idx, lemma, pos):
    """{accents} per en.wiktionary entry family: a set with two members is a
    free variant inside one entry or a homograph across entries; the caller
    tells them apart with en_kind()."""
    out = []
    entries = idx.get(lemma, [])
    # entries of the list's part of speech; when en.wiktionary has none, all of
    # them (пора is ADV on the list and only a noun there). Order is the dump's,
    # which is the page's, so out[0] is the first-listed entry.
    matched = [e for e in entries if e["pos"] in EPOS.get(pos, set())]
    for e in matched or entries:
        real = [s for s in e["senses"] if not {"form-of", "alt-of"} & set(s["tags"])]
        if not real or all(set(s["tags"]) & MARGINAL for s in real):
            continue
        accs = set()
        for f in e["forms"]:
            form = nfc(f["form"]).translate(APOS_OUT)
            if strip(form) == lemma and positions(form):
                p = positions(form)
                # a doubled position in one form is en.wiktionary's either-stress notation
                for one in (p if len(p) > 1 and "-" not in lemma else [p]):
                    accs.add(one if isinstance(one, tuple) else (one,))
        if accs:
            out.append(accs)
    return out


def en_pos_matched(idx, lemma, pos):
    """True when en.wiktionary has an entry in the list's own part of speech.
    Only such an entry may vote against the dictionary; the fallback to other
    parts of speech in en_readings() only describes a doublet."""
    return any(e["pos"] in EPOS.get(pos, set()) for e in idx.get(lemma, []))


def en_kind(entries):
    """homograph: several entries with different stress; free_variant: one entry
    with two stresses; single: one stress; none."""
    if not entries:
        return "none", set()
    union = set().union(*entries)
    if len(union) == 1:
        return "single", union
    if len(entries) > 1 and any(len(e) == 1 for e in entries) and len({frozenset(e) for e in entries}) > 1:
        return "homograph", union
    return "free_variant", union


# ------------------------------------------------------------------ stage 4
UPOS_UK = {"NOUN": {"NOUN", "PROPN"}, "PROPN": {"NOUN", "PROPN"}, "VERB": {"VERB"}, "ADJ": {"ADJ"}, "ADV": {"ADV"}, "DET": {"PRON", "ADJ"},
           "PRON": {"PRON"}, "NUM": {"NUM"}, "ADP": {"ADP"}, "PART": {"PART"}, "CCONJ": {"CONJ"}, "SCONJ": {"CONJ"}, "INTJ": {"INTJ"}}
# The part of speech is the name of the inflection template under
# "Морфосинтаксичні ознаки" ({{імен uk 1a m una|...}}, {{дієсл uk 6°b/cX|...}}).
POSMAP_UK = [("імен", "NOUN"), ("ім ", "NOUN"), ("сущ", "NOUN"), ("прізв", "PROPN"), ("дієсл", "VERB"), ("прикм", "ADJ"),
             ("присл", "ADV"), ("займ", "PRON"), ("числ", "NUM"), ("прийм", "ADP"), ("спол", "CONJ"), ("част", "PART"),
             ("вигук", "INTJ")]
UK_TEMPLATE = re.compile(r"\{\{\s*((?:імен|ім|сущ|прізв|дієсл|прикм|присл|займ|числ|прийм|спол|част|вигук)[^\s|}]*)\s+uk\b([^\n]*)")
UK_SYLLABLES = re.compile(r"склади\s*=\s*(\{\{склади\|[^}]*\}\}|[^|}\n]+)")


def uk_entries(wikitext):
    """Entries of a uk.wiktionary page, read from the {{=uk=}} section. A page
    with homonyms splits into `== headword ==` chunks (the headword carries the
    stress); a page with one entry has no such heading, and the stress is in
    the inflection template's `склади=` parameter ({{склади|лю|ди́|на}} or
    о́р-ган). The part of speech is the template's name. (The first port read
    a ''' '''-bold headword under `== Українська ==`, which the dump does not
    use, so the stage found nothing; caught by the end-to-end re-run.)"""
    out = []
    if not wikitext or "{{=uk=}}" not in wikitext:
        return out
    sec = wikitext.split("{{=uk=}}", 1)[1]
    sec = re.split(r"\{\{=[a-z-]+=\}\}", sec, maxsplit=1)[0]
    heads = list(re.finditer(r"^==\s*([^=\n]+?)\s*==\s*$", sec, re.M))
    chunks = [(h.group(1), sec[h.end():(heads[i + 1].start() if i + 1 < len(heads) else len(sec))]) for i, h in enumerate(heads)] or [(None, sec)]
    for heading, chunk in chunks:
        t = UK_TEMPLATE.search(chunk)
        pos = None
        if t:
            name = t.group(1) + " "
            pos = next((tag for key, tag in POSMAP_UK if name.startswith(key)), None)
        form = None
        if t:
            s = UK_SYLLABLES.search(t.group(2))
            if s:
                raw = s.group(1).replace("{{склади|", "").replace("}}", "")
                raw = re.sub(r"[|\s\-·]", "", raw)
                if ACUTE in nfc(raw):
                    form = raw
        if form is None and heading and ACUTE in nfc(heading):
            form = heading.split(",")[0].strip()
        gloss = ""
        m = re.search(r"^#\s*([^\n]+)", chunk, re.M)
        if m:
            gloss = m.group(1).strip()
        if form:
            out.append({"head": nfc(form).translate(APOS_OUT), "pos": pos, "gloss": gloss})
    return out


def read_ukwikt(path, wanted):
    """Stream the pages-articles dump; keep the wikitext of the pages whose
    title is one of the list's lemmas. Returns lemma -> wikitext."""
    pages = {}
    title, in_text, buf, keep = None, False, [], False
    with bz2.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if "<title>" in line:
                title = nfc(re.sub(r"\s*</?title>\s*", "", line)).translate(APOS_OUT)
                keep = title in wanted
            elif keep and "<text" in line:
                in_text = True
                buf = [line.split(">", 1)[1]]
                if "</text>" in line:
                    pages[title] = buf[0].split("</text>")[0]
                    in_text = False
            elif keep and in_text:
                if "</text>" in line:
                    buf.append(line.split("</text>")[0])
                    pages[title] = "".join(buf)
                    in_text = False
                else:
                    buf.append(line)
    return pages


def uk_readings(pages, lemma, pos):
    out = set()
    for e in uk_entries(pages.get(lemma, "")):
        if e["pos"] not in UPOS_UK.get(pos, set()):
            continue
        if "форма" in e["gloss"][:12]:
            continue
        h = e["head"].split(",")[0].strip()
        if strip(h) == lemma and positions(h):
            out.add(positions(h))
    return out


# ------------------------------------------------------------------ stage 8
SPELL = [("ект", "єкт"), ("рр", "р"), ("сідний", "сідній"), ("ярмарк", "ярмарок")]
PREF = ["екс-", "прес", "віце-", "держ", "мін", "нац", "політ", "фін", "фіз", "спец", "адмін", "євро", "відео", "фото", "інформ", "обл",
        "центро", "гідромет", "соц", "пів", "укр", "рад", "газ", "транс", "авто"]
ORG = ("Укр", "Держ", "Мін", "Нац", "Центр", "Київ", "Рос", "Мет", "Рад")


def rule_missing(d, w, pos, depth=0):
    """Returns (stressed, status, note) or (None, None, None)."""
    if nvow(w) <= 1:
        return w, "monosyllabic", ""

    def lookup(x, p):
        a, _ = d.resolve(x, p)
        if a and len(a) == 1:
            return a
        rd = d.readings(x)
        if rd:
            acc = {tuple(y) for _, y in rd}
            if len(acc) == 1 and len(next(iter(acc))) == 1:
                return next(iter(acc))
        return None

    a = lookup(w, pos)
    if a:
        return mark(w, a), "dictionary", ""
    for old, new in SPELL:
        if old in w.lower():
            w2 = re.sub(old, new, w, flags=re.I)
            a = lookup(w2, pos)
            if a:
                return mark(w2, a), "spelling_variant", f"standard spelling {w2}"
    if "-" in w and depth < 3:
        head, _, tail = w.rpartition("-")
        s, how, _ = rule_missing(d, tail, pos, depth + 1)
        if how in ("dictionary", "spelling_variant", "compound_rule", "monosyllabic"):
            if ACUTE not in s:
                s = mark(s, (last_vowel(s),))
            return head + "-" + s, "compound_rule", ""
    if w.isupper() and len(w) <= 6:
        return mark(w, (last_vowel(w),)), "abbreviation_rule", ""
    if pos == "PROPN" and re.search(r"[еє]нк[оа]$", w):
        i = re.search(r"[еє]нк[оа]$", w).start() + 1
        return mark(w, (i,)), "surname_enko_rule", ""
    low = w.lower()
    if pos != "PROPN" or w.startswith(ORG):
        for i in range(2, len(w) - 2):
            pre, suf = low[:i], w[i:]
            if nvow(suf) == 0:
                break
            okpre = any(low.startswith(p.rstrip("-")) for p in PREF)
            if not okpre and len(suf) < 5:
                continue
            a = lookup(suf.lower(), pos if pos != "PROPN" else "NOUN") if nvow(suf) > 1 else ((last_vowel(suf),) if okpre else None)
            if a:
                return w[:i] + mark(suf, a), "compound_rule", ""
    return None, None, None


# ------------------------------------------------------------------ stage 9
UA_HEADER = {"User-Agent": "ukvocab-stress-check/0.2 (research; low-volume)"}


def wiki_api(params):
    url = "https://uk.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA_HEADER), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 20 * (attempt + 1)
            print(f"  429, waiting {wait}s", flush=True)
            time.sleep(wait)
    return {}


def wiki_name(lemma):
    """[stressed, article, alternates] or [None, None, None]. A stressed token
    counts only when its unstressed form equals the lemma exactly and every
    mark sits on a vowel."""
    d = wiki_api({"action": "query", "generator": "search", "gsrsearch": lemma, "gsrlimit": "5", "prop": "extracts", "exintro": "1",
                  "explaintext": "1", "exchars": "400", "format": "json", "formatversion": "2"})
    pages = sorted(d.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
    votes, src = collections.Counter(), {}
    for p in pages:
        for tok in re.findall(r"[\w\u0301\u2019'-]+", p.get("extract", "")):
            tok = nfc(tok).translate(APOS_OUT)
            if ACUTE in tok and strip(tok) == lemma and marks_on_vowels(tok):
                votes[tok] += 1
                src.setdefault(tok, p["title"])
    if not votes:
        return [None, None, None]
    best = votes.most_common(1)[0][0]
    return [best, src[best], "|".join(k for k in votes if k != best)]


# ------------------------------------------------------------------ main
def build(args):
    seed = json.load(open(SEED, encoding="utf-8"))
    lemmas = [(i + 1, nfc(r["lemma"]), r["pos"]) for i, r in enumerate(seed["rows"])]
    wanted = {l for _, l, _ in lemmas}
    d = Dictionary()
    en = read_kaikki(args.kaikki, wanted) if args.kaikki else {}
    uk = read_ukwikt(args.ukwikt, wanted) if args.ukwikt else {}
    names = {}
    if args.names_cache and os.path.exists(args.names_cache):
        names = json.load(open(args.names_cache, encoding="utf-8"))

    rows = []
    for rank, lemma, pos in lemmas:
        row = {"rank": rank, "lemma": lemma, "pos": pos, "stress": "", "variants": [], "status": "missing", "note": "", "source": ""}
        rows.append(row)
        # 1
        if nvow(lemma) <= 1:
            row.update(stress=lemma, status="monosyllabic", source="rule")
            continue
        # 2
        acc, how = d.resolve(lemma, pos)
        dict_all = d.accent_sets(lemma)
        dict_single = acc if (acc and len(acc) == 1 and len(dict_all) > 0) else None
        if acc and len(acc) > 1 and "-" not in lemma:
            dict_single = None  # one reading, two accents: a doublet, read below
        en_ent = en_readings(en, lemma, pos) if en else []
        kind, en_acc = en_kind(en_ent)
        # the first-listed en.wiktionary entry's stress is the primary of a
        # homograph or free variant (the corpus count may move it later)
        first = sorted(en_ent[0])[0] if en_ent else None
        uk_acc = uk_readings(uk, lemma, pos) if uk else set()

        hyphen_ctx = False
        if "-" in lemma:
            multi = [a for a in dict_all if len(a) > 1]
            # The released column is not uniform here, and it is reproduced as
            # released: where the library's tagged pass (stanza) marks one part
            # the row is the dictionary's main stress (adjudicated, 4 rows);
            # where it marks two or none, en.wiktionary's full form stands
            # (wiktionary, 10 rows). The tagged pass is a model, not a lookup,
            # so one row (півде́нно-за́хідний) can land on either side between
            # versions; a uniform convention is a data change for v1.0.1.
            ctx = d.context(lemma) if (multi and args.library_context) else None
            if ctx and len(positions(ctx)) == 1:
                # The released column took these from the library's own
                # tagged pass, which marks one part (івано-франкі́вський); the
                # row then goes to the vote below like any single-stress row.
                # The column is not consistent here: rows that reached the
                # library with two marks keep both (прем’є́р-міні́стр, from
                # en.wiktionary) or the main stress with a note. Reproduced as
                # released; a uniform convention is a data change (see
                # docs/ukrainian-frequency/stress-column.md).
                dict_single, how, hyphen_ctx = positions(ctx), "unique", True
            elif multi:
                # the dictionary marks a compound's main and secondary stress;
                # en.wiktionary, when it has the word, writes every part's
                # stress in one form, and that form is taken whole
                if kind == "single" and len(next(iter(en_acc))) > 1:
                    row.update(stress=mark(lemma, next(iter(en_acc))), status="wiktionary", source="wiktionary")
                else:
                    main = max(multi, key=lambda a: a[-1])
                    row.update(stress=mark(lemma, (main[-1],)), status="compound_main_stress", source="rule",
                               note=f"secondary stress: {mark(lemma, (main[0],))}")
                continue
            if not dict_all:
                if kind == "single":
                    row.update(stress=mark(lemma, next(iter(en_acc))), status="wiktionary_filled", source="wiktionary")
                    continue
                comp = d.compound(lemma) or (d.context(lemma) if args.library_context else None)
                if comp:
                    row.update(stress=comp, status="compound", source="ukrainian-word-stress")
                    continue

        # 3 + 4 + 5
        if dict_single:
            dict_name = "dict+pos" if how == "pos_unique" else "dict"
            status = "dictionary_pos" if how == "pos_unique" else "dictionary"
            en_vote = next(iter(en_acc)) if kind == "single" and en_pos_matched(en, lemma, pos) else None
            if en_vote is not None and "-" in lemma and len(en_vote) > 1 and set(dict_single) <= set(en_vote):
                # en.wiktionary marks every part of the compound, the dictionary
                # the main stress: agreement, kept as the dictionary wrote it
                row.update(stress=mark(lemma, dict_single), status="adjudicated", source="compound_main_stress_agrees",
                           note=f"wiktionary: {mark(lemma, en_vote)}")
                continue
            if en_vote is None or en_vote == dict_single:
                # en.wiktionary agrees or is silent: the dictionary stands.
                # uk.wiktionary alone does not overturn it (one voice against one).
                # A single-stress row is not relabeled when en.wiktionary lists a
                # second reading; the released column never did, and doing so is
                # a data change for a later version, not a reproduction.
                row.update(stress=mark(lemma, dict_single), status="compound" if hyphen_ctx else status, source="ukrainian-word-stress")
                continue
            # en.wiktionary disagrees: a vote, with uk.wiktionary as the third voice
            votes = collections.Counter({dict_single: 1, en_vote: 1})
            who = {dict_single: [dict_name], en_vote: ["en.wikt"]}
            if len(uk_acc) == 1:
                x = next(iter(uk_acc))
                votes[x] += 1
                who.setdefault(x, []).append("uk.wikt")
            best, n = votes.most_common(1)[0]
            if n >= 2:
                row.update(stress=mark(lemma, best), status="adjudicated", source="+".join(who[best]))
            else:
                row.update(status="missing", note="conflict: " + " ; ".join(f"{mark(lemma, k)}: {','.join(v)}" for k, v in who.items()))
            continue
        if dict_all and len(dict_all) > 1:
            # a dictionary doublet: let en.wiktionary say what kind
            single = {a for a in dict_all if len(a) == 1}
            if kind == "single" and en_acc <= single:
                a = next(iter(en_acc))
                row.update(stress=mark(lemma, a), status="wiktionary", source="wiktionary", note="minor variant: " + "|".join(mark(lemma, x) for x in sorted(single - {a})))
            elif kind in ("homograph", "free_variant"):
                row.update(stress=mark(lemma, first), status=kind, source="wiktionary", variants=[mark(lemma, first)] + [mark(lemma, a) for a in sorted(en_acc) if a != first])
            elif how == "pos_unique" and acc:
                row.update(stress=mark(lemma, acc), status="dictionary_pos", source="ukrainian-word-stress")
            else:
                ctx = d.context(lemma) if args.library_context else None
                if ctx and positions(ctx) in single:
                    row.update(stress=ctx, status="library_context", source="ukrainian-word-stress")
                else:
                    prim = sorted(single)[0]
                    row.update(stress=mark(lemma, prim), status="doublet_dictionary_only", source="ukrainian-word-stress", variants=[mark(lemma, a) for a in sorted(single)])
            continue
        # absent from the dictionary
        if kind == "single":
            row.update(stress=mark(lemma, next(iter(en_acc))), status="wiktionary_filled", source="wiktionary")
            continue
        if kind in ("homograph", "free_variant"):
            row.update(stress=mark(lemma, first), status="wiktionary_filled_variant", source="wiktionary", variants=[mark(lemma, first)] + [mark(lemma, a) for a in sorted(en_acc) if a != first])
            continue
        if len(uk_acc) == 1:
            row.update(stress=mark(lemma, next(iter(uk_acc))), status="wiktionary_filled", source="uk.wiktionary")
            continue
        # 8
        s, status, note = rule_missing(d, lemma, pos)
        if s:
            row.update(stress=s, status=status, note=note, source="rule")
            continue
        # 9
        # names, and the capitalized nouns that are names in all but tag (Вікімапія)
        if (pos == "PROPN" or lemma[:1].isupper()) and args.names:
            if lemma not in names:
                names[lemma] = wiki_name(lemma)
                if args.names_cache:
                    json.dump(names, open(args.names_cache, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
                time.sleep(1.2)
            best, title, alts = names.get(lemma, [None, None, None])
            if best:
                row.update(stress=best, status="wikipedia_lead_variants" if alts else "wikipedia_lead", source=f"uk.wikipedia: {title}")
                if alts:
                    row["variants"] = [best] + alts.split("|")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaikki", help="kaikki.org Ukrainian JSONL (or .bz2)")
    ap.add_argument("--ukwikt", help="ukwiktionary-latest-pages-articles.xml.bz2")
    ap.add_argument("--names", action="store_true", help="run the uk.wikipedia names stage (network)")
    ap.add_argument("--names-cache", default=os.path.join(ROOT, "build", "ukwiki-names.json"))
    ap.add_argument("--library-context", action="store_true", help="let the library's own pass settle trie-ambiguous rows (library_context)")
    ap.add_argument("--check", action="store_true", help="rebuild and diff against the committed snapshot; do not write")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.names_cache), exist_ok=True)
    rows = build(args)
    if args.check:
        # Two kinds of difference, reported apart: a changed STRESS is a data
        # change and fails the check; a changed STATUS with the same stress is
        # a provenance label the rebuild reads differently, reported only.
        # A rank in the manual ledger is settled by the builder, which applies
        # stress-overrides.json last; the rebuild does not need to agree there.
        cur = {r["rank"]: r for r in json.load(open(OUT, encoding="utf-8"))["rows"]}
        ledger = {o["rank"] for o in json.load(open(os.path.join(DATA, "stress-overrides.json"), encoding="utf-8"))["rows"]}
        settled = [r for r in rows if r["rank"] in ledger and r["stress"] != cur[r["rank"]]["stress"]]
        print(f"{len(settled)} rows differ only where the manual ledger settles them (applied last by the builder)")
        rows = [r for r in rows if r["rank"] not in ledger]
        # Proper nouns are out of scope (owner decision 2026-10-01): the column
        # makes no claim about them, so a name that rebuilds differently is
        # reported, never a failure. The names stage keeps running so the
        # report stays honest about what the sources now say.
        names_diff = [(r["rank"], r["lemma"], cur[r["rank"]]["stress"], cur[r["rank"]]["status"], r["stress"], r["status"]) for r in rows
                      if r["pos"] == "PROPN" and r["stress"] != cur[r["rank"]]["stress"]]
        print(f"{len(names_diff)} proper-noun rows rebuild with a different stress (out of scope, reported only)")
        for x in names_diff:
            print("  ", *x)
        rows = [r for r in rows if r["pos"] != "PROPN"]
        stress = [(r["rank"], r["lemma"], cur[r["rank"]]["stress"], cur[r["rank"]]["status"], r["stress"], r["status"]) for r in rows
                  if r["stress"] != cur[r["rank"]]["stress"]]
        labels = collections.Counter((cur[r["rank"]]["status"], r["status"]) for r in rows
                                     if r["stress"] == cur[r["rank"]]["stress"] and r["status"] != cur[r["rank"]]["status"])
        print(f"{len(stress)} in-scope rows rebuild with a different stress than the committed snapshot")
        for x in stress:
            print("  ", *x)
        print(f"{sum(labels.values())} rows keep their stress under a different status label")
        for (a, b), k in labels.most_common():
            print(f"   {k:5d}  {a} -> {b}")
        sys.exit(1 if stress else 0)
    cur = json.load(open(OUT, encoding="utf-8"))
    head = {k: v for k, v in cur.items() if k != "rows"}
    body = ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(head, ensure_ascii=False, indent=1)[:-2] + ',\n "rows": [\n' + body + "\n ]\n}\n")
    c = collections.Counter(r["status"] for r in rows)
    print(dict(c.most_common()))


if __name__ == "__main__":
    main()
