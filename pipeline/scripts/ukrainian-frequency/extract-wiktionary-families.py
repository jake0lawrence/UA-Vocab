#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Ukrainian Frequency, B1 extension: the Wiktionary derived-term family graph.
#
# The open fallback for the one PULS ask that has no public route yet: the
# profile's 1,100 word families ("to be added in future updates" on the
# platform, eLex 2025 section 4.4). This builds a derivational family graph
# from what IS open, the English Wiktionary's Ukrainian entries as extracted
# by kaikki.org (wiktextract), and joins it onto the top-12,000 list.
#
# EDGES, and which ones make a family:
#   derived   headword A lists B under "Derived terms"            (used)
#   affix     B's etymology is an affix template over the single
#             full-word base A ({{af|uk|ви-|давати}} and kin)     (used)
#   aspect    B is A's listed perfective or imperfective partner   (used)
#   related   headword A lists B under "Related terms"            (recorded,
#             NOT used: on this dump it merges unrelated roots through shared
#             suffixes and cognate lists into families of hundreds)
# A family is a connected component of the used edges over NON-COMPOUND
# nodes. Compounds are excluded on purpose: PULS families are nests around
# one root, and Wiktionary lists a compound under both of its roots (високий
# and оплачувати both list високооплачуваний), so one compound node would
# chain two nests into one. A node is a compound when its etymology template
# names two or more full-word bases, or, where no etymology is recorded, when
# two headwords with different stems both list it as derived and the word
# carries both stems (the string evidence).
#
# NODE FILTER: one Cyrillic token of three letters or more, stress stripped,
# apostrophes normalized. Reconstructions (*bogъ), bare affixes (-ство),
# Latin and multiword entries are out. An affix base that Wiktionary knows
# only as a function word (prepositions and the like) is out too, so вгору
# does not chain every в- word into one family.
#
# OUTPUTS:
#   src/data/ukrainian-frequency/wiktionary-families.json     every family that
#       touches the list, all its Wiktionary members, the list members with
#       rank / POS / validated level, and the aggregates the page verifies
#   public/downloads/ukrainian-frequency/wiktionary-families/families.csv
#   public/downloads/ukrainian-frequency/wiktionary-families/edges.csv
#   src/lib/ukrainian-frequency/wiktionary-families.data.mjs  browser tier
#
# Honesty rules: every edge is taken verbatim from a Wiktionary entry; no
# family is inferred from spelling; the validated level beside a list member
# is the PULS overlay's (by permission) and is reported, never used to shape
# the graph. The "same level" statistic is a finding about the profile, not a
# property the graph was built to have.
#
# Usage:
#   python3 scripts/ukrainian-frequency/extract-wiktionary-families.py \
#       --dump kaikki.org-dictionary-Ukrainian.jsonl --dump-date 2026-10-30
# House rule: no em-dashes in anything this writes.
# ---------------------------------------------------------------------------
import argparse
import collections
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "data", "ukrainian-frequency")
LIB = os.path.join(ROOT, "src", "lib", "ukrainian-frequency")
DL = os.path.join(ROOT, "public", "downloads", "ukrainian-frequency", "wiktionary-families")

SNAPSHOT_DATE = "2026-11-20"
# --relabel refreshes the validated levels beside list members from the
# current overlay without the dump; stamped so a reader can tell the two apart.
RELABEL_DATE = "2026-09-24"
CYR = re.compile(r"^[а-яґєіїь']+$")
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
LEVEL_IDX = {l: i for i, l in enumerate(LEVELS)}
AFFIX_TEMPLATES = {"af", "affix", "prefix", "pre", "suffix", "suf", "confix", "con"}
COMPOUND_TEMPLATES = AFFIX_TEMPLATES | {"com", "compound", "univerbation", "univ"}
# The unified {{ety}} template (English Wiktionary's migration, under way by the
# 2026-10-30 dump) writes one etymology as segments, each opened by an operator
# argument: {{ety|uk|:af|банк<t:bank>|-івський}} or {{ety|uk|:bor|fr:x|:af<surf>|a|b}}.
# These operators carry the same claim as the old templates and are read as them;
# every other operator (:bor, :inh, :der, :calque ...) names no Ukrainian base.
ETY_OPERATORS = {":af": "af", ":univ": "univerbation"}
FUNCTION_POS = {"prep", "conj", "particle", "adv", "pron", "det", "intj", "num", "postp"}
ASPECT_KEYS = ("pf", "pf2", "pf3", "impf", "impf2", "impf3")
USED = ("derived", "affix", "aspect")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(ch for ch in s if ch != "́")
    return unicodedata.normalize("NFC", s).replace("’", "'").replace("ʼ", "'").strip().lower()


