#!/usr/bin/env python3
"""Check every published release in this repository against its own checksums.

    python3 scripts/verify.py

For each versioned folder under downloads/ukrainian-frequency: every line of
SHA256SUMS must match its file byte for byte, every file a manifest.json lists
under "sha256" must match, and every latest.json must point at a folder that
exists. Prints one line per folder and exits non-zero on any mismatch. Needs
nothing but the Python standard library.

A released version is never edited here: a correction is a new version folder
and latest.json moves. So a mismatch means the copy you have is not the release.
"""

import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DL = os.path.join(ROOT, "downloads", "ukrainian-frequency")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_hashes(m):
    """The {file: sha256} map a release manifest carries under "sha256"."""
    table = m.get("sha256") if isinstance(m, dict) else None
    if not isinstance(table, dict):
        return {}
    return {name: h for name, h in table.items() if isinstance(h, str)}


def main():
    if not os.path.isdir(DL):
        print(f"no releases at {DL}")
        return 1
    problems, folders, checked = [], 0, 0
    for dirpath, _dirs, names in sorted(os.walk(DL)):
        rel = os.path.relpath(dirpath, DL)
        if "latest.json" in names:
            latest = json.load(open(os.path.join(dirpath, "latest.json"), encoding="utf-8"))
            target = os.path.join(dirpath, latest["latest"])
            if not os.path.isdir(target):
                problems.append(f"{rel}/latest.json points at {latest['latest']}, which is not here")
        if "SHA256SUMS" not in names:
            continue
        folders += 1
        n = 0
        with open(os.path.join(dirpath, "SHA256SUMS"), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                want, name = line.split(None, 1)
                name = name.lstrip("*")
                path = os.path.join(dirpath, name)
                n += 1
                if not os.path.exists(path):
                    problems.append(f"{rel}/{name}: listed in SHA256SUMS, missing")
                elif sha256(path) != want:
                    problems.append(f"{rel}/{name}: does not match SHA256SUMS")
        if "manifest.json" in names:
            m = json.load(open(os.path.join(dirpath, "manifest.json"), encoding="utf-8"))
            for name, want in manifest_hashes(m).items():
                path = os.path.join(dirpath, name)
                if os.path.exists(path):
                    n += 1
                    if sha256(path) != want:
                        problems.append(f"{rel}/{name}: does not match manifest.json")
        checked += n
        print(f"{rel}: {n} checks")
    for p in problems:
        print("FAIL " + p)
    print(f"{folders} release folders, {checked} checks, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
