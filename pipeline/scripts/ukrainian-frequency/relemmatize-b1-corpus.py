#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, the B1 extension, stage 4: the nlp_uk RE-LEMMATIZATION
# (one-time, reproducible, NOT run in the build or CI).
#
# The pinned follow-up from the stage-3 dossier. The shipped usage tables
# (government, collocations, examples) were counted over a spaCy parse whose
# lemmas come from pymorphy3. PULS itself was built with nlp_uk, and thread
# 01's list carries lang-uk's own lemmatization, so the joins those tables
# depend on run on a convention that is nobody's. Mixing lemmatizers breaks
# PULS joins exactly on the edge cases that matter here: reflexive -ся verbs,
# participles against adjectives, aspect partners.
#
# This measures the gap rather than assuming it. It re-reads the SAME corpus
# slice under the SAME line filter the shipped parse used, keeps spaCy for the
# syntax it alone provides (dependencies, morphological Case), and replaces
# ONLY the lemma, per token, with the VESUM headword the nlp_uk pipeline gives
# (LanguageTool Ukrainian over a pinned VESUM dictionary, the core nlp_uk's
# TagText wraps, served by services/lemmatizer). Sentences go to the service
# one at a time in TOKEN mode, so every token keeps 1:1 alignment with the
# parse and the disambiguator sees the real sentence, with no cross-sentence
# bleed from batching.
#
# It answers one question: which convention lands more of this corpus on
# thread 01's list. That rate is the benchmark the SOURCE note names, and it
# decides whether the shipped tables are worth rebuilding. Nothing here
# rewrites them; the numbers come first.
#
# COUNTS ONLY leave this script. No corpus sentence is written anywhere.
#
# Reproduce (about 20 minutes on one CPU, service running on PORT):
#   cd services/lemmatizer && mvn -q package
#   PORT=8787 java -jar target/lemmatizer.jar &
#   python3 -m pip install spacy \
#     https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl
#   curl -sS --range 0-31000000 "https://lang.org.ua/static/downloads/ubertext2.0/wikipedia/sentenced/ubertext.wikipedia.filter_rus_gcld+short.text_only.txt.bz2" \
#     | bzcat 2>/dev/null | head -n 400000 > /tmp/wiki-400k.txt
#   python3 scripts/ukrainian-frequency/relemmatize-b1-corpus.py /tmp/wiki-400k.txt \
#     --service http://127.0.0.1:8787/lemmatize
#
# House rule: no em dashes.
# ---------------------------------------------------------------------------
import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import spacy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")

LIST_VERSION = "v0.2.0"  # keep in step with SPINE in src/lib/ukrainian-frequency/release.mjs
SNAPSHOT_DATE = "2026-09-17"
CONTENT = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
KEEP_DISAGREEMENTS = 400          # the most frequent ones, for the published table
WORKERS = 8

seed = json.load(open(f"{DATA}/ubertext-lemmas-top12k.json", encoding="utf-8"))
puls = json.load(open(f"{DATA}/puls-cefr.json", encoding="utf-8"))


def fold(s):
    return s.replace("'", "’").replace("ʼ", "’").replace("́", "")


LIST_LEMMAS = {fold(r["lemma"].lower()) for r in seed["rows"]}
LIST_POS = {(fold(r["lemma"].lower()), r["pos"]) for r in seed["rows"]}
B1_LEMMAS = {fold(r["lemma"].lower()) for r in puls["rows"] if r["level"] == "B1"}

# The shipped parse's line filter, copied so the slice is the same one.
LATIN_MARKUP = re.compile(r"[A-Za-z]{4,}|\d{4}|[|{}\[\]=]")


def texts(path):
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if len(s) < 30 or len(s) > 400 or s.count(" ") < 5:
            continue
        if LATIN_MARKUP.search(s):
            continue
        yield s


