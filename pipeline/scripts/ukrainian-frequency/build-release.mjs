// ---------------------------------------------------------------------------
// Ukrainian Frequency - freeze the open-data releases. No network.
//
// Runs each committed lemma snapshot (src/data/ukrainian-frequency/) through the
// pure builder and writes the public download bundles to
// public/downloads/ukrainian-frequency/<version>/ (the ranked lemma list as JSON
// and CSV, an Anki-importable TSV, the coverage curve, a manifest, and
// SHA256SUMS; v0.2.0 also ships the v0.1.0 -> v0.2.0 crosswalk and the cleanup
// ledger), points latest.json at the newest list, and regenerates the
// committed, browser-safe tier at src/lib/ukrainian-frequency/release.data.mjs.
//
// RELEASE in that tier is the SPINE (v0.2.0), the list every other table on
// the page joins on by rank. The frozen predecessor (v0.1.0, its Zenodo version
// DOI minted) rides along as RELEASE.predecessor with the migration counts, so
// the page can point a reader keyed on the old ranks at the crosswalk.
//
//   node scripts/ukrainian-frequency/build-release.mjs
//   node scripts/ukrainian-frequency/build-release.mjs --check   (verify, no writes)
// ---------------------------------------------------------------------------

import { createHash } from "node:crypto";
import { writeFileSync, mkdirSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildRelease,
  readSeed,
  filesFor,
  fileAboutFor,
  CHECKPOINTS,
  SPINE,
  LATEST,
  PREVIOUS,
} from "../../src/lib/ukrainian-frequency/release.mjs";
import { renderReleaseIndex } from "./lib/release-index.mjs";

const CHECK = process.argv.includes("--check");

const VERSIONS = [PREVIOUS, SPINE];
const LICENSE = "CC-BY-4.0";
const DATASET = "ukrainian-frequency-lemmas";
const citationFor = (version) =>
  `Lawrence, J. (2026). Ukrainian Frequency: a lemma-based, coverage-graded open frequency list (${version}). jakelawrence.xyz/research/ukrainian-frequency. Derived from UberText 2.0 (Chaplynskyi, 2023).`;

const PROVENANCE = {
  [PREVIOUS]:
    "Derived aggregate counts (facts) from the UberText 2.0 lemma frequency dictionary (lang-uk, Chaplynskyi 2023). The list re-publishes counts, not the source corpus text. Rows are filtered to Ukrainian-Cyrillic-alphabetic lemmas with a linguistic Universal Dependencies POS tag; coverage is recomputed here from raw counts. This is the top 12000 lemmas, a v1 curated slice.",
  [LATEST]:
    "Derived aggregate counts (facts) from the UberText 2.0 lemma frequency dictionary (lang-uk, Chaplynskyi 2023), the same 2023-04-03 source file as v0.1.0. The list re-publishes counts, not the source corpus text. Rows are filtered to Ukrainian-Cyrillic-alphabetic lemmas with a linguistic Universal Dependencies POS tag, then a reviewed cleanup ledger (cleanup.json) is applied over every source row: the lemmatizer's case forms and tag-split compounds are folded into their lemmas, mislabeled names rejoined, non-words and Russian words dropped, apostrophes written one way. Coverage is recomputed here from raw counts over the unchanged token universe. Top 12000 lemma+POS rows after the cleanup; crosswalk.json maps every v0.1.0 rank onto this list.",
};

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DL = path.join(ROOT, "public", "downloads", "ukrainian-frequency");
const LIB = path.join(ROOT, "src", "lib", "ukrainian-frequency");

const sha256 = (body) => createHash("sha256").update(body).digest("hex");
const round100 = (n) => Math.round(n * 100) / 100;