def clean_part(v):
    """One template part as a node candidate: drop the inline modifiers Wiktionary
    appends to a part (<t:gloss>, <g:m>, <alt:...>, <pos:...>, <ref:...>; a ref
    can nest brackets, and modifiers only ever trail the word) and a same-language
    'uk:' prefix. A part in another language ('fr:...') is not a Ukrainian base."""
    v = (v or "").split("<", 1)[0]
    if ":" in v:
        lang, _, rest = v.partition(":")
        if lang != "uk":
            return ""
        v = rest
    return norm(v)


def etym_groups(tpl):
    """(template name, [parts]) for each affix-like claim one etymology template
    makes. An old-style template is one claim (its args 2..n); an {{ety}} template
    is one claim per :af or :univ segment."""
    args = tpl.get("args") or {}
    name = tpl.get("name")
    if name in COMPOUND_TEMPLATES:
        return [(name, [args[k] for k in sorted((k for k in args if k.isdigit() and int(k) >= 2), key=int)])]
    if name != "ety":
        return []
    groups, cur = [], None
    for k in sorted((k for k in args if k.isdigit() and int(k) >= 2), key=int):
        v = args[k]
        if v.startswith(":"):
            op = ETY_OPERATORS.get(v.split("<", 1)[0])
            cur = (op, []) if op else None
            if cur:
                groups.append(cur)
        elif cur:
            cur[1].append(v)
    return groups


def node_ok(w):
    return bool(w) and len(w) >= 3 and bool(CYR.match(w))


def read_edges(path):
    """One pass over the dump. Returns edges by type (sets of (a, b)), each
    headword's Wiktionary POS set, and the compound nodes."""
    edges = {k: set() for k in ("derived", "related", "affix", "aspect")}
    headpos = {}
    compounds = set()
    for line in open(path, encoding="utf-8"):
        e = json.loads(line)
        if e.get("lang_code") != "uk":
            continue
        w = norm(e.get("word", ""))
        if not node_ok(w):
            continue
        headpos.setdefault(w, set()).add(e.get("pos"))
        for kind in ("derived", "related"):
            for d in e.get(kind) or []:
                t = norm(d.get("word", ""))
                if node_ok(t) and t != w:
                    edges[kind].add((w, t))
        for tpl in e.get("etymology_templates") or []:
            for name, raw in etym_groups(tpl):
                parts = [clean_part(v) for v in raw]
                bases = [p for p in parts if node_ok(p) and p != w]
                if len(bases) > 1:
                    compounds.add(w)
                elif len(bases) == 1 and name in AFFIX_TEMPLATES:
                    edges["affix"].add((w, bases[0]))
        for ht in e.get("head_templates") or []:
            args = ht.get("args") or {}
            for k in ASPECT_KEYS:
                t = norm(args.get(k, ""))
                if node_ok(t) and t != w:
                    edges["aspect"].add((w, t))
    # an affix base Wiktionary knows only as a function word chains everything
    edges["affix"] = {(w, b) for w, b in edges["affix"] if not (headpos.get(b) and headpos[b] <= FUNCTION_POS)}
    # undeclared compounds: listed as derived by two headwords of different
    # stems, and carrying both stems
    listed_by = collections.defaultdict(set)
    for a, t in edges["derived"]:
        listed_by[t].add(a)
    for t, heads in listed_by.items():
        stems = {h[:4] for h in heads if h[:4] in t}
        if len(stems) >= 2:
            compounds.add(t)
    for kind in USED:
        edges[kind] = {(a, b) for a, b in edges[kind] if a not in compounds and b not in compounds}
    return edges, headpos, compounds


def previous_snapshots(snapshot):
    """The graph's earlier snapshots, newest first: what each one counted, so a
    consumer built on an older graph (the gap-fill model is read only when it is
    retrained) can say which graph it read instead of being held to this one.
    The committed file's own summary joins the list when this run is a new
    snapshot; a re-run of the same snapshot carries the list over unchanged."""
    path = os.path.join(DATA, "wiktionary-families.json")
    if not os.path.exists(path):
        return []
    prev = json.load(open(path, encoding="utf-8"))
    carried = prev.get("previous") or []
    if prev.get("snapshot") == snapshot:
        return carried
    keep = ("listCovered", "listTotal", "listInMultiMemberFamilies", "familiesTouchingList", "largestFamily")
    summary = {
        "snapshot": prev.get("snapshot"),
        "dumpDate": prev.get("dumpDate"),
        "counts": {k: prev["counts"][k] for k in keep if k in prev.get("counts", {})} | {"affixEdges": prev.get("counts", {}).get("edges", {}).get("affix")},
        "labeledSpread": prev.get("labeledSpread"),
    }
    return [summary] + carried