class Service:
    """The nlp_uk pipeline over HTTP, one sentence per request, token mode."""

    def __init__(self, url, token=None):
        self.url = url
        self.headers = {"content-type": "application/json"}
        if token:
            self.headers["authorization"] = f"Bearer {token}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.calls = 0
        self.failures = 0

    def lemmas(self, tokens):
        """The VESUM headword per token, aligned 1:1, None where unknown."""
        body = json.dumps({"tokens": tokens}).encode()
        req = urllib.request.Request(self.url, data=body, headers=self.headers)
        for attempt in range(3):
            try:
                with self.opener.open(req, timeout=120) as r:
                    out = json.load(r)
                self.calls += 1
                got = out.get("tokens") or []
                if len(got) != len(tokens):
                    self.failures += 1
                    return None
                return [(t.get("lemma"), t.get("pos"), bool(t.get("ambiguous")), bool(t.get("known"))) for t in got]
            except Exception:
                if attempt == 2:
                    self.failures += 1
                    return None
                time.sleep(0.5 * (attempt + 1))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", nargs="?", help="the plain-text 400000-line prefix")
    ap.add_argument("--service", default="http://127.0.0.1:8787/lemmatize")
    ap.add_argument("--service-token", default=os.environ.get("LEMMATIZER_SERVICE_TOKEN"))
    ap.add_argument("--limit", type=int, default=0, help="stop after N sentences (smoke test)")
    ap.add_argument("--out", default=os.path.join(DATA, "b1-usage.relemmatize.json"))
    ap.add_argument("--rebuild", action="store_true",
                    help="write the browser tier from the committed artifact; no corpus, no service")
    args = ap.parse_args()

    if args.rebuild:
        full = json.load(open(args.out, encoding="utf-8"))
        write_browser_tier(full)
        h = full["headline"]
        print(f"browser tier rebuilt: {h['agreePct']} percent agree, "
              f"{h['onListPymorphyPct']} against {h['onListNlpUkPct']} percent on the list")
        return

    if not args.corpus:
        sys.exit("give the corpus prefix, or --rebuild to write the browser tier from the artifact")
    svc = Service(args.service, args.service_token)
    nlp = spacy.load("uk_core_news_sm", disable=["ner"])

    stats = collections.Counter()
    per_pos = collections.defaultdict(collections.Counter)   # spaCy POS -> agree/total
    disagree = collections.Counter()                          # (form, pos, pymorphy, nlpuk) -> n
    classes = collections.Counter()                           # the named edge cases
    onlist = collections.Counter()
    t0 = time.time()

    def analyze(doc):
        toks = [t for t in doc if not t.is_punct and not t.is_space]
        if not toks:
            return None
        return toks, svc.lemmas([t.text for t in toks])

    reported = [0]
    stream = texts(args.corpus)
    if args.limit:
        stream = (s for i, s in enumerate(stream) if i < args.limit)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        pending = []
        for doc in nlp.pipe(stream, batch_size=64):
            pending.append(pool.submit(analyze, doc))
            if len(pending) < WORKERS * 16:
                continue
            drain(pending, stats, per_pos, disagree, classes, onlist)
            pending = []
            # a drain lands wherever it lands, so report on CROSSING a
            # threshold rather than hitting one exactly (the modulo version
            # printed nothing at all for the whole run)
            if stats["sentences"] // 20000 > reported[0]:
                reported[0] = stats["sentences"] // 20000
                print(f"  {stats['sentences']} sentences, {stats['tokens']} tokens, "
                      f"{round(time.time()-t0)}s", file=sys.stderr, flush=True)
        drain(pending, stats, per_pos, disagree, classes, onlist)

    out = build(stats, per_pos, disagree, classes, onlist, svc, time.time() - t0)
    check_gap_accounting(out)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    # The browser tier is written to a fixed path, so a --limit smoke run must
    # not touch it: a 3,000-sentence probe once overwrote the committed tier
    # with its own figures while the real run was still going.
    if args.limit:
        print(f"smoke run ({args.limit} sentences): browser tier NOT written")
    else:
        write_browser_tier(out)
    h = out["headline"]
    print(f"sentences {stats['sentences']}, tokens {stats['tokens']}, "
          f"service calls {svc.calls} ({svc.failures} failed)")
    print(f"lemma agreement {h['agreePct']} percent; content tokens on the list: "
          f"pymorphy3 {h['onListPymorphyPct']} percent, nlp_uk {h['onListNlpUkPct']} percent "
          f"({h['verdict']})")