function freeze(version) {
  const seed = readSeed(version);
  const files = filesFor(version);
  const about = fileAboutFor(version);
  const { rows, coverage, stats, bodies, migration } = buildRelease(version);
  const citation = citationFor(version);

  // A small, browser-safe sample so the page can show real lemmas without
  // shipping the full 12000-row list into the client bundle. The full list is a
  // download.
  const sample = rows.slice(0, 24).map((r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, permille: r.permille }));
  const milestones = [1000, 2000, 5000, 10000]
    .filter((n) => n <= rows.length)
    .map((n) => ({ rank: n, lemma: rows[n - 1].lemma, pos: rows[n - 1].pos, coveragePct: round100(rows[n - 1].cumulativeCoverage * 100) }));

  const sha = {};
  for (const f of files) sha[f] = sha256(bodies[f]);

  const manifest = {
    version,
    dataset: DATASET,
    subject: "A lemma-based, coverage-graded open frequency list for modern Ukrainian",
    tier: "public",
    provenance: PROVENANCE[version],
    source: {
      name: "UberText 2.0 lemma frequency dictionary",
      publisher: "lang-uk",
      url: seed.source_url,
      citation: seed.source_citation,
      // v0.2.0 is cut from the same download as v0.1.0; only the v0.1.0 seed records the access date
      accessed: seed.accessed ?? readSeed(PREVIOUS).accessed,
    },
    canonical: "/research/ukrainian-frequency",
    ...(version === LATEST
      ? {
          supersedes: PREVIOUS,
          cleanup: "docs/ukrainian-frequency/list-v0.2.0.md",
          migration,
          note: "Every other table on the study page joins on this list's ranks. A table keyed on v0.1.0 ranks migrates through crosswalk.json. Cite the version you used.",
        }
      : {}),
    wordTokenUniverse: stats.wordTokenUniverse,
    lemmas: stats.lemmas,
    properNouns: stats.properNouns,
    posHistogram: stats.posHistogram,
    coverage,
    milestones,
    checkpoints: CHECKPOINTS,
    license: LICENSE,
    files: files.map((f) => ({ file: f, about: about[f] })),
    citation,
    sha256: sha,
  };

  return { version, seed, files, rows, coverage, stats, bodies, migration, sample, milestones, sha, manifest, citation };
}

