#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 06: derive a lemma frequency list from ONE
# UberText 2.0 subcorpus, so two genres can be compared against each other.
#
# One-time, reproducible. NOT run in the build or in CI.
#
#   python3 scripts/ukrainian-frequency/genre-freq.py IN.bz2 OUT.json [MAX_TOKENS] [KEEP]
#
# WHY THIS EXISTS: thread 02 reports that 229 word entries of the A2 lexical
# minimum do not rank in the top 12,000 of this site's frequency list, and that
# the misses concentrate in food, hygiene and household vocabulary. That list is
# built on UberText 2.0's COMBINED corpus, which is dominated by its news
# subcorpus (3.5 GB of 5.1 GB). So the finding as stated is a claim about
# frequency lists in general, resting on evidence about one genre mix. This
# script is half of the test that separates the two.
#
# WHAT MAKES THE COMPARISON FAIR, and what does not:
#   - SAME COLLECTION. Both genres are UberText 2.0 subcorpora: same crawl, same
#     cleaning, same Russian-language filtering. A separate fiction corpus (the
#     Chtyvo library, say) would confound genre with collection and processing.
#   - SAME LEMMATIZER. Both sides go through pymorphy3 here. That is NOT the
#     lemmatizer lang-uk used for the shipped combined dictionary, so these ranks
#     are NEVER comparable to the shipped ranks and must never be mixed with
#     them. They are internally consistent, which is all the comparison needs.
#   - SAME SIZE. Corpus size drives how deep a frequency list reaches, so the
#     caller must pass MAX_TOKENS to cap both genres at the same token count.
#   - SAME SAMPLING SHAPE. KEEP is "num/den" (e.g. "1/2") and keeps that fraction
#     of lines spread across the WHOLE file. Reading a prefix instead would
#     confound genre with position in the collection, and a fiction prefix can be
#     one publisher or one era. A plain stride cannot hit an arbitrary fraction
#     (1/2 is 50 percent when 62.5 might be wanted), which is why this takes a
#     ratio rather than a step.
#
# COST: counts WORDFORM types first and lemmatizes only the distinct types, so
# the work scales with vocabulary (about 1M types) rather than tokens (about
# 10^8). Whole-subcorpus runs finish in minutes rather than hours.
#
# KNOWN LIMITATION, stated rather than hidden: pymorphy3 mis-lemmatizes a few
# high-frequency Ukrainian pronouns (its top-15 for fiction contains "йога" for
# "його" and "мен" for "мене"). This affects function words, not the content
# vocabulary the comparison is about, and it affects BOTH genres identically.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import bz2
import json
import re
import sys
import unicodedata
from collections import Counter

WORD = re.compile(r"[А-Яа-яЄєІіЇїҐґ’ʼ']+")
APOS = str.maketrans({"ʼ": "’", "'": "’", "`": "’", "´": "’"})


def norm(w):
    w = unicodedata.normalize("NFC", unicodedata.normalize("NFD", w).replace("́", ""))
    return w.translate(APOS).lower().strip("’")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__ or "usage: genre-freq.py IN.bz2 OUT.json [MAX_TOKENS] [KEEP]")
    src, out = sys.argv[1], sys.argv[2]
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    keep_num, keep_den = 1, 1
    if len(sys.argv) > 4:
        keep_num, keep_den = (int(x) for x in sys.argv[4].split("/"))

    opener = bz2.open if src.endswith(".bz2") else open
    forms = Counter()
    total = 0
    with opener(src, "rt", encoding="utf-8", errors="ignore") as fh:
        for i, line in enumerate(fh):
            if keep_den > 1 and (i % keep_den) >= keep_num:
                continue
            for m in WORD.findall(line):
                w = norm(m)
                if len(w) > 1:
                    forms[w] += 1
                    total += 1
            if cap and total >= cap:
                break
    print(f"[{src}] tokens={total:,} wordform types={len(forms):,}", flush=True)

    import pymorphy3
    morph = pymorphy3.MorphAnalyzer(lang="uk")
    lemmas = Counter()
    for form, n in forms.items():
        try:
            lemmas[norm(morph.parse(form)[0].normal_form)] += n
        except Exception:
            continue
    print(f"[{src}] lemma types={len(lemmas):,}", flush=True)

    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "source": src, "tokens": total, "keep": f"{keep_num}/{keep_den}",
            "formTypes": len(forms), "lemmaTypes": len(lemmas),
            "rows": lemmas.most_common(),
        }, fh, ensure_ascii=False)
    print(f"[{src}] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