def drain(pending, stats, per_pos, disagree, classes, onlist):
    for fut in pending:
        got = fut.result()
        if not got:
            continue
        toks, analysis = got
        stats["sentences"] += 1
        if analysis is None:
            stats["sentencesUnanalyzed"] += 1
            continue
        for i, (t, (lemma, pos, ambiguous, known)) in enumerate(zip(toks, analysis)):
            py = fold(t.lemma_.lower())
            uk = fold((lemma or "").lower())
            stats["tokens"] += 1
            if ambiguous:
                stats["ambiguous"] += 1
            if not known:
                stats["unknownToVesum"] += 1
            agree = bool(uk) and py == uk
            stats["agree"] += 1 if agree else 0
            per_pos[t.pos_]["total"] += 1
            per_pos[t.pos_]["agree"] += 1 if agree else 0
            if t.pos_ in CONTENT:
                onlist["content"] += 1
                if not uk:
                    onlist["nlpUkNoLemma"] += 1
                # The gap is a CONTENT-token figure, so the two directions
                # that make it up have to be counted over content tokens too.
                # The disagreementClasses counters below run over every part of
                # speech, which is a different population and cannot reconcile
                # with this gap: that mistake once got published as an
                # explanation of it.
                py_on, uk_on = py in LIST_LEMMAS, uk in LIST_LEMMAS
                if py_on and not uk_on:
                    onlist["contentMovedOff"] += 1
                elif uk_on and not py_on:
                    onlist["contentMovedOn"] += 1
                if py in LIST_LEMMAS:
                    onlist["pymorphy"] += 1
                if uk in LIST_LEMMAS:
                    onlist["nlpUk"] += 1
                if (py, t.pos_) in LIST_POS:
                    onlist["pymorphyPos"] += 1
                if (uk, t.pos_) in LIST_POS:
                    onlist["nlpUkPos"] += 1
                if py in B1_LEMMAS:
                    onlist["pymorphyB1"] += 1
                if uk in B1_LEMMAS:
                    onlist["nlpUkB1"] += 1
            if agree or not uk:
                continue
            disagree[(t.text.lower(), t.pos_, py, uk)] += 1
            # the three classes the plan named, plus the one the probe found
            if py.endswith("ся") != uk.endswith("ся"):
                classes["reflexiveSuffix"] += 1
            if t.pos_ == "ADJ" and uk in LIST_LEMMAS and py not in LIST_LEMMAS:
                classes["participleAsAdjective"] += 1
            if i == 0 and t.text[:1].isupper():
                classes["sentenceInitialCapital"] += 1
            if py in LIST_LEMMAS and uk not in LIST_LEMMAS:
                classes["pymorphyOnListOnly"] += 1
            if uk in LIST_LEMMAS and py not in LIST_LEMMAS:
                classes["nlpUkOnListOnly"] += 1


