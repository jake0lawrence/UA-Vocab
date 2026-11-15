#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, thread 02: read the published A2 lexical minimum out of
# its own PDF and write the committed source snapshot borodin-a2.raw.json.
#
# SOURCE: "1000 i 1 slovo" (A2), Kseniia Borodin and Olesia Lazarenko,
# Europa-Universitat Viadrina Frankfurt (Oder), 2026, 108 pages.
# DOI 10.11584/opus4-1448, URN urn:nbn:de:kobv:521-opus4-14485.
# License CC-BY-4.0, so the factual word list may be extracted and republished
# with attribution. Only the factual list is taken: no usage examples, no
# grammatical prose, no other content of the guide is reproduced.
#
# WHY A PDF PARSER: the A1 volume reached us as a spreadsheet (one column, 944
# lines) and its snapshot is that column verbatim. The A2 volume is published as
# a typeset book, so the "machine-readable list" has to be recovered from the
# typesetting. This script is that one-time step, committed so the snapshot is
# reproducible rather than asserted. It is NOT run in the build or in CI; the
# 2.3 MB PDF is not vendored (fetch it from the DOI above).
#
#   python3 scripts/ukrainian-frequency/parse-borodin-a2-pdf.py path/to/Borodin_Lazarenko.pdf
#
# HOW THE BOOK IS LAID OUT, and what that forces:
#   - Two sections. The ALPHABETICAL REGISTER (one entry per headword, with
#     stress marks, grammar notes and a usage example) and the THEMATIC
#     DICTIONARY (the same vocabulary regrouped under topic headings, printed
#     without stress marks and without grammar). Both are extracted; the
#     thematic index is the axis the A1 list never had.
#   - Two columns. In the register the left column (x0 < 285pt) carries the
#     headword and its grammar; the right column carries the usage example.
#     Only the left column is read. The examples are the authors' prose and are
#     deliberately left in the book.
#   - Stress marks are combining acutes with zero advance width, and the fonts
#     sometimes advance the text position across them. Reading pdfminer's
#     word-margin output yields phantom spaces inside words ("безлакто зний"),
#     so lines are rebuilt from glyph geometry instead: gaps are measured
#     between glyphs that actually have width, and a space is emitted only for a
#     real space glyph or a gap wider than GAP_PT.
#   - Entry boundaries are vertical, not typographic. A new entry starts after a
#     paragraph gap (dy >= NEW_ENTRY_DY); the tighter leading below it belongs to
#     that entry (a wrapped headword, a "(...)" grammar note, or a "-> perfective"
#     line). The gap compresses at the foot of a page, which is why the threshold
#     is calibrated to the measured distribution rather than to the nominal
#     paragraph spacing.
#
# WHAT IS AND IS NOT NORMALIZED:
#   - Headword text is kept verbatim, stress marks included.
#   - A perfective partner printed on its own "->" line is folded into the
#     entry with the en-dash separator the A1 snapshot and the book's own
#     thematic section both use for aspect pairs, so the shared candidate
#     parser reads it without a special case. This is the
#     one structural change made to the printed text, and it is recorded in
#     borodin-a2.SOURCE.md.
#   - Grammar notes are captured per entry but kept OUT of the entry string;
#     they are the authors' pedagogical content, not the word list.
#
# House rule: no em-dashes in the files this writes.
# ---------------------------------------------------------------------------

import json
import os
import re
import sys
import unicodedata

try:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextContainer, LTTextLine
except ImportError:  # pragma: no cover - documented one-time dependency
    sys.exit("needs pdfminer.six:  python3 -m pip install pdfminer.six")

COLUMN_SPLIT_PT = 285.0   # left (headword) column vs right (example) column
GAP_PT = 1.2              # glyph gap that counts as a space at 12pt
NEW_ENTRY_DY = 17.0       # paragraph gap above a new register entry
# Measured over the whole register, the leading is cleanly bimodal: lines that
# continue an entry sit at dy <= 14, entries open at dy >= 20, and nothing lands
# in between. 17 is the middle of that empty band.
MARKS = {"́", "̀"}
# The typesetter sets the antonym marker in Symbol, which arrives as a
# private-use codepoint; the authors print it as "not equal".
GLYPH_FIXES = {"": "≠", "": "→"}

CYRILLIC_UPPER = re.compile(r"^[А-ЯЄІЇҐ]$")
THEMATIC_HEADING = "ТЕМАТИЧНИЙ СЛОВНИК"
ABBREVIATIONS_HEADING = "СПИСОК УМОВНИХ ПОЗНАЧЕНЬ"
REGISTER_HEADING = "АЛФАВІТНИЙ СЛОВНИК"


