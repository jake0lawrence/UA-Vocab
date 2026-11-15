"""The API against a fixed sample of 50 lemmas with their published validated
levels (ten per level; the strict join, the cross-tag rows and the apostrophe
lemmas all represented). The fixture is a literal, sampled once from
public/downloads/ukrainian-frequency/validated-cefr/lemmas.csv with seed
20260913, so a regression in normalization or the join shows up as a level
that no longer matches. It is not regenerated at test time on purpose."""

import uavocab
from uavocab import coverage, levels, lookup, norm, sources

# (lemma, UD pos, validated level, rank)
KNOWN = [
    ('долар', 'NOUN', 'A1', 195),
    ('відпочивати', 'VERB', 'A1', 4556),
    ('огірок', 'NOUN', 'A1', 10996),
    ('культура', 'NOUN', 'A1', 540),
    ('річка', 'NOUN', 'A1', 705),
    ('цукерка', 'NOUN', 'A1', 11598),
    ('показувати', 'VERB', 'A1', 1449),
    ('один', 'ADJ', 'A1', 3827),
    ('шостий', 'ADJ', 'A1', 4002),
    ('п’ятий', 'ADJ', 'A1', 1853),
    ('процес', 'NOUN', 'A2', 300),
    ('цифра', 'NOUN', 'A2', 2267),
    ('дзеркало', 'NOUN', 'A2', 2539),
    ('голуб', 'NOUN', 'A2', 9525),
    ('відстань', 'NOUN', 'A2', 1176),
    ('одягнути', 'VERB', 'A2', 11570),
    ('вузький', 'ADJ', 'A2', 3974),
    ('усередині', 'ADP', 'A2', 10049),
    ('кілька', 'DET', 'A2', 178),
    ('м’ясний', 'ADJ', 'A2', 8959),
    ('зібрати', 'VERB', 'B1', 1542),
    ('повезти', 'VERB', 'B1', 9486),
    ('будівля', 'NOUN', 'B1', 584),
    ('пішохід', 'NOUN', 'B1', 5253),
    ('мріяти', 'VERB', 'B1', 5324),
    ('комунальний', 'ADJ', 'B1', 1327),
    ('самостійний', 'ADJ', 'B1', 4038),
    ('вище', 'ADP', 'B1', 6222),
    ('ведучий', 'ADJ', 'B1', 5292),
    ('пам’ять', 'NOUN', 'B1', 964),
    ('завести', 'VERB', 'B2', 5044),
    ('вступ', 'NOUN', 'B2', 2045),
    ('експериментальний', 'ADJ', 'B2', 6049),
    ('прибутковий', 'ADJ', 'B2', 7377),
    ('начебто', 'PART', 'B2', 4255),
    ('насолоджуватися', 'VERB', 'B2', 9778),
    ('вболівальник', 'NOUN', 'B2', 4211),
    ('цивільний', 'NOUN', 'B2', 9873),
    ('народжений', 'ADJ', 'B2', 9970),
    ('пом’якшення', 'NOUN', 'B2', 8608),
    ('потік', 'NOUN', 'C1', 1805),
    ('нісенітниця', 'NOUN', 'C1', 11836),
    ('стрімкий', 'ADJ', 'C1', 6642),
    ('завершуватися', 'VERB', 'C1', 7337),
    ('прикмета', 'NOUN', 'C1', 8560),
    ('послужити', 'VERB', 'C1', 8904),
    ('здобич', 'NOUN', 'C1', 9030),
    ('потерпілий', 'ADJ', 'C1', 6600),
    ('слідчий', 'ADJ', 'C1', 1216),
    ('з’єднаний', 'ADJ', 'C1', 11796)
]


def test_fixture_is_fifty_distinct_readings():
    assert len(KNOWN) == 50
    assert len({(l, p) for l, p, _, _ in KNOWN}) == 50
    assert {lvl for _, _, lvl, _ in KNOWN} == {"A1", "A2", "B1", "B2", "C1"}


def test_lookup_returns_the_published_level_for_every_known_lemma():
    for lemma, pos, level, rank in KNOWN:
        hit = lookup(lemma, pos=pos)
        assert hit is not None, lemma
        assert hit["level"] == level, (lemma, pos, hit["level"])
        assert hit["rank"] == rank, (lemma, pos, hit["rank"])
        assert hit["pos"] == pos
        assert hit["on_list"] is True
        assert hit["level_source"].startswith("PULS validated level, POS-aware")
        assert hit["sources"]["validated_cefr"]["license"] == "CC-BY-NC-SA-4.0"
        assert hit["sources"]["validated_cefr"]["snapshot"] == "2026-07-23"


def test_lookup_without_pos_returns_the_most_frequent_reading_and_lists_the_rest():
    hit = lookup("один")
    assert hit["rank"] == 43 and hit["pos"] == "DET"
    assert [r["rank"] for r in hit["readings"]] == sorted(r["rank"] for r in hit["readings"])
    assert any(r["pos"] == "ADJ" and r["rank"] == 3827 for r in hit["readings"])


def test_apostrophe_and_stress_variants_normalize_to_one_key():
    assert norm("п'ять") == norm("п’ять") == norm("пʼять") == norm("П'ЯТЬ")
    assert norm("абе́тка") == "абетка"
    a = lookup("п'ять")
    b = lookup("п’ять")
    assert a and b and a["rank"] == b["rank"] and a["level"] == "A1"