function main() {
  const built = Object.fromEntries(VERSIONS.map((v) => [v, freeze(v)]));
  const spine = built[SPINE];
  const previous = built[PREVIOUS];

  const latestBody =
    JSON.stringify({ latest: LATEST, path: `/downloads/ukrainian-frequency/${LATEST}/` }, null, 2) + "\n";

  // The generated, browser-safe tier the page + test read. Numbers re-derive
  // from the same snapshots; the page re-verifies they reconcile, live.
  const releaseData =
    "// GENERATED by scripts/ukrainian-frequency/build-release.mjs - do not edit by hand.\n" +
    "// The browser-safe release tier: version, headline stats, the coverage curve,\n" +
    "// the file list, and hashes of the committed open-data bundle. Every number\n" +
    "// re-derives from src/data/ukrainian-frequency/ubertext-lemmas-top12k.json; the\n" +
    "// page re-verifies the totals reconcile and CI re-hashes the files. RELEASE is\n" +
    "// the spine the other tiers join on; RELEASE.predecessor is the frozen v0.1.0\n" +
    "// list with the counts of what the crosswalk did to it.\n" +
    "export const RELEASE = " +
    JSON.stringify(
      {
        version: spine.version,
        dataset: DATASET,
        license: LICENSE,
        citation: spine.citation,
        source: spine.manifest.source,
        wordTokenUniverse: spine.stats.wordTokenUniverse,
        lemmas: spine.stats.lemmas,
        properNouns: spine.stats.properNouns,
        posHistogram: spine.stats.posHistogram,
        coverage: spine.coverage,
        milestones: spine.milestones,
        sample: spine.sample,
        files: spine.files,
        sha256: spine.sha,
        downloadBase: `/downloads/ukrainian-frequency/${spine.version}`,
        migration: spine.migration,
        predecessor: {
          version: previous.version,
          downloadBase: `/downloads/ukrainian-frequency/${previous.version}`,
          citation: previous.citation,
          lemmas: previous.stats.lemmas,
          wordTokenUniverse: previous.stats.wordTokenUniverse,
          properNouns: previous.stats.properNouns,
          coverage: previous.coverage,
          files: previous.files,
          sha256: previous.sha,
        },
      },
      null,
      2,
    ) +
    ";\n";

  if (CHECK) {
    const committed = readFileSync(path.join(LIB, "release.data.mjs"), "utf8");
    if (committed !== releaseData) {
      console.error("DRIFT: src/lib/ukrainian-frequency/release.data.mjs does not match a fresh build. Run `npm run uk-freq:build-release`.");
      process.exit(1);
    }
    if (readFileSync(path.join(DL, "latest.json"), "utf8") !== latestBody) {
      console.error(`DRIFT: latest.json does not point at ${LATEST}. Run \`npm run uk-freq:build-release\`.`);
      process.exit(1);
    }
    for (const b of Object.values(built)) {
      const out = path.join(DL, b.version);
      const manifestBody = JSON.stringify(b.manifest, null, 2) + "\n";
      if (!existsSync(path.join(out, "manifest.json")) || readFileSync(path.join(out, "manifest.json"), "utf8") !== manifestBody) {
        console.error(`DRIFT: committed ${b.version}/manifest.json does not match a fresh build. Run \`npm run uk-freq:build-release\`.`);
        process.exit(1);
      }
      for (const f of b.files) {
        if (!existsSync(path.join(out, f)) || readFileSync(path.join(out, f), "utf8") !== b.bodies[f]) {
          console.error(`DRIFT: committed ${b.version}/${f} does not match a fresh build. Run \`npm run uk-freq:build-release\`.`);
          process.exit(1);
        }
      }
    }
    console.log("Ukrainian Frequency releases verified: committed tier re-derives byte-for-byte.");
    return;
  }

  for (const b of Object.values(built)) {
    const out = path.join(DL, b.version);
    const manifestBody = JSON.stringify(b.manifest, null, 2) + "\n";
    const sumsBody = b.files.map((f) => `${b.sha[f]}  ${f}`).join("\n") + "\n";
    const indexBody = renderReleaseIndex({
      kicker: "Open data / Ukrainian Frequency",
      title: "A lemma-based Ukrainian frequency list",
      subject: b.manifest.subject,
      version: b.version,
      license: LICENSE,
      canonical: "/research/ukrainian-frequency#release",
      citation: b.citation,
      files: b.files,
    });
    mkdirSync(out, { recursive: true });
    for (const f of b.files) writeFileSync(path.join(out, f), b.bodies[f]);
    writeFileSync(path.join(out, "manifest.json"), manifestBody);
    writeFileSync(path.join(out, "SHA256SUMS"), sumsBody);
    writeFileSync(path.join(out, "index.html"), indexBody);

    console.log("Ukrainian Frequency release frozen:", b.version);
    console.log(`  lemmas ${b.stats.lemmas} | word-token universe ${b.stats.wordTokenUniverse} | proper nouns ${b.stats.properNouns}`);
    const top1k = b.coverage.find((c) => c.lemmas === 1000);
    const top5k = b.coverage.find((c) => c.lemmas === 5000);
    if (top1k && top5k) console.log(`  coverage: top-1000 ${top1k.coveragePct}% | top-5000 ${top5k.coveragePct}%`);
    if (b.migration) console.log(`  from ${PREVIOUS}: kept ${b.migration.kept} | merged ${b.migration.merged} | dropped ${b.migration.dropped} | entered ${b.migration.entered}`);
    console.log(`  files ${b.files.length} | license ${LICENSE}`);
  }
  writeFileSync(path.join(DL, "latest.json"), latestBody);
  writeFileSync(path.join(LIB, "release.data.mjs"), releaseData);
  console.log(`latest.json -> ${LATEST}; RELEASE spine ${SPINE}, predecessor ${PREVIOUS}`);
}

main();
