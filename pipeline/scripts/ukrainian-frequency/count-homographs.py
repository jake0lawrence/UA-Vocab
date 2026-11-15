#!/usr/bin/env python3
# ============================================================
# UKRAINIAN FREQUENCY : thread 07, word stress: the homograph corpus count
#
# For a homograph (one spelling, two words, two stresses: о́рган the body,
# орга́н the instrument) the stress column cannot know which reading a learner
# will meet more often, and the first en.wiktionary entry is not evidence. This
# script asks the corpus the list is built from. For each in-scope homograph it
# takes both readings' paradigms from en.wiktionary (kaikki.org), keeps the
# inflected forms that are SPELLED differently between the readings (о́ргану vs
# орга́на are spelled alike and tell nothing; прохо́дити's проходитиме against
# проходи́ти's проходім do), counts those forms across the five UberText 2.0
# subcorpora, and writes the counts per reading. The pure builder then makes
# the reading with the larger count the primary and puts the counts on the row.
#
# What it cannot do, and says so: a pair whose forms are spelled alike in every
# cell (most noun pairs) is not decidable by counting surface forms, and stays
# `homograph` with the first en.wiktionary entry as primary and the note
# saying the primary is unverified. Sense disambiguation of the shared forms
# would need a tagger that knows the two words, which no open Ukrainian tagger
# does.
#
# NOT run in the build or CI (it streams about 300 MB of kaikki and 5.2 GB of
# compressed corpus text; nothing lands on disk but the counts). CI holds the
# committed stress-homographs.json to the stress snapshot (every lemma on it is
# a homograph on the list) and the release to the JSON; never to the corpus.
#
# Stages, each resumable through --work-dir:
#   1. --kaikki: stream the kaikki JSONL, keep every entry whose word is an
#      in-scope homograph lemma (kaikki-entries.json), and index every form
#      of every Ukrainian entry by the words that have it (kaikki-forms.json),
#      so a form that belongs to any other word can be struck below. A page
#      that is itself an inflected form (kaikki's form-of entries: обіду is a
#      page, but not a word) registers nothing, or every form with its own
#      page would look like another word's.
#   2. plan: group a lemma's entries by the stress of the canonical headword;
#      a reading's distinguishing forms are the forms no other reading of that
#      lemma spells the same way, minus the headword itself, minus any form that
#      is itself a lemma on the list (an aspect partner or a related verb kaikki
#      lists under `forms`, which belongs to its own row), minus forms whose
#      only tags are an aspect label, minus any form that the thread-04
#      paradigms file lists for ANOTHER lemma (заходи is the imperative of
#      заходи́ти and the plural of захід "measures"; погоди the imperative of
#      погоди́ти and the genitive of погода "weather": a surface count cannot
#      tell them apart, so such a form is evidence for nothing), and likewise
#      any form or headword of any other word in en.wiktionary (твердь the
#      noun against the imperative of тве́рдити), and, the authoritative
#      check, any form the site's own lemmatizer (VESUM through
#      /api/lemmatize, token mode, cached in the work dir) reads as any word
#      but the homograph itself (зводи is the imperative of зводи́ти and the
#      plural of звід; деревинка is a diminutive kaikki lists under the noun's
#      forms). A form VESUM does not know keeps kaikki's word for it.
#      Decidable means every reading keeps at least one distinguishing form.
#   3. --corpus <name>=<url-or-path> (repeatable): stream each subcorpus,
#      lowercase, tokenize on Cyrillic letters and the apostrophe, count the
#      distinguishing forms. Counts per corpus are saved as each one finishes,
#      with the form set they were counted over; a cached corpus is reused
#      only while that set still covers the plan, else it is streamed again.
#      A stream the network cuts short is recorded as truncated with the
#      lines it did read, never passed off as the whole corpus.
#   4. write src/data/ukrainian-frequency/stress-homographs.json: the plan,
#      the counts per reading per corpus, and the decision per row, keyed by
#      rank (пора is on the list twice, as a noun and as an adverb).
#
#   python3 scripts/ukrainian-frequency/count-homographs.py \
#     --kaikki https://kaikki.org/dictionary/Ukrainian/kaikki.org-dictionary-Ukrainian.jsonl \
#     --corpus wikipedia=https://lang.org.ua/static/downloads/ubertext2.0/wikipedia/sentenced/ubertext.wikipedia.filter_rus_gcld+short.text_only.txt.bz2 \
#     --corpus news=... --corpus fiction=... --corpus court=... --corpus social=... \
#     --snapshot 2026-10-01
#
# A run with the same inputs reproduces the same JSON. House rule: no em-dashes.
# ============================================================

