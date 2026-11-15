// ---------------------------------------------------------------------------
// Ukrainian Frequency - a lemma-based open frequency list (pure builder).
//
// Field Data thread. It turns a cited, committed snapshot of the UberText 2.0
// lemma frequency dictionary (lang-uk) into a versioned, hashed open-data
// release: a ranked, coverage-graded lemma list as CSV and JSON, an
// Anki-importable frequency deck seed, and the empirical text-coverage curve.
//
// Why lemma-based: Ukrainian is heavily inflected, so a single lemma scatters
// its frequency mass across a dozen or more wordforms. A raw wordform list
// therefore understates what a given amount of vocabulary buys a reader. The
// source dictionary is already lemmatized (Universal Dependencies POS), so the
// list counts lemmas, the unit a learner actually studies.
//
// Honesty discipline (inherited from the research program):
//  - No em-dashes anywhere, in copy or code. A test enforces it.
//  - The list is DERIVED aggregate counts (facts), re-released under CC-BY with
//    the source attributed. It is not the source corpus text.
//  - Coverage is computed here from raw counts, not read from the source file's
//    own freq columns (whose normalization is undocumented).
//  - Frequency bands are transparent thousand-rank bins. They are NOT CEFR
//    levels; validated CEFR alignment lives in thread 2 (cefr.mjs,
//    puls-cefr.data.mjs).
//
// This module is pure data-processing (Node fs for the committed seed). It is
// imported by the generator (scripts/ukrainian-frequency/build-release.mjs) and
// by the drift-guard test, never by the client page. The page reads the
// generated, browser-safe release.data.mjs instead.
// ---------------------------------------------------------------------------

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const DATA = path.join(ROOT, "src", "data", "ukrainian-frequency");

// Two frozen lists. v0.2.0 is the SPINE: the default seed
// (ubertext-lemmas-top12k.json) every other tier joins on by rank. It is the
// same source as v0.1.0 with the reviewed cleanup ledger applied
// (docs/ukrainian-frequency/list-v0.2.0.md) and ships with the crosswalk that
// maps every v0.1.0 rank onto it. v0.1.0 stays frozen from its own seed file,
// byte-identical (its Zenodo version DOI is minted), as the predecessor.
export const SPINE = "v0.2.0";
export const LATEST = "v0.2.0";
export const PREVIOUS = "v0.1.0";
export const SEEDS = {
  "v0.1.0": "ubertext-lemmas-top12k.v0.1.0.json",
  "v0.2.0": "ubertext-lemmas-top12k.json",
};
const CROSSWALK = path.join(DATA, "list-v0.2.0-crosswalk.json");
const CLEANUP = path.join(DATA, "list-cleanup.json");

// The ordered release files common to both lists (the constant older callers
// import); v0.2.0 drops the undefined `docs` column and adds the migration files.
export const FILES = ["lemmas.json", "lemmas.csv", "lemmas.anki.tsv", "coverage.json", "coverage.csv"];
const FILES_V2 = [...FILES, "crosswalk.json", "crosswalk.csv", "cleanup.json"];

export function filesFor(version) {
  return version === LATEST ? FILES_V2 : FILES;
}

// A one-line description per file for the manifest and the page.
export const FILE_ABOUT = {
  "lemmas.json": "The ranked lemma list: rank, lemma, UD part of speech, corpus count, document count, per-mille frequency, cumulative coverage, and the thousand-rank frequency band.",
  "lemmas.csv": "The same ranked lemma list as CSV, for spreadsheets and scripts.",
  "lemmas.anki.tsv": "An Anki-importable frequency deck seed: lemma, part of speech, rank, per-mille. One note per lemma, ordered most frequent first.",
  "coverage.json": "The empirical running-text coverage curve: what share of word tokens the top N lemmas account for, at each checkpoint.",
  "coverage.csv": "The coverage curve as CSV.",
};
const FILE_ABOUT_V2 = {
  ...FILE_ABOUT,
  "lemmas.json": "The ranked lemma list: rank, lemma, UD part of speech, corpus count, per-mille frequency, cumulative coverage, and the thousand-rank frequency band. The source's doc_count column is not carried: it exceeds the row's own count in a fifth of the rows and is defined nowhere upstream.",
  "crosswalk.json": "Every v0.1.0 row once, in v0.1.0 order, with its fate in v0.2.0 (kept, merged, dropped) and the v0.2.0 rank it now counts toward, then the rows that entered from below the v0.1.0 cut. A table keyed on v0.1.0 ranks migrates through this file.",
  "crosswalk.csv": "The crosswalk as one CSV: the v0.1.0 rows with their fate, then the entered rows (fate `entered`, no v1Rank).",
  "cleanup.json": "The reviewed cleanup ledger the list was built with: every explicit merge and drop with its reason, the two general rules (apostrophe glyph, mislabeled names), and the six recorded decisions.",
};

export function fileAboutFor(version) {
  return version === LATEST ? FILE_ABOUT_V2 : FILE_ABOUT;
}

// Coverage checkpoints (N lemmas). The curve is the headline empirical finding.
export const CHECKPOINTS = [100, 250, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000];

export function readSeed(version = SPINE) {
  if (!SEEDS[version]) throw new Error(`no seed for ${version}`);
  return JSON.parse(readFileSync(path.join(DATA, SEEDS[version]), "utf8"));
}