def union_find(edge_sets):
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for es in edge_sets:
        for a, b in sorted(es):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    return {w: find(w) for w in sorted(parent)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="kaikki.org-dictionary-Ukrainian.jsonl (the full dump)")
    ap.add_argument("--dump-date", help="the dump's Last-Modified date, yyyy-mm-dd")
    ap.add_argument("--relabel", action="store_true",
                    help="no dump: re-read the committed graph and refresh only the validated levels beside list members "
                         "(and everything derived from them) from the current puls-cefr.json; edges.csv is left as committed")
    args = ap.parse_args()
    if not args.relabel and not (args.dump and args.dump_date):
        ap.error("--dump and --dump-date are required unless --relabel")

    seed = json.load(open(os.path.join(DATA, "ubertext-lemmas-top12k.json"), encoding="utf-8"))
    puls = json.load(open(os.path.join(DATA, "puls-cefr.json"), encoding="utf-8"))
    rows = [dict(r, rank=i + 1) for i, r in enumerate(seed["rows"])]
    by_lemma = {}
    for r in rows:
        by_lemma.setdefault(norm(r["lemma"]), []).append(r)
    level_by_rank = {r["rank"]: r["level"] for r in puls["rows"] if r["level"] in LEVEL_IDX}

    committed = None
    if args.relabel:
        # The graph is the committed one; only the levels beside its list
        # members move. Family membership never depends on a level, so the
        # ids, sizes and counts carry over unchanged.
        committed = json.load(open(os.path.join(DATA, "wiktionary-families.json"), encoding="utf-8"))
        edges = None
        touching = []
        for f in committed["families"]:
            lm = sorted(([r for r in by_lemma.get(norm(m["lemma"]), []) if r["rank"] == m["rank"]][0] for m in f["listMembers"]), key=lambda r: r["rank"])
            touching.append((lm[0]["rank"], f["id"], f["members"], lm))
    else:
        edges, headpos, compounds = read_edges(args.dump)
        fam_of = union_find([edges[k] for k in USED])
        members = collections.defaultdict(list)
        for w, f in fam_of.items():
            members[f].append(w)

        # families that touch the list, ordered by their lowest-ranked list member
        touching = []
        for f, ws in members.items():
            lm = sorted((r for w in ws for r in by_lemma.get(w, [])), key=lambda r: r["rank"])
            if lm:
                touching.append((lm[0]["rank"], f, sorted(ws), lm))
        touching.sort()

    families = []
    spread_rows = []
    size_hist = collections.Counter()
    covered = set()
    for n, (_, f, ws, lm) in enumerate(touching, start=1):
        fid = f"wf{n:05d}"
        list_members = [{"lemma": r["lemma"], "rank": r["rank"], "pos": r["pos"], "level": level_by_rank.get(r["rank"])} for r in lm]
        for r in lm:
            covered.add(r["rank"])
        levels = sorted({LEVEL_IDX[m["level"]] for m in list_members if m["level"]})
        size_hist[min(len(lm), 10)] += 1
        if len([m for m in list_members if m["level"]]) >= 2:
            spread_rows.append(levels[-1] - levels[0])
        families.append({"id": fid, "root": lm[0]["lemma"], "size": len(ws), "listMembers": list_members, "members": ws,
                         "levelSpread": (levels[-1] - levels[0]) if len(levels) else None})

    spread = collections.Counter(spread_rows)
    labeled_spread = {
        "families": len(spread_rows),
        "sameLevel": spread.get(0, 0),
        "oneApart": spread.get(1, 0),
        "twoOrMore": sum(c for s, c in spread.items() if s >= 2),
        "meanSpread": round(sum(spread_rows) / len(spread_rows), 3) if spread_rows else None,
    }
    counts = {
        "headwords": committed["counts"]["headwords"] if committed else len(headpos),
        "edges": committed["counts"]["edges"] if committed else {k: len(v) for k, v in edges.items()},
        "compoundNodesExcluded": committed["counts"]["compoundNodesExcluded"] if committed else len(compounds),
        "wordsInGraph": committed["counts"]["wordsInGraph"] if committed else len(fam_of),
        "familiesAll": committed["counts"]["familiesAll"] if committed else len(members),
        "familiesTouchingList": len(families),
        "listCovered": len(covered),
        "listTotal": len(rows),
        "listInMultiMemberFamilies": sum(len(f["listMembers"]) for f in families if len(f["listMembers"]) >= 2),
        "largestFamily": max(f["size"] for f in families) if families else 0,
        "largestListMembers": max(len(f["listMembers"]) for f in families) if families else 0,
    }
    meta_snapshot = committed["snapshot"] if committed else SNAPSHOT_DATE
    meta = {
        "snapshot": meta_snapshot,
        "dumpDate": committed["dumpDate"] if committed else args.dump_date,
        "relabeled": RELABEL_DATE if committed else None,
        "source": "English Wiktionary, Ukrainian entries, via kaikki.org (wiktextract) full dump; CC-BY-SA 3.0",
        "license": "CC-BY-NC-SA-4.0 as a whole: the validated levels beside list members are PULS's, CC BY-NC-SA 4.0 by permission; the edges and members are Wiktionary content, CC-BY-SA 3.0, attributed, and CC-BY-SA on their own without the level column",
        "usedEdges": list(USED),
        "rules": [
            "node: one Cyrillic token of three or more letters, stress stripped, apostrophe normalized; reconstructions, bare affixes, Latin and multiword entries are out",
            "derived: headword A lists B under Derived terms",
            "affix: B's etymology is one affix claim over exactly one full-word base A, written either as an affix template ({{af}}, {{prefix}}, {{suffix}}, {{confix}}) or as an :af segment of the unified {{ety}} template; inline modifiers on a part (<t:...>, <g:...>, <alt:...>) are dropped before the part is read, and a part in another language is not a base",
            "compound nodes are excluded from the used edges: a word whose etymology names two or more full-word bases, or one that two headwords of different stems both list as derived while it carries both stems",
            "affix bases Wiktionary knows only as function words are dropped, so prepositional compounds do not chain every prefix into one family",
            "aspect: B is A's listed perfective or imperfective partner in the headword template",
            "related: recorded in edges.csv, not used for families (merges unrelated roots through shared suffixes)",
            "family: connected component of the used edges; ids are assigned in order of the family's lowest-ranked list member",
        ],
        "counts": counts,
        "sizeHistogram": {str(k): v for k, v in sorted(size_hist.items())},
        "labeledSpread": labeled_spread,
        "downloads": {"families": "/downloads/ukrainian-frequency/wiktionary-families/families.csv",
                      "edges": "/downloads/ukrainian-frequency/wiktionary-families/edges.csv"},
        "previous": previous_snapshots(meta_snapshot),
    }
    full = dict(meta)
    full["families"] = families
    with open(os.path.join(DATA, "wiktionary-families.json"), "w", encoding="utf-8") as fh:
        json.dump(full, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    os.makedirs(DL, exist_ok=True)
    with open(os.path.join(DL, "families.csv"), "w", encoding="utf-8") as fh:
        fh.write("family_id,root,family_size,lemma,on_list,rank,pos,validated_level\n")
        for f in families:
            on = {m["lemma"]: m for m in f["listMembers"]}
            for w in f["members"]:
                ms = [m for m in f["listMembers"] if norm(m["lemma"]) == w] or ([on[w]] if w in on else [])
                if ms:
                    for m in ms:
                        fh.write(f"{f['id']},{f['root']},{f['size']},{m['lemma']},yes,{m['rank']},{m['pos']},{m['level'] or ''}\n")
                else:
                    fh.write(f"{f['id']},{f['root']},{f['size']},{w},no,,,\n")
    in_graph = {w for f in families for w in f["members"]}
    if edges is not None:
        with open(os.path.join(DL, "edges.csv"), "w", encoding="utf-8") as fh:
            fh.write("source,target,edge_type,used_for_families\n")
            for kind in ("derived", "affix", "aspect", "related"):
                for a, b in sorted(edges[kind]):
                    if a in in_graph or b in in_graph:
                        fh.write(f"{a},{b},{kind},{'yes' if kind in USED else 'no'}\n")

    # the browser tier: aggregates plus a handful of readable families
    def readable(f):
        return 3 <= len(f["listMembers"]) <= 6 and f["levelSpread"] is not None and all(m["level"] for m in f["listMembers"])
    sample = [{"id": f["id"], "root": f["root"], "size": f["size"], "levelSpread": f["levelSpread"],
               "listMembers": f["listMembers"]} for f in families if readable(f)][:8]
    slim = dict(meta)
    slim["sample"] = sample
    body = (
        "// GENERATED by scripts/ukrainian-frequency/extract-wiktionary-families.py - do not edit by hand.\n"
        "// Browser-safe tier of the WIKTIONARY DERIVED-TERM FAMILY GRAPH, the open fallback for the\n"
        "// PULS word families: aggregates, the labeled-family level spread, and a few readable\n"
        "// families. Full graph: src/data/ukrainian-frequency/wiktionary-families.json and the CSVs.\n"
        "export const WIKT_FAMILIES = " + json.dumps(slim, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(os.path.join(LIB, "wiktionary-families.data.mjs"), "w", encoding="utf-8") as fh:
        fh.write(body)

    print(json.dumps({"counts": counts, "labeledSpread": labeled_spread, "sizeHistogram": meta["sizeHistogram"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
