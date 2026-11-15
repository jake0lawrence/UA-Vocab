# ---------------------------------------------------------------------------
# Ukrainian Frequency - one-time provenance step: build the committed seed.
#
# This documents (and reproduces) how the committed snapshot at
#   src/data/ukrainian-frequency/ubertext-lemmas-top12k.json
# was extracted from the source lemma frequency dictionary. It is NOT run in the
# build or in CI (the build reads the committed snapshot). It exists so the
# derivation is transparent and repeatable.
#
# The committed snapshot is DERIVED aggregate counts (facts): a filtered top-N
# slice of the source dictionary's (lemma, POS, count, doc_count) columns. It is
# not the source corpus text.
#
# Reproduce:
#   1. curl -sSL -o ubertext_freq.csv.xz \
#        https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz
#   2. python3 scripts/ukrainian-frequency/extract-source.py ubertext_freq.csv.xz \
#        > src/data/ukrainian-frequency/ubertext-lemmas-top12k.json
#
# Source: UberText 2.0 lemma frequency dictionary (lang-uk).
# Citation: Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern
#   Ukrainian at Scale. Proc. 2nd Ukrainian NLP Workshop (UNLP), ACL.
# ---------------------------------------------------------------------------
import csv, lzma, re, sys, json

UK = re.compile(r"^[абвгґдеєжзиіїйклмнопрстуфхцчшщьюяАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ'’ʼ\-]+$")
# Universal Dependencies POS tags that are real linguistic words. Excludes X
# (foreign/unclassified), SYM, PUNCT, and numerals written as digits.
KEEP = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON", "DET", "NUM", "ADP", "CCONJ", "SCONJ", "PART", "INTJ"}
N = 12000
ACCESSED = "2026-07-14"


def main(path):
    total = 0
    buf = []
    with lzma.open(path, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r)  # header: lemma,pos,count,doc_count,freq_by_pos,freq_in_corpus,doc_frequency
        for rec in r:
            if len(rec) < 4:
                continue
            lemma, pos, count, doc_count = rec[0], rec[1], rec[2], rec[3]
            if pos not in KEEP:
                continue
            if not UK.match(lemma):
                continue
            # Drop single-character proper-noun / abbreviation noise, but keep
            # single-character real words (я, і, у).
            if len(lemma) == 1 and pos == "PROPN":
                continue
            try:
                c, dc = int(count), int(doc_count)
            except ValueError:
                continue
            total += c
            if len(buf) < 400000:  # bounded buffer; source is already count-desc
                buf.append((lemma, pos, c, dc))

    # Deterministic order: count desc, then lemma, then POS.
    buf.sort(key=lambda x: (-x[2], x[0], x[1]))
    top = buf[:N]

    snapshot = {
        "source": "UberText 2.0 lemma frequency dictionary (lang-uk)",
        "source_file": "ubertext_freq.csv.xz",
        "source_url": "https://lang.org.ua/static/downloads/ubertext2.0/dicts/ubertext_freq.csv.xz",
        "source_citation": "Chaplynskyi, D. (2023). Introducing UberText 2.0: A Corpus of Modern Ukrainian at Scale. Proc. 2nd Ukrainian NLP Workshop (UNLP), ACL.",
        "accessed": ACCESSED,
        "extraction": "Rows filtered to Ukrainian-Cyrillic-alphabetic lemmas with a linguistic UD POS tag (excludes X, SYM, PUNCT, numerals-as-digits, single-character proper nouns). Coverage denominator is the sum of raw occurrence counts over that filtered word-token universe. Top 12000 lemma+POS rows by count, ties broken by lemma then POS.",
        "pos_scheme": "Universal Dependencies (UD) v2",
        "word_token_universe_total": total,
        "n": len(top),
        "rows": [{"lemma": l, "pos": p, "count": c, "docs": dc} for (l, p, c, dc) in top],
    }
    json.dump(snapshot, sys.stdout, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 extract-source.py ubertext_freq.csv.xz > seed.json")
    main(sys.argv[1])
