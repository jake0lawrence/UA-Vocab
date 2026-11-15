# ukvocab is now uavocab

This package was renamed **[uavocab](https://pypi.org/project/uavocab/)** at
version 0.5.0, to match the site the data belongs to,
[uavocab.org](https://uavocab.org).

```
pip install uavocab
```

```python
import uavocab
uavocab.lookup("п'ять")["level"]   # 'A1'
```

Nothing else changed: same data, same four functions (`lookup`, `levels`,
`coverage`, `sources`), same licenses.

This last release under the old name carries no data of its own. It depends
on `uavocab` and re-exports it, so `pip install ukvocab` and `import ukvocab`
keep working, with a warning that names the new import. It will not be
released again; new data arrives under `uavocab`.

| | |
|---|---|
| The package | https://pypi.org/project/uavocab/ |
| The study the data comes from | https://uavocab.org/research |
| Every dataset, its license and how to cite it | https://uavocab.org/data |
| Source | https://github.com/jake0lawrence/UA-Vocab |
| Archived copies with DOIs (Zenodo) | frequency list [10.5281/zenodo.22823134](https://doi.org/10.5281/zenodo.22823134), word stress [10.5281/zenodo.23092388](https://doi.org/10.5281/zenodo.23092388) |

Versions 0.3.0 to 0.4.1 of `ukvocab` stay on PyPI as they were, for anyone
who pinned one.