def line_text(line):
    """Rebuild a text line from glyph geometry, immune to the stress-mark
    advance that makes pdfminer's own word splitting insert phantom spaces."""
    out = []
    prev_x1 = None
    for c in line:
        if not isinstance(c, LTChar):
            continue
        t = GLYPH_FIXES.get(c.get_text(), c.get_text())
        if t in MARKS or c.width == 0:
            out.append(t)
            continue
        if t.isspace():
            if out and not out[-1].isspace():
                out.append(" ")
            prev_x1 = c.x1
            continue
        if prev_x1 is not None and c.x0 - prev_x1 > GAP_PT:
            if out and not out[-1].isspace():
                out.append(" ")
        out.append(t)
        prev_x1 = c.x1
    return "".join(out).strip()


def is_bold(line):
    return any(
        isinstance(c, LTChar) and "Bold" in c.fontname and not c.get_text().isspace()
        for c in line
    )


def page_lines(page, left_only):
    rows = []
    for element in page:
        if not isinstance(element, LTTextContainer):
            continue
        for line in element:
            if not isinstance(line, LTTextLine):
                continue
            if left_only and line.x0 >= COLUMN_SPLIT_PT:
                continue
            text = line_text(line)
            if text:
                rows.append({
                    "y": line.y1,
                    "x": line.x0,
                    "text": text,
                    "bold": is_bold(line),
                })
    rows.sort(key=lambda r: (-r["y"], r["x"]))
    return rows


def parse_register(pages):
    """Alphabetical register -> [{entry, grammar[], sectionLetter}] in book order."""
    entries = []
    section = None
    for rows in pages:
        prev_y = None
        force_new = True
        for row in rows:
            text = row["text"]
            dy = (prev_y - row["y"]) if prev_y is not None else None
            prev_y = row["y"]
            if text.isdigit() or text.startswith(REGISTER_HEADING):
                force_new = True
                continue
            if CYRILLIC_UPPER.match(text):
                # An alphabet divider. It sits tight above the first entry of its
                # letter, so without this the entry would read as a wrapped line.
                section = text
                force_new = True
                continue
            starts_block = force_new or dy is None or dy >= NEW_ENTRY_DY
            force_new = False
            if starts_block and not text.startswith(("(", "→")):
                entries.append({"entry": text, "grammar": [], "section": section})
                continue
            if not entries:
                continue
            current = entries[-1]
            if text.startswith("→"):
                partner = text.lstrip("→").strip()
                if partner:
                    current["entry"] = f"{current['entry']} \u2013 {partner}"
            elif text.startswith("("):
                current["grammar"].append(text)
            elif current["grammar"]:
                # continuation of a wrapped grammar note
                current["grammar"][-1] = f"{current['grammar'][-1]} {text}"
            else:
                # continuation of a wrapped headword
                current["entry"] = f"{current['entry']} {text}"
    return entries


def parse_thematic(pages, register_entries):
    """Thematic dictionary -> [{theme, words[]}] in book order.

    These pages set the same vocabulary in two columns under bold topic
    headings, one unit per line, without stress marks. Headings are typeset in
    bold and appear only in the left column, so a heading opens a theme that
    owns every line below it (in BOTH columns) until the next heading, and a
    theme runs on across a page break until a new heading appears. Reading order
    inside a theme is left column top to bottom, then right column, which is how
    the authors' part-of-speech grouping reads.
    """
    known = {_match_key(e) for e in register_entries}
    themes = []
    for rows in pages:
        headings = [r for r in rows if r["bold"] and r["x"] < COLUMN_SPLIT_PT]
        headings.sort(key=lambda r: -r["y"])
        for i, heading in enumerate(headings):
            floor = headings[i + 1]["y"] if i + 1 < len(headings) else float("-inf")
            body = [
                r for r in rows
                if not r["bold"] and floor < r["y"] < heading["y"] and not r["text"].isdigit()
            ]
            body.sort(key=lambda r: (r["x"] >= COLUMN_SPLIT_PT, -r["y"]))
            if heading["text"].startswith(THEMATIC_HEADING):
                continue
            themes.append({"theme": heading["text"], "words": [r["text"] for r in body]})
        if not headings:
            # A theme continued onto this page: everything belongs to the last one.
            body = [r for r in rows if not r["text"].isdigit() and not r["bold"]]
            body.sort(key=lambda r: (r["x"] >= COLUMN_SPLIT_PT, -r["y"]))
            if themes:
                themes[-1]["words"].extend(r["text"] for r in body)
            continue
        # Lines above the first heading continue the previous page's theme.
        top = headings[0]
        spill = [
            r for r in rows
            if not r["bold"] and r["y"] > top["y"] and not r["text"].isdigit()
            and THEMATIC_HEADING not in r["text"]
        ]
        if spill and len(themes) > len(headings):
            spill.sort(key=lambda r: (r["x"] >= COLUMN_SPLIT_PT, -r["y"]))
            themes[-len(headings) - 1]["words"].extend(r["text"] for r in spill)
    for theme in themes:
        theme["words"] = _rejoin_wraps(theme["words"], known)
    return themes


