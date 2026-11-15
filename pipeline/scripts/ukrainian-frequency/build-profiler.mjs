// ---------------------------------------------------------------------------
// Ukrainian Frequency - freeze the text profiler's lexicon bundle (thread 06)
// and run the validation set. No network.
//
// Assembles, from the committed source tiers, the two artifacts the in-browser
// profiler downloads on the first analyze gesture:
//   lexicon.json  the top-12000 lemmas with POS, validated PULS level (or null),
//                 Wiktionary family id, the aspect-partner pairs, and the two
//                 Borodin minimums as index sets
//   forms.json    surface form -> lemma index, from the Wiktionary paradigm
//                 tables (thread 04), only where the form differs from the lemma
// under public/downloads/ukrainian-frequency/profiler/<version>/ (with a
// manifest, SHA256SUMS and an index page), then runs the profiler over the
// committed validation texts (profiler-validation.json) and regenerates the
// browser-safe tier src/lib/ukrainian-frequency/profiler.data.mjs (counts,
// hashes, the validation result). --check verifies byte-for-byte.
//
//   node scripts/ukrainian-frequency/build-profiler.mjs
//   node scripts/ukrainian-frequency/build-profiler.mjs --check
// ---------------------------------------------------------------------------

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildLexicon, loadLexicon } from "../../src/lib/ukrainian-frequency/profiler/lexicon.mjs";
import { runValidation } from "../../src/lib/ukrainian-frequency/profiler/validation.mjs";
import { renderReleaseIndex } from "./lib/release-index.mjs";
import { SPINE } from "../../src/lib/ukrainian-frequency/release.mjs";

const CHECK = process.argv.includes("--check");

export const VERSION = "v1.2.0";
const LICENSE = "CC-BY-NC-SA-4.0";
const DATASET = "ukrainian-frequency-profiler";
const CITATION =
  `Lawrence, J. (2026). Ukrainian Frequency: a text profiler for Ukrainian, lexicon bundle (${VERSION}). jakelawrence.xyz/research/ukrainian-frequency/profiler. Lemmas from UberText 2.0 (Chaplynskyi, 2023); paradigm forms and word families from Wiktionary via kaikki.org (CC BY-SA); validated levels from the Ukrainian Vocabulary Profile (Synchak et al., 2025; PULS, by permission, CC BY-NC-SA 4.0); lexical minimums from Borodin et al. (CC BY).`;

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DATA = path.join(ROOT, "src", "data", "ukrainian-frequency");
const OUT = path.join(ROOT, "public", "downloads", "ukrainian-frequency", "profiler", VERSION);
const LATEST_DIR = path.join(ROOT, "public", "downloads", "ukrainian-frequency", "profiler");
const LIB = path.join(ROOT, "src", "lib", "ukrainian-frequency");

const sha256 = (body) => createHash("sha256").update(body).digest("hex");
const readJson = (f) => JSON.parse(readFileSync(path.join(DATA, f), "utf8"));

export function readFormRows() {
  const raw = gunzipSync(readFileSync(path.join(ROOT, "public", "downloads", "ukrainian-frequency", "paradigms", "forms.csv.gz"))).toString("utf8");
  const rows = [];
  for (const line of raw.split("\n").slice(1)) {
    if (!line) continue;
    const [rank, lemma, pos, form] = line.split(",");
    rows.push({ rank: Number(rank), lemma, pos, form });
  }
  return rows;
}

export function buildAll() {
  const seed = readJson("ubertext-lemmas-top12k.json");
  const built = buildLexicon({
    seed,
    formRows: readFormRows(),
    puls: readJson("puls-cefr.json"),
    families: readJson("wiktionary-families.json"),
    aspect: readJson("b1-aspect.json"),
    borodinA1: readJson("borodin-a1.json"),
    borodinA2: readJson("borodin-a2.json"),
    // the list the indices are ranks on, and the map from the previous list's
    // ranks, so a known set saved under v0.1.0 migrates when the bundle loads
    crosswalk: readJson("list-v0.2.0-crosswalk.json"),
    listVersion: SPINE,
  });
  const validationSet = readJson("profiler-validation.json");
  const lex = loadLexicon(built.lexicon, built.forms);
  const validation = runValidation(validationSet.texts, lex);
  return { built, lex, validationSet, validation };
}

