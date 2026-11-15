# Changelog

The package was published as `ukvocab` through 0.4.1 and as `uavocab` from
0.5.0. Versions below 0.5.0 are on PyPI under the old name.

## 0.5.0 (2026-11-15)

- Renamed from `ukvocab` to `uavocab`, the name of the site the data belongs
  to (uavocab.org) and of the public source repository
  (github.com/jake0lawrence/UA-Vocab). `import uavocab` replaces
  `import ukvocab`; the API is unchanged. `ukvocab` 0.5.0 is a final release
  under the old name that depends on this package and re-exports it with a
  warning that names the new import, so existing installs and imports keep
  working.
- Every link now points at where things live: the study moved to
  uavocab.org/research on 2026-11-14. Project links on PyPI, `sources()["site"]`,
  each dataset's `url` (a section that exists on the page) and each citation
  name uavocab.org. 0.4.x linked jakelawrence.xyz, its Source link pointed into
  a private repository and its Data link answered 404.
- Stress column v1.0.1 to v1.0.2: one row changes. тризуб (rank 11,982) is a
  free variant, три́зуб first and тризу́б accepted, on a reader's report checked
  against a recording and a dictionary (the site published v1.0.2 on
  2026-10-09; 0.4.x still carried v1.0.1). The other eight tables are
  byte-identical to 0.4.1.
- The source tests can run outside the study's repository: with
  UAVOCAB_FETCH_SOURCES=1 they read the published release files from
  uavocab.org and check the package against them.

## 0.4.1 (2026-11-15)

- Corrected the credit for ukrainian-word-stress in the README PyPI renders: it
  is a lang-uk project, started by Oleksiy Syvokon and maintained by Dmytro
  Chaplynskyi. Release 0.4.0 credited it to someone who is not its author or
  maintainer. No data changed; the Parquet tier is byte-identical to 0.4.0.

## 0.4.0

- Added the `stress` dataset, a per-lemma word-stress column joined on rank.

## 0.3.0

- First release on PyPI. Combined license CC-BY-NC-SA 4.0.
