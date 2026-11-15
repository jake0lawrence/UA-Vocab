"""uavocab: the open Ukrainian vocabulary data behind uavocab.org, offline.

The data is the Ukrainian Frequency study at https://uavocab.org/research.
This package was published as `ukvocab` up to 0.4.1; that name now installs
this one.

Four functions, kept small on purpose:

    lookup(lemma, pos=None)      one lemma: level, its source, rank, enrichment
    levels(lemmas)               batch: lemma -> level, with the source
    coverage(lemmas, known_set)  the running-text coverage computation
    sources()                    version, snapshot and license per dataset

Every return value carries the dataset, version and snapshot it came from.
The package does not lemmatize: pass lemmas in the VESUM / UberText
convention (the infinitive for verbs, the nominative singular for nouns).
Predicted CEFR levels are deliberately not in this package.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional, Union

from . import _store
from ._store import LEVELS, norm

__all__ = ["lookup", "levels", "coverage", "sources", "LEVELS", "norm", "__version__"]


def __getattr__(name):
    if name == "__version__":
        return _store.manifest()["packageVersion"]
    raise AttributeError(name)


LEVEL_SOURCE_VALIDATED = "PULS validated level, POS-aware join onto the frequency list (validated_cefr)"
LEVEL_SOURCE_CROSSWALK = "PULS validated level via the crosswalk: lemma-string join, no part of speech (crosswalk)"


def _reading(row: dict) -> dict:
    lv = _store.level_by_rank().get(row["rank"])
    return {
        "rank": row["rank"],
        "pos": row["pos"],
        "count": row["count"],
        "permille": row["permille"],
        "cumulative_coverage": row["cumulativeCoverage"],
        "freq_band": row["freqBand"],
        "level": lv["level"] if lv else None,
        "join": lv["join"] if lv else None,
        "stress": _store.stress_by_rank().get(row["rank"]),
    }


def _enrichment(key: str) -> dict:
    return {
        "aspect": [dict(r) for r in _store.aspect_by_verb().get(key, [])],
        "government": [dict(r) for r in _store.government_by_verb().get(key, [])],
        "collocations": [dict(r) for r in _store.collocations_by_lemma().get(key, [])],
    }


def lookup(lemma: str, pos: Optional[str] = None) -> Optional[dict]:
    """One lemma. Returns None when no table knows the string at all.

    With `pos` (a UD tag such as NOUN, VERB, ADJ, DET) the reading with that
    part of speech is returned; without it, the most frequent reading, and
    every other reading is listed under `readings` so a homograph is never
    silently collapsed. The level comes from the validated overlay when the
    lemma is on the frequency list (POS-aware); otherwise from the crosswalk,
    which joins by lemma string only, and `level_source` says which.
    """
    key = norm(lemma)
    readings = _store.frequency_by_key().get(key, [])
    if pos is not None:
        readings = [r for r in readings if r["pos"] == pos]
    primary = _reading(readings[0]) if readings else None
    xw = _store.crosswalk_by_key().get(key)
    if primary is None and xw is None:
        return None

    level = primary["level"] if primary else None
    level_source = LEVEL_SOURCE_VALIDATED if level else None
    if level is None and xw and xw.get("validatedLevel"):
        level = xw["validatedLevel"]
        level_source = LEVEL_SOURCE_CROSSWALK

    used = ["frequency", "validated_cefr", "crosswalk", "borodin_a1", "borodin_a2"]
    if primary is not None:
        used.append("stress")
    enrichment = _enrichment(key)
    if any(enrichment.values()):
        used += ["b1_aspect", "b1_government", "b1_collocations"]

    return {
        "query": lemma,
        "lemma": readings[0]["lemma"] if readings else (xw["lemma"] if xw else key),
        "on_list": primary is not None,
        "rank": primary["rank"] if primary else None,
        "pos": primary["pos"] if primary else (xw.get("pos") if xw else None),
        "count": primary["count"] if primary else None,
        "permille": primary["permille"] if primary else None,
        "freq_band": primary["freq_band"] if primary else None,
        "level": level,
        "level_source": level_source,
        "join": primary["join"] if primary else None,
        "stress": primary["stress"] if primary else None,
        "readings": [_reading(r) for r in _store.frequency_by_key().get(key, [])],
        "minimums": {
            "a1": key in _store.crosswalk_volume_keys("A1"),
            "a2": key in _store.crosswalk_volume_keys("A2"),
            "a1_entries": [r["entry"] for r in _store.borodin_keys("a1").get(key, [])],
            "a2_entries": [r["entry"] for r in _store.borodin_keys("a2").get(key, [])],
        },
        "crosswalk": {
            "class": xw["class"],
            "volume": xw.get("volume"),
            "validated_level": xw.get("validatedLevel"),
            "relative": xw.get("relative"),
            "relative_via": xw.get("relativeVia"),
        } if xw else None,
        "enrichment": enrichment,
        "sources": {name: _store.source_of(name) for name in used},
    }


def levels(lemmas: Iterable[str]) -> Dict[str, dict]:
    """Batch lookup: input string -> {level, level_source, rank, pos, source}.
    A lemma no table knows gets level None and an empty source."""
    out: Dict[str, dict] = {}
    for lemma in lemmas:
        hit = lookup(lemma)
        if hit is None:
            out[lemma] = {"level": None, "level_source": None, "rank": None, "pos": None, "source": None}
            continue
        src_name = "validated_cefr" if hit["level_source"] == LEVEL_SOURCE_VALIDATED else ("crosswalk" if hit["level"] else None)
        out[lemma] = {
            "level": hit["level"],
            "level_source": hit["level_source"],
            "rank": hit["rank"],
            "pos": hit["pos"],
            "source": _store.source_of(src_name) if src_name else None,
        }
    return out


KnownSet = Union[str, int, Iterable[str]]


def _resolve_known(known_set: KnownSet):
    """A known set is an iterable of lemma strings, a level name (every
    validated lemma at or below it), 'borodin-a1' / 'borodin-a2' (the
    minimum, on and off the list, A2 including A1), or an int N (the top N of
    the frequency list)."""
    if isinstance(known_set, int) and not isinstance(known_set, bool):
        return _store.top_n_set(known_set), f"top {known_set} of the frequency list", ["frequency"]
    if isinstance(known_set, str):
        tag = known_set.strip()
        if tag.upper() in LEVELS:
            return _store.level_set(tag.upper()), f"every validated lemma at or below {tag.upper()}", ["validated_cefr", "frequency"]
        if tag.lower() in ("borodin-a1", "a1-minimum"):
            return _store.crosswalk_volume_keys("A1"), "the Borodin A1 minimum (every headword, on or off the list)", ["crosswalk", "borodin_a1"]
        if tag.lower() in ("borodin-a2", "a2-minimum"):
            return _store.crosswalk_volume_keys("A2"), "the Borodin A1 and A2 minimums (every headword, on or off the list)", ["crosswalk", "borodin_a1", "borodin_a2"]
        raise ValueError(f"unknown known_set name {known_set!r}: a level (A1..C1), 'borodin-a1', 'borodin-a2', an int, or an iterable of lemmas")
    return frozenset(norm(s) for s in known_set), "a caller-supplied set of lemmas", ["frequency"]


def coverage(lemmas: Iterable[str], known_set: KnownSet, top_unknown: int = 20) -> dict:
    """Running-text coverage of a lemmatized text against a known set.

    `lemmas` is the text as a sequence of lemmas, one per token, repeats
    included (coverage is token coverage, not type coverage). Tokens are
    counted as known when their normalized lemma is in the known set; the
    package does not decide what a word is, so pass only the tokens you want
    counted (a caller usually drops punctuation, numbers and proper names).
    Also reports how many tokens are on the frequency list at all, and the
    most frequent unknown lemmas, so a gap is a list rather than a number.
    """
    known, description, used = _resolve_known(known_set)
    counts = Counter(norm(t) for t in lemmas)
    total = sum(counts.values())
    known_tokens = sum(n for k, n in counts.items() if k in known)
    on_list = sum(n for k, n in counts.items() if k in _store.frequency_by_key())
    unknown = Counter({k: n for k, n in counts.items() if k not in known})
    by_level: Dict[str, int] = {lvl: 0 for lvl in LEVELS}
    unleveled = 0
    for k, n in counts.items():
        readings = _store.frequency_by_key().get(k)
        lv = _store.level_by_rank().get(readings[0]["rank"]) if readings else None
        if lv:
            by_level[lv["level"]] += n
        else:
            unleveled += n
    return {
        "tokens": total,
        "types": len(counts),
        "known": known_tokens,
        "unknown": total - known_tokens,
        "coverage": (known_tokens / total) if total else 0.0,
        "on_list": on_list,
        "on_list_share": (on_list / total) if total else 0.0,
        "by_validated_level": by_level,
        "unleveled": unleveled,
        "known_set": description,
        "known_set_size": len(known),
        "top_unknown": unknown.most_common(top_unknown),
        "sources": {name: _store.source_of(name) for name in used},
    }


def sources() -> dict:
    """Version, snapshot, license, attribution, citation and checksum per
    dataset, plus the combined license and why, straight from the manifest."""
    m = _store.manifest()
    return {
        "package": m["package"],
        "package_version": m["packageVersion"],
        "site": m["site"],
        "combined_license": m["combinedLicense"],
        "combined_license_why": m["combinedLicenseWhy"],
        "not_shipped": list(m["notShipped"]),
        "datasets": {name: dict(d) for name, d in m["datasets"].items()},
    }