def build(stats, per_pos, disagree, classes, onlist, svc, seconds):
    tokens = stats["tokens"] or 1
    content = onlist["content"] or 1
    pct = lambda n, d: round(1000 * n / (d or 1)) / 10
    top = disagree.most_common(KEEP_DISAGREEMENTS)
    return {
        "snapshot": SNAPSHOT_DATE,
        # the list the on-list flags were computed against; the test checks the
        # sample against that list, so a list refresh does not fail a run that
        # has not been repeated against the service
        "listVersion": LIST_VERSION,
        "question": "The shipped usage tables carry pymorphy3 lemmas; PULS was built with nlp_uk and thread 01's list carries lang-uk's own lemmatization. This measures how far the two conventions differ over the same corpus slice, and which one lands more of it on the list.",
        "method": "The same 400000-line prefix of UberText 2.0's Wikipedia subcorpus under the same clean-sentence filter the shipped parse used. spaCy uk_core_news_sm 3.8.0 supplies tokenization, part of speech and dependencies; the lemma is replaced per token by the VESUM headword from services/lemmatizer (LanguageTool Ukrainian over a pinned VESUM dictionary, the core nlp_uk's TagText wraps). One request per sentence in token mode, so alignment is 1:1 and the disambiguator sees the real sentence with no cross-sentence bleed.",
        "pipelines": {
            "parse": "spaCy uk_core_news_sm 3.8.0 (UD Ukrainian-IU; pymorphy3 lemmas)",
            "nlpUk": "LanguageTool Ukrainian 6.8 over morfologik-ukrainian-lt 6.8.0 (VESUM 6.8.0), rule-based disambiguator; nlp_uk's statistical and semantic extras not applied",
        },
        "note": "COUNTS ONLY. No corpus sentence is recorded here. The disagreement table is the most frequent forms, so it is a sample and is labeled one.",
        "corpus": {
            "sentences": stats["sentences"],
            "sentencesUnanalyzed": stats["sentencesUnanalyzed"],
            "tokens": stats["tokens"],
            "serviceCalls": svc.calls,
            "serviceFailures": svc.failures,
            "seconds": round(seconds),
        },
        "agreement": {
            "tokens": stats["tokens"],
            "agree": stats["agree"],
            "disagree": stats["tokens"] - stats["agree"],
            "agreePct": pct(stats["agree"], tokens),
            "ambiguous": stats["ambiguous"],
            "ambiguousPct": pct(stats["ambiguous"], tokens),
            "unknownToVesum": stats["unknownToVesum"],
            "unknownToVesumPct": pct(stats["unknownToVesum"], tokens),
        },
        "perPos": {
            pos: {"total": c["total"], "agree": c["agree"], "agreePct": pct(c["agree"], c["total"])}
            for pos, c in sorted(per_pos.items(), key=lambda kv: -kv[1]["total"])
        },
        "onList": {
            "contentTokens": onlist["content"],
            "pymorphy": onlist["pymorphy"],
            "nlpUk": onlist["nlpUk"],
            "pymorphyPct": pct(onlist["pymorphy"], content),
            "nlpUkPct": pct(onlist["nlpUk"], content),
            "pymorphyWithPos": onlist["pymorphyPos"],
            "nlpUkWithPos": onlist["nlpUkPos"],
            "pymorphyWithPosPct": pct(onlist["pymorphyPos"], content),
            "nlpUkWithPosPct": pct(onlist["nlpUkPos"], content),
            "pymorphyB1": onlist["pymorphyB1"],
            "nlpUkB1": onlist["nlpUkB1"],
            "gap": onlist["pymorphy"] - onlist["nlpUk"],
            "nlpUkNoLemma": onlist["nlpUkNoLemma"],
        },
        "gapAccounting": {
            "gap": onlist["pymorphy"] - onlist["nlpUk"],
            "movedOff": onlist["contentMovedOff"],
            "movedOn": onlist["contentMovedOn"],
            "note": "the on-list gap, token by token, over the content tokens the gap is measured on: a content token whose pymorphy3 lemma is on the list and whose nlp_uk lemma is not moves one off, the reverse moves one on, and the two differ by exactly the gap. The disagreementClasses counters are NOT these: they run over every part of speech, so they describe the disagreements rather than the gap.",
        },
        "disagreementClasses": dict(sorted(classes.items())),
        "disagreementClassesNote": "counted over every part of speech and over disagreeing tokens only, so pymorphyOnListOnly and nlpUkOnListOnly describe the disagreements, NOT the content-token on-list gap. Read gapAccounting for that.",
        "disagreementsKept": len(top),
        "disagreementsTotal": len(disagree),
        "disagreements": [
            {"form": f, "pos": p, "pymorphy": py, "nlpUk": uk, "n": n,
             "pymorphyOnList": py in LIST_LEMMAS, "nlpUkOnList": uk in LIST_LEMMAS}
            for (f, p, py, uk), n in top
        ],
        "headline": {
            "agreePct": pct(stats["agree"], tokens),
            "onListPymorphyPct": pct(onlist["pymorphy"], content),
            "onListNlpUkPct": pct(onlist["nlpUk"], content),
            "delta": round(pct(onlist["nlpUk"], content) - pct(onlist["pymorphy"], content), 1),
            "verdict": verdict(onlist, content),
        },
    }