def _match_key(text):
    """Fold a printed unit to the form used only for spotting wrapped lines:
    stress marks dropped, apostrophe variants unified, whitespace collapsed."""
    text = unicodedata.normalize("NFD", text).replace("́", "").replace("̀", "")
    text = unicodedata.normalize("NFC", text)
    for ch in "ʼ’‘`´":
        text = text.replace(ch, "'")
    return " ".join(text.split()).lower()


def _rejoin_wraps(words, known):
    """The thematic columns set one unit per line, so a unit too wide for the
    column silently becomes two lines. Two repairs, both evidence-based rather
    than guessed: a line carrying a ')' it never opened continues its
    predecessor, and a line whose join with its predecessor matches a register
    entry (while the line alone matches nothing) was a wrap of that entry."""
    out = []
    for word in words:
        if out:
            unbalanced = word.count(")") > word.count("(")
            joined = f"{out[-1]} {word}"
            verified = _match_key(joined) in known and _match_key(word) not in known
            if unbalanced or verified:
                out[-1] = joined
                continue
        out.append(word)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__ or "usage: parse-borodin-a2-pdf.py path/to/Borodin_Lazarenko.pdf")
    pdf_path = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    out_path = os.path.join(repo_root, "src", "data", "ukrainian-frequency", "borodin-a2.raw.json")

    # One pass: keep every page's left column and, separately, every page's full
    # text, so the section boundaries can be found without a second read.
    left_pages, full_pages = [], []
    for page in extract_pages(pdf_path):
        left_pages.append(page_lines(page, left_only=True))
        full_pages.append(page_lines(page, left_only=False))

    # The register carries no heading of its own: it opens on the page after the
    # list of abbreviations and closes where the thematic dictionary opens.
    register_start = None
    thematic_start = None
    thematic_end = len(full_pages)
    for i, rows in enumerate(full_pages):
        joined = " ".join(r["text"] for r in rows)
        if register_start is None and ABBREVIATIONS_HEADING in joined:
            register_start = i + 1
        if thematic_start is None and THEMATIC_HEADING in joined:
            thematic_start = i
    if register_start is None or thematic_start is None:
        sys.exit("could not find the section headings; is this the right PDF?")
    for i in range(thematic_start, len(full_pages)):
        joined = " ".join(r["text"] for r in full_pages[i])
        if "Kseniia Borodin" in joined and "PhD" in joined:
            thematic_end = i
            break

    register = parse_register(left_pages[register_start:thematic_start])
    thematic = parse_thematic(full_pages[thematic_start:thematic_end], [e["entry"] for e in register])

    raw = {
        "source": "1000 i 1 slovo: Lexical Minimum in Ukrainian as a Foreign Language, Level A2 (Borodin, Lazarenko)",
        "sourceUrl": "https://doi.org/10.11584/opus4-1448",
        "urn": "urn:nbn:de:kobv:521-opus4-14485",
        "license": "CC-BY-4.0",
        "publisher": "Europa-Universitat Viadrina Frankfurt (Oder)",
        "published": "2026-05-08",
        "extracted": "2026-07-28",
        "extractor": "scripts/ukrainian-frequency/parse-borodin-a2-pdf.py",
        "note": (
            "Factual word list only, extracted from the CC-BY-4.0 publication. Usage "
            "examples, grammatical prose and all other content of the guide are left in "
            "the book. Perfective partners printed on a '->' line are folded into the "
            "entry with ' - ', matching the A1 snapshot's aspect-pair form."
        ),
        "registerPages": [register_start + 1, thematic_start],
        "thematicPages": [thematic_start + 1, thematic_end],
        "entryCount": len(register),
        "themeCount": len(thematic),
        "thematicUnits": sum(len(t["words"]) for t in thematic),
        "entries": [e["entry"] for e in register],
        "grammar": {e["entry"]: e["grammar"] for e in register if e["grammar"]},
        "themes": thematic,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    print(f"register pages {register_start + 1}-{thematic_start}, thematic pages {thematic_start + 1}-{thematic_end}")
    print(f"register entries: {len(register)} ({sum(1 for e in register if e['grammar'])} with grammar notes)")
    print(f"themes: {len(thematic)} covering {sum(len(t['words']) for t in thematic)} thematic lines")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