function main() {
  const { built, lex, validationSet, validation } = buildAll();
  const lexiconBody = JSON.stringify(built.lexicon) + "\n";
  const formsBody = JSON.stringify(built.forms) + "\n";
  // the validation set travels with the bundle (CC BY-SA, attributed), so the
  // page's re-run button and any reader can fetch the same texts the frozen
  // result was computed on
  const validationBody =
    JSON.stringify({
      snapshot: validationSet.snapshot,
      source: validationSet.source,
      sourceUrl: validationSet.sourceUrl,
      license: validationSet.license,
      levelAssertedBy: validationSet.levelAssertedBy,
      caveat: validationSet.caveat,
      method: validationSet.method,
      count: validationSet.count,
      texts: validationSet.texts.map((t) => ({ id: t.id, level: t.level, title: t.title, url: t.url, words: t.words, text: t.text })),
    }) + "\n";
  const sha = { "lexicon.json": sha256(lexiconBody), "forms.json": sha256(formsBody), "validation.json": sha256(validationBody) };

  const leveled = lex.lemmas.filter((L) => L.level).length;
  const inFamilies = lex.lemmas.filter((L) => L.family).length;
  const counts = {
    lemmas: lex.size,
    leveled,
    unlabeled: lex.size - leveled,
    forms: lex.forms.size,
    lemmasWithForms: new Set([...lex.forms.values()].flat()).size,
    families: lex.familyOf.size,
    lemmasInFamilies: inFamilies,
    aspectPairs: built.lexicon.aspectPairs.length,
    sets: Object.fromEntries(Object.entries(built.lexicon.sets).map(([k, v]) => [k, { onList: v.idx.length, offList: v.offList.length }])),
  };

  const manifest = {
    version: VERSION,
    dataset: DATASET,
    subject: "The lexicon bundle behind the Ukrainian text profiler: top-12000 lemmas with validated CEFR levels, Wiktionary paradigm forms and word families, B1 aspect pairs, and two published lexical minimums, packaged for in-browser lemmatization and coverage profiling",
    tier: "public",
    method:
      "lexicon.json: the thread-01 lemma list (rank order) joined per rank to the validated PULS level (null where the profile has none; nothing is guessed), the Wiktionary derivational family id, the aspect-partner pairs from the B1 relation table plus the hand-curated suppletive pairs, and the Borodin A1 and A2 minimums as index sets (with their off-list headwords kept as strings). forms.json: every surface form in the thread-04 Wiktionary paradigm tables mapped to its lemma index, frequency-ordered where a form belongs to several lemmas, omitted where the form equals the lemma. The profiler resolves a token to its exact lemma first, otherwise to the most frequent lemma listed for the form.",
    canonical: "/research/ukrainian-frequency/profiler",
    counts,
    license: LICENSE,
    files: [
      { file: "lexicon.json", about: "lemmas [lemma, pos, level|null, familyId|null] in rank order; families {id: [lemma indices]}; aspectPairs [[i, j]]; sets {borodinA1, borodinA2: {idx, offList}}; listVersion (the list the indices are ranks on); migrate {from, toIndex} (the previous list's index of every row mapped to its index here, -1 where the row was dropped)" },
      { file: "forms.json", about: "forms {surface form: lemma index | [lemma indices, most frequent first]}" },
      { file: "validation.json", about: "the level-asserted validation texts (learn-ukrainian, CC BY-SA 4.0, attributed) the frozen validation run was computed on: id, level, title, url, text" },
    ],
    citation: CITATION,
    sha256: sha,
  };
  const manifestBody = JSON.stringify(manifest, null, 2) + "\n";
  const sumsBody = Object.entries(sha).map(([f, h]) => `${h}  ${f}`).join("\n") + "\n";
  const latestBody = JSON.stringify({ latest: VERSION, path: `/downloads/ukrainian-frequency/profiler/${VERSION}/` }, null, 2) + "\n";

  const dataBody =
    "// GENERATED by scripts/ukrainian-frequency/build-profiler.mjs - do not edit by hand.\n" +
    "// Browser-safe tier of the text profiler (thread 06): the lexicon bundle's\n" +
    "// version, counts and hashes (the bundle itself is downloaded on the first\n" +
    "// analyze gesture, never bundled), plus the frozen validation run over the\n" +
    "// committed level-asserted texts. Re-derives from the committed source tiers;\n" +
    "// the build script's --check mode verifies byte-for-byte reproduction.\n" +
    "export const PROFILER = " +
    JSON.stringify(
      {
        version: VERSION,
        dataset: DATASET,
        license: LICENSE,
        citation: CITATION,
        counts,
        files: ["lexicon.json", "forms.json", "validation.json"],
        sha256: sha,
        downloadBase: `/downloads/ukrainian-frequency/profiler/${VERSION}`,
        validation: {
          setVersion: validationSet.snapshot,
          source: validationSet.source,
          sourceUrl: validationSet.sourceUrl,
          license: validationSet.license,
          levelAssertedBy: validationSet.levelAssertedBy,
          caveat: validationSet.caveat,
          method: validationSet.method,
          count: validationSet.count,
          perLevelCount: validationSet.perLevel,
          lastRun: new Date().toISOString().slice(0, 10),
          ...validation,
          rows: validation.rows.map((r) => ({ ...r, url: validationSet.texts.find((t) => t.id === r.id).url })),
        },
      },
      null,
      2,
    ) +
    ";\n";

  if (CHECK) {
    const committed = readFileSync(path.join(LIB, "profiler.data.mjs"), "utf8");
    // lastRun is a date stamp; compare everything else
    const strip = (s) => s.replace(/"lastRun": "\d{4}-\d{2}-\d{2}"/, '"lastRun": ""');
    if (strip(committed) !== strip(dataBody)) {
      console.error("DRIFT: src/lib/ukrainian-frequency/profiler.data.mjs does not match a fresh build. Run `npm run uk-freq:build-profiler`.");
      process.exit(1);
    }
    for (const [f, body] of [["lexicon.json", lexiconBody], ["forms.json", formsBody], ["validation.json", validationBody], ["SHA256SUMS", sumsBody]]) {
      if (readFileSync(path.join(OUT, f), "utf8") !== body) {
        console.error(`DRIFT: committed profiler ${f} does not match a fresh build. Run \`npm run uk-freq:build-profiler\`.`);
        process.exit(1);
      }
    }
    console.log("Ukrainian Frequency profiler verified: committed tier re-derives byte-for-byte.");
    return;
  }

  const indexBody = renderReleaseIndex({
    kicker: "Open data / Ukrainian Frequency",
    title: "The text profiler's lexicon bundle",
    subject: manifest.subject,
    version: VERSION,
    license: LICENSE,
    canonical: "/research/ukrainian-frequency/profiler",
    citation: CITATION,
    files: ["lexicon.json", "forms.json", "validation.json"],
  });

  // A released bundle is immutable: next.config.mjs serves these three files
  // with `Cache-Control: immutable` for a year, so changed bytes under an
  // existing version would never reach a browser that already holds the old
  // ones. A changed bundle is a new VERSION.
  for (const [f, body] of [["lexicon.json", lexiconBody], ["forms.json", formsBody], ["validation.json", validationBody]]) {
    const p = path.join(OUT, f);
    if (existsSync(p) && readFileSync(p, "utf8") !== body) {
      console.error(`REFUSED: ${VERSION}/${f} is already released and these bytes differ. Bump VERSION; released bundles are served as immutable.`);
      process.exit(1);
    }
  }

  mkdirSync(OUT, { recursive: true });
  writeFileSync(path.join(OUT, "lexicon.json"), lexiconBody);
  writeFileSync(path.join(OUT, "forms.json"), formsBody);
  writeFileSync(path.join(OUT, "validation.json"), validationBody);
  writeFileSync(path.join(OUT, "manifest.json"), manifestBody);
  writeFileSync(path.join(OUT, "SHA256SUMS"), sumsBody);
  writeFileSync(path.join(OUT, "index.html"), indexBody);
  writeFileSync(path.join(LATEST_DIR, "latest.json"), latestBody);
  writeFileSync(path.join(LIB, "profiler.data.mjs"), dataBody);

  console.log("Ukrainian Frequency profiler frozen:", VERSION);
  console.log(JSON.stringify(counts, null, 1));
  const v = validation;
  console.log(`validation: n=${v.n} exact=${v.exact} (${v.exactPct}%) withinOne=${v.withinOne} unresolved=${v.unresolved} ordersLevels=${v.ordersLevels}`);
  console.log(JSON.stringify(v.perLevel, null, 1));
  console.log(JSON.stringify(v.meanAtB1ByAsserted));
  for (const r of v.rows) console.log(r.level, r.id.padEnd(32), `tok=${r.tokens}`, JSON.stringify(r.byLevel), `verdict=${r.verdict}`, `off=${r.offListPct}% unl=${r.unlabeledPct}%`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) main();