SAMPLE = 10


def write_browser_tier(full):
    """The slim tier the page reads: aggregates, the verdict, a small sample.

    The 400-row disagreement table stays in src/data; the page shows the ten
    most frequent, which is enough to see WHY the conventions differ without
    shipping a lexicon to the browser.
    """
    slim = {k: v for k, v in full.items() if k not in ("disagreements", "perPos")}
    slim["perPos"] = dict(list(full["perPos"].items())[:8])
    # Which class agrees least, derived rather than remembered. The first
    # write-up of this called proper nouns the worst class from memory when
    # pronouns and determiners are both lower. A sample floor keeps a
    # 300-token punctuation class from taking the title.
    floor = 1000
    eligible = [(pos, c) for pos, c in full["perPos"].items() if c["total"] >= floor]
    worst = min(eligible, key=lambda kv: kv[1]["agreePct"])
    slim["lowestAgreement"] = {
        "pos": worst[0], "agreePct": worst[1]["agreePct"], "total": worst[1]["total"],
        "minSample": floor,
        "ranking": [{"pos": pos, "agreePct": c["agreePct"], "total": c["total"]}
                    for pos, c in sorted(eligible, key=lambda kv: kv[1]["agreePct"])[:5]],
    }
    slim["sample"] = full["disagreements"][:SAMPLE]
    body = (
        "// GENERATED by scripts/ukrainian-frequency/relemmatize-b1-corpus.py - do not edit by hand.\n"
        "// Browser-safe tier of the nlp_uk RE-LEMMATIZATION (stage 4's pinned follow-up): how far\n"
        "// the shipped usage tables' pymorphy3 lemma convention differs from the nlp_uk / VESUM one\n"
        "// PULS was built with, measured over the same corpus slice. Counts only; the full table\n"
        "// (every disagreement type and every part of speech) is\n"
        "// src/data/ukrainian-frequency/b1-usage.relemmatize.json.\n"
        "export const B1_RELEMMATIZE = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(ROOT, "src", "lib", "ukrainian-frequency", "b1-relemmatize.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)


def check_gap_accounting(full):
    """The gap must be fully explained, or the explanation is not one.

    Raises rather than shipping a figure whose parts do not sum, because the
    first version of this script published a class net of 5,973 as "the whole
    of" a 9,019-token gap.
    """
    g = full["gapAccounting"]
    parts = g["movedOff"] - g["movedOn"]
    if parts != g["gap"]:
        raise SystemExit(
            f"gap accounting does not close: {g['movedOff']} off - "
            f"{g['movedOn']} on = {parts}, but the gap is {g['gap']}"
        )
    g["closes"] = True


def verdict(onlist, content):
    a = onlist["pymorphy"] / (content or 1)
    b = onlist["nlpUk"] / (content or 1)
    if abs(b - a) < 0.005:
        return "the two conventions reconcile with the list equally well; a rebuild would move nothing"
    return ("nlp_uk reconciles better with the list" if b > a
            else "pymorphy3 reconciles better with the list")


if __name__ == "__main__":
    main()
