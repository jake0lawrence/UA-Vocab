"""Row counts and hashes: the package's tables are exactly the published files.

The published files are the study's releases, served at
https://uavocab.org/downloads/ukrainian-frequency/ and kept at that same path,
downloads/ukrainian-frequency, in the open repository
(github.com/jake0lawrence/UA-Vocab). From a checkout the tests read them from
disk. Anywhere else (an installed wheel) they are fetched from uavocab.org
when UAVOCAB_FETCH_SOURCES=1, and skipped with a reason otherwise; the
manifest test needs neither and always runs."""

import csv
import hashlib
import io
import os
import urllib.request

import pyarrow.parquet as pq
import pytest

import uavocab
from uavocab import _store

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ORIGIN = "https://uavocab.org"


def _published(rel: str) -> bytes:
    """The bytes of a published release file, from the repo or from uavocab.org."""
    # the study's source repository keeps releases under public/; the open
    # repository keeps them at the path the site serves them at
    for local in (os.path.join(REPO, rel), os.path.join(REPO, rel[len("public/"):])):
        if os.path.exists(local):
            return open(local, "rb").read()
    if os.environ.get("UAVOCAB_FETCH_SOURCES") == "1":
        assert rel.startswith("public/"), rel
        url = ORIGIN + rel[len("public"):]
        req = urllib.request.Request(url, headers={"User-Agent": "uavocab-tests (+https://github.com/jake0lawrence/UA-Vocab)"})
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.read()
    pytest.skip(f"{rel} is not in this checkout; set UAVOCAB_FETCH_SOURCES=1 to read it from {ORIGIN}")


def test_every_parquet_matches_its_manifest_row_count_and_hash():
    m = _store.manifest()
    for name, d in m["datasets"].items():
        path = os.path.join(_store.DATA_DIR, d["file"])
        body = open(path, "rb").read()
        assert hashlib.sha256(body).hexdigest() == d["sha256"], name
        t = pq.read_table(path)
        assert t.num_rows == d["rows"], name
        assert t.column_names == d["columns"], name


def test_row_counts_match_the_published_files_exactly():
    m = _store.manifest()
    for name, d in m["datasets"].items():
        body = _published(d["source"]["path"])
        assert hashlib.sha256(body).hexdigest() == d["source"]["sha256"], (
            f"{name}: the published file changed; rebuild with scripts/ukrainian-frequency/build-package.py")
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8"), newline="")))
        assert len(rows) == d["rows"] == d["source"]["rows"], name


def test_the_published_headline_counts():
    # the counts the site publishes; a change here is a release, not a drift
    m = _store.manifest()["datasets"]
    assert m["frequency"]["rows"] == 12000
    assert m["validated_cefr"]["rows"] == 6403
    assert m["borodin_a1"]["rows"] == 929
    assert m["borodin_a2"]["rows"] == 1000
    assert m["crosswalk"]["rows"] == 10366


def test_nothing_predicted_is_shipped_and_puls_is_the_only_noncommercial_source():
    files = set(os.listdir(_store.DATA_DIR))
    assert not any("predict" in f or "lexicon" in f or "unimorph" in f or "forms" in f or "examples" in f for f in files)
    for r in _store.rows("validated_cefr"):
        assert r["confidence"] == "validated"
    for d in uavocab.sources()["datasets"].values():
        assert d["license"] in ("CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-SA-4.0")
        if d["license"] == "CC-BY-NC-SA-4.0":
            assert "PULS" in d["attribution"], d["title"]