import argparse
import collections
import gzip
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
OUT = os.path.join(DATA, "stress-homographs.json")

ACUTE = "\u0301"
GRAVE = "\u0300"
APOS = str.maketrans({"\u02bc": "\u2019", "'": "\u2019", "`": "\u2019"})
TOKEN = re.compile(r"[а-яіїєґА-ЯІЇЄҐ\u2019'\u02bc-]+")
UA = {"User-Agent": "ukvocab-stress-homographs/0.1 (research; one pass)"}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def clean(s):
    return re.sub(ACUTE + "+", ACUTE, nfc(s)).replace(GRAVE, "").translate(APOS)


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


class Stream:
    """A text stream over a URL or a path; .bz2 is decompressed on the fly
    through bzcat, and `truncated` says whether bzcat saw the end of the file."""

    def __init__(self, src):
        self.proc = None
        self.text = open_stream(src, self)

    def __iter__(self):
        return iter(self.text)

    @property
    def truncated(self):
        if self.proc is None:
            return False
        self.proc.stdout.close()
        return self.proc.wait() != 0


def open_stream(src, owner=None):
    """A text stream over a URL or a path; .bz2 is decompressed on the fly."""
    if src.startswith("http://") or src.startswith("https://"):
        raw = urllib.request.urlopen(urllib.request.Request(src, headers=UA), timeout=120)
    else:
        raw = open(src, "rb")
    if src.endswith(".bz2"):
        # bz2.BZ2File over a socket is slow in CPython; a subprocess bzcat keeps up with the network
        proc = subprocess.Popen(["bzcat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1 << 20)
        if owner is not None:
            owner.proc = proc

        def pump():
            try:
                while True:
                    chunk = raw.read(1 << 20)
                    if not chunk:
                        break
                    proc.stdin.write(chunk)
            finally:
                proc.stdin.close()

        import threading

        threading.Thread(target=pump, daemon=True).start()
        return io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ stage 1
def read_kaikki(src, wanted):
    out = collections.defaultdict(list)
    owners = collections.defaultdict(set)
    n = 0
    for line in open_stream(src):
        n += 1
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        w = nfc(e.get("word", "")).translate(APOS)
        lw = w.lower()
        # a form-of page (обіду, "genitive singular of обід") is not a word of
        # its own; registering it as one would strike the very forms it names
        form_of = any("form-of" in s.get("tags", []) or s.get("form_of") for s in e.get("senses", []))
        if not form_of:
            owners[lw].add(lw)
            for f in e.get("forms", []):
                if {"romanization", "table-tags", "inflection-template", "class"} & set(f.get("tags", [])):
                    continue
                form = strip(f.get("form", "")).lower()
                if form:
                    owners[form].add(lw)
        if w not in wanted:
            continue
        out[w].append({
            "pos": e.get("pos"),
            "head": [f["form"] for f in e.get("forms", []) if "canonical" in f.get("tags", [])],
            # glosses are a reader's hint, not a quotation: the house rule folds a dash
            "glosses": [g.replace("\u2014", "-").replace("\u2013", "-") for s in e.get("senses", []) for g in s.get("glosses", [])[:1]][:4],
            "forms": [{"form": f["form"], "tags": f.get("tags", [])} for f in e.get("forms", [])
                      if not {"canonical", "romanization", "table-tags", "inflection-template", "class"} & set(f.get("tags", []))],
        })
    return {"lines": n, "entries": out, "owners": {f: sorted(ws) for f, ws in owners.items() if len(ws) > 1 or f not in ws}}


# ------------------------------------------------------------------ stage 2
ASPECT_ONLY = {frozenset(["perfective"]), frozenset(["imperfective"]), frozenset(["perfective", "aspect"]), frozenset(["imperfective", "aspect"])}


def plan_for(lemma, entries, list_lemmas, other_forms, kaikki_owners, foreign=frozenset()):
    groups = {}
    for e in entries:
        heads = [clean(h) for h in e["head"] if strip(h) == lemma and positions(h)]
        if not heads:
            continue
        p = positions(heads[0])
        if len(p) != 1:
            continue
        g = groups.setdefault(p, {"stress": heads[0], "pos": set(), "glosses": [], "forms": set()})
        g["pos"].add(e["pos"])
        for x in e["glosses"]:
            if x not in g["glosses"] and len(g["glosses"]) < 3:
                g["glosses"].append(x)
        for f in e["forms"]:
            if frozenset(f["tags"]) in ASPECT_ONLY:
                continue
            form = strip(f["form"]).lower()
            if not re.fullmatch(r"[а-яіїєґ\u2019-]+", form):
                continue
            if form == lemma.lower() or (form in list_lemmas and form != lemma.lower()):
                continue
            if form in other_forms.get(lemma.lower(), set()):
                continue
            if any(o != lemma.lower() for o in kaikki_owners.get(form, ())):
                continue
            if form in foreign:
                continue
            g["forms"].add(form)
    if len(groups) < 2:
        return {"decidable": False, "why": "en.wiktionary has one stress group for this spelling", "readings": [
            {"stress": g["stress"], "pos": sorted(g["pos"]), "glosses": g["glosses"], "uniqueForms": []} for g in groups.values()]}
    keys = sorted(groups, key=lambda k: k[0])
    uniq = {k: groups[k]["forms"] - set().union(*(groups[o]["forms"] for o in keys if o != k)) for k in keys}
    decidable = all(uniq[k] for k in keys)
    return {
        "decidable": decidable,
        "why": "" if decidable else "the readings' forms are spelled alike in every cell",
        "readings": [{"stress": groups[k]["stress"], "pos": sorted(groups[k]["pos"]), "glosses": groups[k]["glosses"], "uniqueForms": sorted(uniq[k])} for k in keys],
    }


# ------------------------------------------------------------------ stage 2b
def lemmatize(forms, url, cache_path):
    """Every VESUM headword the lemmatizer offers for each form (the lemma it
    picks plus every alternative), through the site's own endpoint in token
    mode; answers are cached so a re-run asks only for forms it has not seen."""
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    todo = sorted(f for f in forms if f not in cache)
    for i in range(0, len(todo), 1500):
        batch = todo[i:i + 1500]
        body = json.dumps({"tokens": batch}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={**UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            answer = json.load(resp)
        for t in answer["tokens"]:
            lemmas = set()
            if t.get("lemma"):
                lemmas.add(nfc(t["lemma"]).translate(APOS).lower())
            for a in t.get("alternatives", []) or []:
                if a.get("lemma"):
                    lemmas.add(nfc(a["lemma"]).translate(APOS).lower())
            cache[nfc(t["token"]).translate(APOS).lower()] = {"known": bool(t.get("known")), "lemmas": sorted(lemmas)}
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return cache


def foreign_forms(lemma, forms, lemmatized):
    """The forms VESUM reads as any word but this lemma. A form it does not
    know is not struck: kaikki's word for it stands."""
    out = set()
    for f in forms:
        a = lemmatized.get(f)
        if a and a["known"] and any(l != lemma.lower() for l in a["lemmas"]):
            out.add(f)
    return out


# ------------------------------------------------------------------ stage 3
def count_corpus(src, forms, log=None):
    counts = collections.Counter()
    tokens = 0
    lines = 0
    stream = Stream(src)
    for line in stream:
        lines += 1
        for tok in TOKEN.findall(line.lower()):
            tokens += 1
            t = tok.translate(APOS)
            if t in forms:
                counts[t] += 1
        if log and lines % 2_000_000 == 0:
            print(f"  {lines:,} lines, {tokens:,} tokens", file=log, flush=True)
    return {"lines": lines, "tokens": tokens, "truncated": stream.truncated, "counts": dict(counts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaikki", help="kaikki JSONL (url or path); omit to reuse the cached entries")
    ap.add_argument("--corpus", action="append", default=[], help="name=url-or-path of a subcorpus; repeatable")
    ap.add_argument("--work-dir", default=os.path.join(ROOT, "build", "stress-homographs"))
    ap.add_argument("--snapshot", required=True, help="the date of this run, recorded in the JSON")
    ap.add_argument("--min-count", type=int, default=20, help="a reading needs this many distinguishing-form hits before it can win")
    ap.add_argument("--min-ratio", type=float, default=1.5, help="the winner needs this many times the loser's hits")
    ap.add_argument("--lemmatizer", default="https://www.jakelawrence.xyz/api/lemmatize", help="the site's lemmatizer endpoint (token mode); '' to skip the VESUM check")
    args = ap.parse_args()
    os.makedirs(args.work_dir, exist_ok=True)

    snap = json.load(open(os.path.join(DATA, "stress.json"), encoding="utf-8"))
    seed = json.load(open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    list_lemmas = {nfc(r["lemma"]).translate(APOS).lower() for r in seed["rows"]}
    homographs = [r for r in snap["rows"] if r["status"] == "homograph" and r["pos"] != "PROPN"]
    wanted = {r["lemma"] for r in homographs}

    # every inflected form the thread-04 paradigms file lists, by lemma, so a
    # form another lemma also has can be struck from a homograph's evidence
    forms_by_lemma = collections.defaultdict(set)
    with gzip.open(os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "paradigms", "forms.csv.gz"), "rt", encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            cells = line.rstrip("\n").split(",")
            if len(cells) < 6:
                continue
            forms_by_lemma[nfc(cells[1]).translate(APOS).lower()].add(nfc(cells[3]).translate(APOS).replace(ACUTE, "").replace(GRAVE, "").lower())
    other_forms = {}
    for w in wanted:
        lw = w.lower()
        other_forms[lw] = set().union(*(f for l, f in forms_by_lemma.items() if l != lw))

    cache = os.path.join(args.work_dir, "kaikki-entries.json")
    if args.kaikki:
        k = read_kaikki(args.kaikki, wanted)
        json.dump(k, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"kaikki: {k['lines']:,} lines, {len(k['entries'])} of {len(wanted)} homograph lemmas have entries", flush=True)
    k = json.load(open(cache, encoding="utf-8"))

    # keyed by rank, not lemma: пора is on the list twice (noun and adverb)
    def make_plan(foreign_by_lemma):
        plan, forms = {}, set()
        for r in homographs:
            p = plan_for(r["lemma"], k["entries"].get(r["lemma"], []), list_lemmas, other_forms, k.get("owners", {}), foreign_by_lemma.get(r["lemma"], frozenset()))
            plan[r["rank"]] = {"lemma": r["lemma"], "pos": r["pos"], **p}
            for rd in p["readings"]:
                forms.update(rd["uniqueForms"])
        return plan, forms

    # pass one plans from kaikki alone; pass two strikes every candidate form
    # the lemmatizer reads as another word, and only then is a pair decidable
    plan, candidates = make_plan({})
    struck = 0
    if args.lemmatizer:
        lemmatized = lemmatize(candidates, args.lemmatizer, os.path.join(args.work_dir, "lemmatizer.json"))
        foreign = {}
        for p in plan.values():
            mine = set().union(*(set(rd["uniqueForms"]) for rd in p["readings"])) if p["readings"] else set()
            foreign[p["lemma"]] = frozenset(foreign_forms(p["lemma"], mine, lemmatized))
        struck = sum(len(v) for v in foreign.values())
        plan, _ = make_plan(foreign)
        print(f"lemmatizer: {len(candidates)} candidate forms, {struck} struck as another word's", flush=True)
    forms = set()
    for p in plan.values():
        if p["decidable"]:
            for rd in p["readings"]:
                forms.update(rd["uniqueForms"])
    dec = sum(1 for p in plan.values() if p["decidable"])
    print(f"plan: {len(plan)} homographs, {dec} decidable by spelling, {len(forms)} forms to count", flush=True)

    counts_path = os.path.join(args.work_dir, "counts.json")
    counts = json.load(open(counts_path, encoding="utf-8")) if os.path.exists(counts_path) else {}
    for spec in args.corpus:
        name, src = spec.split("=", 1)
        if name in counts and forms <= set(counts[name].get("forms", ())):
            print(f"corpus {name}: cached", flush=True)
            continue
        print(f"corpus {name}: streaming {src}", flush=True)
        counts[name] = {"source": src, "forms": sorted(forms), **count_corpus(src, forms, log=sys.stdout)}
        json.dump(counts, open(counts_path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"corpus {name}: {counts[name]['lines']:,} lines, {counts[name]['tokens']:,} tokens, {sum(counts[name]['counts'].values()):,} hits{' (TRUNCATED: the stream ended early)' if counts[name]['truncated'] else ''}", flush=True)

    total = collections.Counter()
    for c in counts.values():
        total.update(c["counts"])
    results = {}
    for rank, p in sorted(plan.items()):
        readings = []
        for rd in p["readings"]:
            per = {name: sum(c["counts"].get(f, 0) for f in rd["uniqueForms"]) for name, c in counts.items()}
            n = sum(total.get(f, 0) for f in rd["uniqueForms"])
            top = sorted(((total.get(f, 0), f) for f in rd["uniqueForms"]), reverse=True)[:5]
            readings.append({**rd, "hits": n, "hitsByCorpus": per, "topForms": [{"form": f, "hits": h} for h, f in top if h]})
        decision = {"primary": None, "why": p["why"]}
        if p["decidable"] and counts:
            ranked = sorted(readings, key=lambda x: -x["hits"])
            win, lose = ranked[0], ranked[1]
            if win["hits"] >= args.min_count and (lose["hits"] == 0 or win["hits"] / lose["hits"] >= args.min_ratio):
                decision = {"primary": win["stress"], "why": f"{win['hits']:,} against {lose['hits']:,} hits on the forms that differ in spelling"}
            else:
                decision = {"primary": None, "why": f"too close or too few: {win['hits']:,} against {lose['hits']:,} hits (floor {args.min_count}, ratio {args.min_ratio})"}
        results[str(rank)] = {"rank": rank, "lemma": p["lemma"], "pos": p["pos"], "decidable": p["decidable"], "readings": readings, "decision": decision}

    out = {
        "note": "The homograph corpus count behind the stress column: for each in-scope homograph, both en.wiktionary readings, the inflected forms that differ in spelling between them, and how often those forms occur across the UberText 2.0 subcorpora. The pure builder makes the reading with the larger count the primary (status homograph_corpus) and leaves a pair spelled alike in every form as homograph with the first en.wiktionary entry as primary. Generated by scripts/ukrainian-frequency/count-homographs.py; see stress-homographs.SOURCE.md.",
        "snapshot": args.snapshot,
        "kaikkiLines": k["lines"],
        "rule": {"minCount": args.min_count, "minRatio": args.min_ratio, "distinguishingForms": "forms spelled differently between the readings, minus the headword, minus any form that is itself a lemma on the list, minus bare aspect-partner entries, minus any form the thread-04 paradigms file lists for another lemma, minus any form or headword of any other word in en.wiktionary, minus any form the site's lemmatizer (VESUM) reads as another word", "lemmatizer": args.lemmatizer or None, "formsStruckByLemmatizer": struck},
        "corpora": {name: {"source": c["source"], "lines": c["lines"], "tokens": c["tokens"], "truncated": bool(c.get("truncated"))} for name, c in counts.items()},
        "summary": {
            "homographs": len(results),
            "decidableBySpelling": dec,
            "decided": sum(1 for r in results.values() if r["decision"]["primary"]),
            "flipped": sum(1 for r in results.values() if r["decision"]["primary"] and r["decision"]["primary"] != next(x["stress"] for x in snap["rows"] if x["rank"] == r["rank"])),
        },
        "results": results,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"]), flush=True)


if __name__ == "__main__":
    main()
