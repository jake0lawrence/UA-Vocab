#!/usr/bin/env python3
"""
Ukrainian Frequency, thread 06 (the text profiler): assemble the validation set.

Fetches level-marked Ukrainian passages from the open learn-ukrainian course
(https://learn-ukrainian.github.io, curriculum content CC BY-SA 4.0), keeps only
the Ukrainian-language prose blocks of each thematic module (dialogues, model
texts, worked examples), drops the pedagogy chrome (learner path, self-check,
textbook-check, summary sections, fill-in blanks, cross-references), and writes
src/data/ukrainian-frequency/profiler-validation.json.

The level of each text is asserted by the course, by which core track the
module sits in (a1 / a2 / b1). That is an independent assertion relative to this
profiler, but it is NOT a graded-reader publisher's claim: the course modules
are machine-drafted and audited by that project's own pipeline. The page says so.

Not run in build or CI (network). Usage:

    python3 scripts/ukrainian-frequency/fetch-profiler-validation.py
    python3 scripts/ukrainian-frequency/fetch-profiler-validation.py --from-dir <dir of saved html>

The module list is fixed below so a re-run is reproducible; a module that has
moved or vanished is reported and skipped, never guessed.
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date

BASE = "https://learn-ukrainian.github.io"
MODULES = {
    "A1": ["my-family", "who-am-i", "my-morning", "weather", "my-city", "at-the-cafe", "shopping",
            "free-time", "transport", "my-day", "around-the-city"],
    "A2": ["liudyna-i-stosunky", "shopping-and-health", "services-and-communication", "work-and-food",
            "home-and-daily-life", "telling-stories-and-travel", "education-and-work", "nature-and-traditions",
            "dozvillia-i-khobi", "preferences-and-choices"],
    "B1": ["people-and-relationships", "daily-life-and-routines", "work-and-career", "health-at-the-doctor",
            "restaurant-and-food", "shopping-and-services", "housing-and-renting", "traveling-ukraine",
            "nature-and-environment", "education-and-university", "places-and-locations",
            "leisure-culture-festivals", "society-and-media", "reading-literature"],
}
MIN_WORDS = 60
MAX_PER_LEVEL = 10
EXCLUDE_H2 = re.compile(r"Learner Path|Шлях учня|Textbook Check|Самоперев|Підсумок|Learn Ukrainian|Робота з помилками", re.I)
EXCLUDE_BLOCK = re.compile(r"^\(див\.|____|Сигнал:|^📚|^\(see ", re.I)
CYR = re.compile(r"[А-Яа-яЇїІіЄєҐґ]")
LAT = re.compile(r"[A-Za-z]")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jakelawrence.xyz ukrainian-frequency profiler validation (polite, one-off)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8")


def extract(page):
    page = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", page, flags=re.S)
    m = re.search(r"<main[^>]*>(.*?)</main>", page, flags=re.S)
    if m:
        page = m.group(1)
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", page, flags=re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))).strip() if title_m else ""
    keep = True
    blocks = []
    for mm in re.finditer(r"<(h[1-4]|p|li|blockquote|td|dd)[^>]*>(.*?)</\1>", page, flags=re.S):
        tag = mm.group(1)
        t = html.unescape(re.sub(r"<[^>]+>", "", mm.group(2))).strip()
        t = re.sub(r"\s+", " ", t)
        # dashes are normalized to a plain hyphen: punctuation is not part of the
        # lexical profile, and the repository's house rule forbids em dashes
        t = re.sub(r"[\u2014\u2015\u2012]", "-", t)
        if not t:
            continue
        if tag == "h2":
            keep = not EXCLUDE_H2.search(t)
            continue
        if tag in ("h1", "h3", "h4"):
            continue
        if not keep or EXCLUDE_BLOCK.search(t):
            continue
        cyr = len(CYR.findall(t))
        lat = len(LAT.findall(t))
        if cyr > 25 and cyr > 4 * lat:
            blocks.append(t)
    # de-duplicate while keeping order
    seen = set()
    out = []
    for b in blocks:
        if b in seen:
            continue
        seen.add(b)
        out.append(b)
    return title, out


def main():
    from_dir = None
    if "--from-dir" in sys.argv:
        from_dir = sys.argv[sys.argv.index("--from-dir") + 1]
    texts = []
    skipped = []
    for level, slugs in MODULES.items():
        rows = []
        for slug in slugs:
            url = f"{BASE}/{level.lower()}/{slug}/"
            try:
                if from_dir:
                    page = open(os.path.join(from_dir, f"{level.lower()}_{slug}.html"), encoding="utf-8").read()
                else:
                    page = fetch(url)
            except Exception as e:  # noqa: BLE001
                skipped.append({"level": level, "slug": slug, "reason": str(e)[:80]})
                continue
            title, blocks = extract(page)
            body = "\n\n".join(blocks)
            words = len(re.findall(r"[А-Яа-яЇїІіЄєҐґ][А-Яа-яЇїІіЄєҐґ'’ʼ́-]*", body))
            if words < MIN_WORDS or not title:
                skipped.append({"level": level, "slug": slug, "reason": f"only {words} Ukrainian words extracted"})
                continue
            rows.append({"id": f"{level.lower()}-{slug}", "level": level, "slug": slug, "title": title, "url": url,
                         "words": words, "blocks": len(blocks), "text": body})
        rows.sort(key=lambda r: slugs.index(r["slug"]))
        texts.extend(rows[:MAX_PER_LEVEL])
    out = {
        "snapshot": date.today().isoformat(),
        "source": "learn-ukrainian (Krisztian Koos and contributors), the open A1 to C2 Ukrainian course",
        "sourceUrl": BASE,
        "license": "CC-BY-SA-4.0 (curriculum content; LICENSE-CONTENT.md in the course repository)",
        "levelAssertedBy": "placement in the course's core CEFR track (a1 / a2 / b1), aligned by the course to the Ukrainian State Standard 2024",
        "caveat": "The course modules are machine-drafted and audited by that project's own review pipeline, not graded readers vetted by a testing body. The level is the course's assertion, independent of this profiler, and weaker than a published graded reader's.",
        "method": "For each thematic module page, keep the Ukrainian-language prose blocks (a block with more than 25 Cyrillic letters and more than four times as many Cyrillic as Latin letters) outside the learner-path, self-check, textbook-check, error-work and summary sections; drop fill-in blanks and cross-references; join in page order; em dashes normalized to a hyphen (punctuation is not profiled). Modules yielding fewer than 60 Ukrainian words are skipped, at most 10 per level.",
        "minWords": MIN_WORDS,
        "maxPerLevel": MAX_PER_LEVEL,
        "count": len(texts),
        "perLevel": {lvl: sum(1 for t in texts if t["level"] == lvl) for lvl in MODULES},
        "skipped": skipped,
        "texts": texts,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "data", "ukrainian-frequency", "profiler-validation.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("texts",)}, ensure_ascii=False, indent=1))
    for t in texts:
        print(t["level"], t["slug"], t["words"], "words", t["blocks"], "blocks")


if __name__ == "__main__":
    main()
