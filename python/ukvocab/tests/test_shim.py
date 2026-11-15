"""The old name is an alias of the new one, and says so."""

import importlib
import sys
import warnings


def _fresh_import():
    sys.modules.pop("ukvocab", None)
    sys.modules.pop("ukvocab._store", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        mod = importlib.import_module("ukvocab")
    return mod, caught


def test_import_warns_and_names_the_new_package():
    _, caught = _fresh_import()
    msgs = [str(w.message) for w in caught if issubclass(w.category, FutureWarning)]
    assert any("uavocab" in m for m in msgs), msgs


def test_the_alias_is_the_new_package():
    ukvocab, _ = _fresh_import()
    import uavocab

    assert ukvocab.lookup is uavocab.lookup
    assert ukvocab.coverage is uavocab.coverage
    assert ukvocab.__version__ == uavocab.__version__
    assert set(ukvocab.__all__) == set(uavocab.__all__)
    assert ukvocab.lookup("п’ять")["level"] == "A1"
    assert ukvocab.sources()["package"] == "uavocab"


def test_old_submodule_imports_still_resolve():
    _fresh_import()
    from ukvocab._store import manifest
    from uavocab import _store

    assert manifest is _store.manifest