def test_cross_tag_rows_carry_their_rule():
    hit = lookup("який", pos="DET")
    assert hit["level"] == "A1"
    assert hit["join"] == "cross-tag:DET->займенник"
    strict = lookup("в", pos="ADP")
    assert strict["join"] == "pos-family"


def test_off_list_lemma_falls_back_to_the_crosswalk_and_says_so():
    # a Borodin headword the corpus never reached, but the profile levels
    hit = lookup("абетка")
    assert hit is not None
    assert hit["on_list"] is False and hit["rank"] is None
    assert hit["level"] in ("A1", "A2", "B1", "B2", "C1", None)
    if hit["level"]:
        assert "crosswalk" in hit["level_source"]
    assert hit["minimums"]["a2"] is True


def test_unknown_string_returns_none():
    assert lookup("qwertyuiop") is None
    assert lookup("") is None


def test_levels_batch_matches_lookup():
    got = levels([l for l, _, _, _ in KNOWN[:12]] + ["qwertyuiop"])
    assert got["qwertyuiop"]["level"] is None and got["qwertyuiop"]["source"] is None
    for lemma, _, level, _ in KNOWN[:12]:
        # the batch call takes the most frequent reading, so compare against pos-free lookup
        assert got[lemma]["level"] == lookup(lemma)["level"]
        assert got[lemma]["source"] is not None


def test_enrichment_is_attached_to_a_b1_verb():
    hit = lookup("повідомити", pos="VERB")
    assert hit["level"] == "B1"
    kinds = {r["kind"] for r in hit["enrichment"]["aspect"]}
    assert "partner" in kinds
    assert any(r["preposition"] == "про" and r["case"] == "Acc" for r in hit["enrichment"]["government"])
    assert hit["enrichment"]["collocations"], "collocations expected for a B1 verb in the corpus slice"
    assert "b1_aspect" in hit["sources"]


def test_coverage_computation():
    text = ["в", "і", "бути", "долар", "qwertyuiop", "долар", "п'ять"]
    c = coverage(text, "A1")
    assert c["tokens"] == 7 and c["types"] == 6
    assert c["known"] == 6 and c["unknown"] == 1
    assert abs(c["coverage"] - 6 / 7) < 1e-9
    assert c["top_unknown"] == [("qwertyuiop", 1)]
    assert c["by_validated_level"]["A1"] == 6
    assert 0 < c["known_set_size"] <= sources()["datasets"]["validated_cefr"]["rows"]
    by_set = coverage(text, {"в", "і"})
    assert by_set["known"] == 2
    top = coverage(text, 100)
    assert top["known"] >= 3
    b = coverage(text, "borodin-a1")
    assert b["known"] >= 4


def test_coverage_rejects_an_unknown_named_set():
    try:
        coverage(["в"], "borodin-c2")
    except ValueError as e:
        assert "known_set" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_sources_carry_license_version_and_snapshot_per_dataset():
    s = sources()
    assert s["package_version"] == uavocab.__version__
    assert s["combined_license"] == "CC-BY-NC-SA-4.0"
    for name, d in s["datasets"].items():
        for key in ("version", "snapshot", "license", "rows", "sha256", "attribution", "citation"):
            assert d.get(key), (name, key)
    assert "predicted" in " ".join(s["not_shipped"]).lower()


def test_lookup_carries_the_stress_column():
    hit = lookup("людина", "NOUN")
    assert hit["stress"]["stress"] == "люди\u0301на"
    assert hit["stress"]["status"] == "dictionary"
    assert hit["stress"]["variants"] == []
    assert hit["sources"]["stress"]["license"] == "CC-BY-SA-4.0"
    organ = lookup("орган", "NOUN")["stress"]
    assert organ["status"] == "homograph"
    assert organ["variants"][0] == organ["stress"]
    assert len(organ["variants"]) == 2
    assert "=" in organ["note"]
    mono = lookup("в", "ADP")["stress"]
    assert mono["status"] == "monosyllabic" and mono["stress"] == "в"
    # an off-list word has no stress, and says so with None rather than a key error
    assert lookup("апельсин")["stress"] is None


def test_the_stress_column_is_release_v1_0_2():
    # v1.0.2 (2026-10-09) changed one row on a reader's report: тризуб is a
    # free variant, три́зуб first. 0.4.x shipped v1.0.1, which had тризу́б only.
    s = sources()["datasets"]["stress"]
    assert s["version"] == "v1.0.2"
    t = lookup("тризуб", "NOUN")["stress"]
    assert t["stress"] == "три\u0301зуб"
    assert t["status"] == "free_variant"
    assert t["variants"] == ["три\u0301зуб", "тризу\u0301б"]


def test_every_link_points_at_the_study_on_uavocab_org():
    s = sources()
    assert s["package"] == "uavocab"
    assert s["site"] == "https://uavocab.org/research"
    for name, d in s["datasets"].items():
        assert d["url"].startswith("https://uavocab.org/research"), (name, d["url"])
        assert "jakelawrence.xyz" not in d["citation"], (name, d["citation"])