export function readCrosswalk() {
  return JSON.parse(readFileSync(CROSSWALK, "utf8"));
}

// What v0.2.0 did to the spine, in five numbers: read off the crosswalk, so the
// manifest, the page and the test cannot quote a figure the file does not hold.
export function migrationStats(cross = readCrosswalk()) {
  const fates = { kept: 0, merged: 0, dropped: 0 };
  const moves = [];
  for (const r of cross.rows) {
    fates[r.fate] = (fates[r.fate] || 0) + 1;
    if (r.fate === "kept" && r.v2Rank !== r.v1Rank) moves.push(Math.abs(r.v2Rank - r.v1Rank));
  }
  moves.sort((a, b) => a - b);
  return {
    from: cross.from,
    to: cross.to,
    kept: fates.kept,
    merged: fates.merged,
    dropped: fates.dropped,
    entered: cross.entered.length,
    moved: moves.length,
    medianMove: moves.length ? moves[moves.length >> 1] : 0,
  };
}

// RFC-4180 cell.
function csvCell(v) {
  let s;
  if (v === null || v === undefined) s = "";
  else s = String(v);
  if (/[",\n]/.test(s)) s = `"${s.replace(/"/g, '""')}"`;
  return s;
}

// Deterministic CSV: header is the given ordered column list.
function toCsv(cols, rows) {
  const lines = [cols.join(",")];
  for (const row of rows) lines.push(cols.map((c) => csvCell(row[c])).join(","));
  return lines.join("\n") + "\n";
}

// Round to a fixed number of places without trailing float noise.
function round(n, places) {
  const f = 10 ** places;
  return Math.round(n * f) / f;
}

// Build a release from its committed seed. Network-free and deterministic.
// The spine is the default.
export function buildRelease(version = SPINE) {
  const seed = readSeed(version);
  const total = seed.word_token_universe_total;
  const src = seed.rows;
  // the source's doc_count is carried only where the seed still has it (v0.1.0)
  const hasDocs = src.length > 0 && "docs" in src[0];

  // Ranked rows with derived per-mille + cumulative coverage + thousand-rank band.
  const rows = [];
  let cum = 0;
  for (let i = 0; i < src.length; i++) {
    const r = src[i];
    const rank = i + 1;
    cum += r.count;
    rows.push({
      rank,
      lemma: r.lemma,
      pos: r.pos,
      count: r.count,
      ...(hasDocs ? { docs: r.docs } : {}),
      permille: round((r.count / total) * 1000, 4),
      cumulativeCoverage: round(cum / total, 6),
      freqBand: Math.ceil(rank / 1000),
    });
  }

  // Coverage curve at the checkpoints.
  const coverage = CHECKPOINTS.filter((n) => n <= rows.length).map((n) => ({
    lemmas: n,
    coverage: round(rows[n - 1].cumulativeCoverage, 4),
    coveragePct: round(rows[n - 1].cumulativeCoverage * 100, 2),
  }));

  // POS histogram over the released list (a transparency figure).
  const posHistogram = {};
  for (const r of rows) posHistogram[r.pos] = (posHistogram[r.pos] || 0) + 1;

  const bodies = {
    "lemmas.json": JSON.stringify(rows) + "\n",
    "lemmas.csv": toCsv(
      ["rank", "lemma", "pos", "count", ...(hasDocs ? ["docs"] : []), "permille", "cumulativeCoverage", "freqBand"],
      rows,
    ),
    "lemmas.anki.tsv":
      rows.map((r) => `${r.lemma}\t${r.pos}\t${r.rank}\t${r.permille}`).join("\n") + "\n",
    "coverage.json": JSON.stringify(coverage) + "\n",
    "coverage.csv": toCsv(["lemmas", "coverage", "coveragePct"], coverage),
  };

  let migration = null;
  if (version === LATEST) {
    // The migration files ship the committed artifacts verbatim (the test suite
    // already holds them to the seed), plus a flat CSV reading of the crosswalk.
    const crossText = readFileSync(CROSSWALK, "utf8");
    const cross = JSON.parse(crossText);
    const flat = [
      ...cross.rows.map((r) => ({
        v1Rank: r.v1Rank,
        lemma: r.lemma,
        pos: r.pos,
        count: r.count,
        fate: r.fate,
        step: r.step || "",
        intoLemma: r.into ? r.into.lemma : "",
        intoPos: r.into ? r.into.pos : "",
        v2Rank: r.v2Rank ?? "",
      })),
      ...cross.entered.map((r) => ({
        v1Rank: "",
        lemma: r.lemma,
        pos: r.pos,
        count: r.count,
        fate: "entered",
        step: "",
        intoLemma: "",
        intoPos: "",
        v2Rank: r.v2Rank,
      })),
    ];
    bodies["crosswalk.json"] = crossText;
    bodies["crosswalk.csv"] = toCsv(["v1Rank", "lemma", "pos", "count", "fate", "step", "intoLemma", "intoPos", "v2Rank"], flat);
    bodies["cleanup.json"] = readFileSync(CLEANUP, "utf8");
    migration = migrationStats(cross);
  }

  const stats = {
    lemmas: rows.length,
    wordTokenUniverse: total,
    properNouns: posHistogram.PROPN || 0,
    posHistogram,
  };

  return { version, rows, coverage, stats, bodies, migration };
}
