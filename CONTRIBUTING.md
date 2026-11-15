# Contributing

Thank you for reading the data closely. Corrections are the most useful thing
anyone sends.

## Reporting a correction

Open an issue: https://github.com/jake0lawrence/UA-Vocab/issues

Say which file and row (the `rank` is enough for any table keyed on it), what
is wrong, and how you know: a dictionary, a recording, a corpus count, your own
ear as a speaker. A wrong stress, a wrong level, a lemma that is not a lemma,
a broken link, a README that says something the file does not: all welcome.

Corrections are decided in the open, recorded in the folder's README with the
reason, and released as a new version. The one that made stress v1.0.2 came in
exactly this way: a reader reported тризуб, the report was checked against an
open recording and a dictionary, and the row changed.

Several tables are built over other people's work (lang-uk's frequency
dictionary and stress library, the PULS profile, the Borodin minimums,
Wiktionary). When an error is theirs, the fix belongs upstream, and the issue
will say where it was sent.

## Why pull requests to the data are not merged directly

The files here are generated. Each release is built from cited sources by the
study's pipeline and frozen with checksums, and this repository is regenerated
from those releases. A released file is never edited in place: a correction is
a new version folder, `latest.json` moves, and the old version stays for anyone
who cited it. So a pull request that edits a CSV cannot be merged as it is, but
it is a perfectly good way to show a correction; it will be read like an issue.

## Forking

Fork freely within each file's license (see LICENSE.md). Every folder's README
names its license and what it owes: most files are CC BY 4.0 or CC BY-SA 4.0;
anything carrying a PULS CEFR level is CC BY-NC-SA 4.0, so a commercial fork
drops those columns. Run `python3 scripts/verify.py` after copying to confirm
you have the releases intact.

## Running the checks

```
python3 scripts/verify.py                          # every release against its checksums
python3 -m pip install "pyarrow==25.0.1" pytest
python3 scripts/build-package.py --check           # the package data is the releases
python3 -m pip install ./python/uavocab
python3 -m pytest -q python/uavocab/tests
```
