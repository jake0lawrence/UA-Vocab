// ---------------------------------------------------------------------------
// Ukrainian Frequency - freeze the word-stress overlay (thread 07). No network.
//
// Runs the committed, reviewed stress snapshot (src/data/ukrainian-frequency/
// stress.json), the manual-decision ledger (stress-overrides.json, applied
// last) and the adjudication log through the pure builder in
// src/lib/ukrainian-frequency/stress.mjs, reads the thread-04 paradigms file
// against it, and writes:
//   public/downloads/ukrainian-frequency/stress/<version>/
//     stress.csv / stress.json / stress.anki.tsv / adjudication.csv /
//     paradigm-disagreements.csv / README.md / manifest.json / SHA256SUMS / index.html
//   public/downloads/ukrainian-frequency/stress/latest.json
//   src/lib/ukrainian-frequency/stress.data.mjs   (browser-safe tier)
//
//   node scripts/ukrainian-frequency/build-stress.mjs
//   node scripts/ukrainian-frequency/build-stress.mjs --check   (verify only)
//
// House rule: no em-dashes in the files this writes.
// ---------------------------------------------------------------------------

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildStress,
  STRESS_VERSION,
  STRESS_DATASET,
  STRESS_LICENSE,
  STRESS_LIST,
  STATUSES,
  FILES,
  CSV_COLUMNS,
} from "../../src/lib/ukrainian-frequency/stress.mjs";
import { renderReleaseIndex } from "./lib/release-index.mjs";

const CHECK = process.argv.includes("--check");

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DATA = path.join(ROOT, "src", "data", "ukrainian-frequency");
const LIB = path.join(ROOT, "src", "lib", "ukrainian-frequency");
const DL = path.join(ROOT, "public", "downloads", "ukrainian-frequency");
const BASE = path.join(DL, "stress");
const OUT = path.join(BASE, STRESS_VERSION);

const sha256 = (body) => createHash("sha256").update(body).digest("hex");
const readJson = (f) => JSON.parse(readFileSync(path.join(DATA, f), "utf8"));
const n = (x) => x.toLocaleString("en-US");

const CITATION = `Lawrence, J. (2026). Ukrainian Frequency: a per-lemma word-stress column for the top-12,000 list (${STRESS_VERSION}). jakelawrence.xyz/research/ukrainian-frequency. Over ukrainian-word-stress (lang-uk), en.wiktionary and uk.wiktionary.`;
const SUBJECT = "Word stress for every lemma of the top-12,000 Ukrainian frequency list: one confident stress where the sources agree, labeled variants and homographs where they do not, provenance per row; proper nouns kept but out of scope";
const METHOD =
  "Nine stages, applied in order: the lang-uk ukrainian-word-stress dictionary read directly from its trie and filtered by the list's own UD part of speech and lemma features (no tagger guess on a bare lemma); en.wiktionary (kaikki.org), which separates free variants, homographs and minor variants; uk.wiktionary (the dump); a two-of-three vote where the three disagree; rules for conflicts that are only apparent (compound secondary stress, doubled-accent artifacts); goroh.pp.ua tiebreaks for what is left, one reference lookup per word, recorded as the attested stress only; rules for lemmas no source covers (standard spelling, compounds, acronyms, -енко surnames); uk.wikipedia lead sentences for names; and the manual-decision ledger applied last.";

const README = (stats, snapshot) => `# Ukrainian Frequency, thread 07: word stress

A stressed form for every one of the 12,000 lemmas of the thread-01 frequency
list (v0.2.0). Ukrainian stress is free and mobile, so it cannot be read off the
spelling, and it is the gap learners ask about most. Where the sources agree
there is one stress; where they do not, the row says so instead of guessing.

Join on \`rank\` to \`../../v0.2.0/lemmas.csv\`. The \`lemma\` and \`pos\` columns are
the list's own and a test holds them to it.

## The numbers

| | count |
|---|---|
| lemmas | ${n(stats.lemmas)} |
| proper nouns, out of scope (kept, not counted) | ${n(stats.tiers.scope)} |
| polysyllabic common words (the denominator) | ${n(stats.polysyllabic)} |
| one confident stress | ${n(stats.tiers.one)} (${stats.onePct}% of polysyllabic) |
| labeled: variant, homograph, name, dictionary-only doublet | ${n(stats.tiers.labeled)} (confident or labeled: ${stats.oneOrLabeledPct}%) |
| monosyllabic, no mark needed | ${n(stats.tiers.trivial)} |
| still missing | ${n(stats.tiers.missing)} (${Object.entries(stats.missingByPos).sort((a, b) => b[1] - a[1]).map(([p, c]) => `${c} ${p}`).join(", ")}) |

Proper nouns are **out of scope** by owner decision (2026-10-01), as most learner
lists leave names out: every PROPN row keeps the stress the pipeline found and
the pipeline's own status in \`note\`, carries \`stress_status\` \`proper_noun\`,
and is counted in none of the shares above. Filter on \`pos != PROPN\` for the
column as claimed.

## \`stress.csv\` (one row per lemma)

| column | meaning |
|---|---|
| \`rank\` | the lemma's rank on the thread-01 list (1 = most frequent) |
| \`lemma\` | the dictionary form, the list's own spelling |
| \`pos\` | Universal Dependencies part of speech, the list's own tag |
| \`stress\` | the primary stressed form; the stress mark is the combining acute U+0301; empty when \`stress_status\` is \`missing\` |
| \`stress_variants\` | pipe-separated, primary first; set when more than one stress is valid or possible |
| \`stress_status\` | how the row was resolved (table below) |
| \`note\` | glosses for a homograph, the secondary stress of a compound, the standard spelling of a nonstandard lemma, or the other source's reading |
| \`source\` | provenance of the chosen stress: the dictionary, the Wiktionary that resolved it, the vote, the rule, the goroh tiebreak, or the uk.wikipedia article title |

\`stress.json\` is the same table with the counts and this status table in the
header. \`stress.anki.tsv\` is an Anki-importable seed: stressed form, part of
speech, rank, variants, status, one note per lemma, most frequent first.

### \`stress_status\`

| status | count | meaning |
|---|---|---|
${Object.entries(STATUSES).filter(([k]) => stats.byStatus[k] > 0).map(([k, v]) => `| \`${k}\` | ${n(stats.byStatus[k])} | ${v.about} |`).join("\n")}

## \`adjudication.csv\`

Every lemma the sources disagreed on (${n(stats.adjudicated)} rows), with each
source's vote and the decision taken: the show-your-work layer. The
${n(stats.overrides)} manual decisions, including the ${n(stats.goroh)} rows that cite a goroh.pp.ua
tiebreak, are in the repository's \`stress-overrides.json\` and are applied last
by the builder, so a rebuilt pipeline reproduces them and a test fails if a
goroh-backed row changes without an entry there.

## \`doublets.csv\`

The ${n(stats.doubletsOpen)} in-scope rows where the dictionary lists two stresses and no open
source covers the word (\`stress_status\` \`doublet_dictionary_only\`; the primary
is the first listed). By owner decision (2026-10-01) these are settled from a
printed orthoepic dictionary (Pohribnyi, Orfoepichnyi slovnyk) rather than from
goroh.pp.ua, which would otherwise become a pillar of the data: each lookup
enters \`stress-overrides.json\` with the page as evidence, and the same test
that holds goroh refuses a row citing the printed source without a ledger entry.
This file is the worklist; it shrinks as the ledger grows.

## \`paradigm-disagreements.csv\`

This column read against the headwords of the thread-04 paradigms file
(\`../../paradigms/\`, Wiktionary's forms, verbatim): ${n(stats.paradigmDisagreements)} rows where the
paradigm's headword stress is not one this column accepts. \`verdict\`
\`stress_column\` (${n(stats.paradigmCorrections)} rows) means the paradigm headword is the one to
correct and the \`evidence\` column says why (goroh and the dictionary agree
against en.wiktionary; or the paradigm joined the other homograph, as музи́ка the
musician for му́зика the music). \`open\` means neither side is adjudicated:
a review queue, not a verdict. The paradigms file is not patched: it is a
verbatim mirror and the next dump would overwrite the patch; the corrections
are published here and queued upstream instead.

## Method

${METHOD}

Two things the method does not do. It does not let any one source win by
default: en.wiktionary was wrong against goroh on по́каз, нульови́й, побажа́ння and
казко́вий, and the library dictionary was wrong twice (йо́го for його́ at rank 40,
підозрюва́тися for підо́зрюватися). And it does not guess a homograph's primary
where the corpus cannot tell the readings apart: ${n(stats.homographsCounted)} homographs whose two
readings differ in spelling somewhere in the paradigm (прохо́дити / проходи́ти)
take their primary from a count of those distinguishing forms across the five
UberText 2.0 subcorpora, after every form that is also another word's (заходи,
the imperative of заходи́ти and the plural of захід) is struck by the site's own
VESUM lemmatizer (\`homograph_corpus\`, counts in \`source\`;
${n(stats.homographsFlipped)} of them flipped from the first en.wiktionary entry); the ${n(stats.byStatus.homograph)} whose
forms are spelled alike in every cell (о́рган / орга́н) keep the first
en.wiktionary entry as primary and say in \`note\` that it is unverified.

## Source and license

- **ukrainian-word-stress** 2.1.0 (lang-uk: Oleksiy Syvokon, maintained by Dmytro Chaplynskyi), MIT.
  https://github.com/lang-uk/ukrainian-word-stress. The dictionary baseline for
  ${n(stats.provenance.library)} rows. (v1.0.1, 2026-10-07, corrects this credit:
  the v1.0.0 README named a reader who pointed at the library as its
  maintainer. The data files are byte-identical to v1.0.0, which stays
  published under its own DOI.)
- **v1.0.2** (2026-10-09) changes one row: тризуб (rank 11,982) moves from the
  dictionary's тризу́б to \`free_variant\` with три́зуб first. A native-speaker
  reader reported три́зуб as the form in speech, the open recording carries it,
  and e2u.org.ua lists both; the decision is in the manual ledger.
- **en.wiktionary** via kaikki.org (wiktextract) and **uk.wiktionary** (the
  dump), CC-BY-SA 3.0. Resolve doublets, fill gaps, and vote.
- **uk.wikipedia** lead sentences, CC-BY-SA 4.0, for ${n(stats.provenance.wikipedia)} proper nouns; the
  article title is in \`source\`.
- **goroh.pp.ua** for ${n(stats.goroh)} tiebreaks: only the attested stress is recorded, no
  content is copied, and every such row is a ledgered manual decision.
- Ranks, lemmas and tags: UberText 2.0 (Chaplynskyi 2023, lang-uk), CC-BY 4.0.

**This file: CC-BY-SA 4.0**, because the Wiktionary-derived rows carry
share-alike. It is kept as its own file, joined on rank, rather than a column
on \`lemmas.csv\`, so the list itself stays CC-BY 4.0.

Cite as: ${CITATION}

Snapshot: ${snapshot}
`;

function main() {
  const snapshot = readJson("stress.json");
  const overrides = readJson("stress-overrides.json");
  const adjudication = readJson("stress-adjudication.json");
  const homographs = existsSync(path.join(DATA, "stress-homographs.json")) ? readJson("stress-homographs.json") : null;
  const seed = readJson("ubertext-lemmas-top12k.json");
  const paradigmForms = gunzipSync(readFileSync(path.join(DL, "paradigms", "forms.csv.gz"))).toString("utf8");

  const { rows, stats, bodies } = buildStress({ snapshot, overrides, adjudication, seed, homographs, paradigmForms, citation: CITATION });
  bodies["README.md"] = README(stats, snapshot.snapshot);

  const sha = {};
  for (const f of FILES) sha[f] = sha256(bodies[f]);

  const manifest = {
    version: STRESS_VERSION,
    dataset: STRESS_DATASET,
    subject: SUBJECT,
    tier: "public",
    method: METHOD,
    canonical: "/research/ukrainian-frequency#stress",
    list: STRESS_LIST,
    snapshot: snapshot.snapshot,
    library: snapshot.library,
    counts: { lemmas: stats.lemmas, properNouns: stats.properNouns, homographsCounted: stats.homographsCounted, homographsFlipped: stats.homographsFlipped, polysyllabic: stats.polysyllabic, tiers: stats.tiers, onePct: stats.onePct, oneOrLabeledPct: stats.oneOrLabeledPct, byStatus: stats.byStatus, provenance: stats.provenance, goroh: stats.goroh, overrides: stats.overrides, doubletsOpen: stats.doubletsOpen, paradigmDisagreements: stats.paradigmDisagreements, paradigmCorrections: stats.paradigmCorrections },
    scope: "Proper nouns (PROPN) are out of scope by owner decision 2026-10-01: kept with the pipeline's stress and status in the note, counted in no share.",
    license: STRESS_LICENSE,
    files: [
      { file: "stress.csv", about: `one row per lemma: ${CSV_COLUMNS.join(", ")}` },
      { file: "stress.json", about: "the same rows with the counts and the status table in the header" },
      { file: "stress.anki.tsv", about: "an Anki-importable seed: stressed form, part of speech, rank, variants, status" },
      { file: "adjudication.csv", about: "every lemma the sources disagreed on, with each source's vote and the decision" },
      { file: "paradigm-disagreements.csv", about: "this column read against the thread-04 paradigm headwords, with a verdict per row" },
      { file: "doublets.csv", about: "the in-scope dictionary-only doublets still open, the worklist for the printed-source pass" },
      { file: "README.md", about: "columns, the status taxonomy, method, sources and attribution" },
    ],
    citation: CITATION,
    sha256: sha,
  };
  const manifestBody = `${JSON.stringify(manifest, null, 2)}\n`;
  const sumsBody = `${FILES.map((f) => `${sha[f]}  ${f}`).join("\n")}\n`;
  const latestBody = `${JSON.stringify({ latest: STRESS_VERSION, path: `/downloads/ukrainian-frequency/stress/${STRESS_VERSION}/` }, null, 2)}\n`;

  const pick = (r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, stress: r.stress, variants: r.variants, status: r.status, note: r.note });
  const samples = {
    head: rows.filter((r) => r.status !== "monosyllabic" && r.status !== "proper_noun").slice(0, 16).map(pick),
    homographs: [
      ...rows.filter((r) => r.status === "homograph_corpus").slice(0, 6).map((r) => ({ ...pick(r), source: r.source })),
      ...rows.filter((r) => r.status === "homograph" && r.note).slice(0, 6).map(pick),
    ],
    freeVariants: rows.filter((r) => r.status === "free_variant").slice(0, 8).map(pick),
  };
  const dataBody =
    "// GENERATED by scripts/ukrainian-frequency/build-stress.mjs - do not edit by hand.\n" +
    "// Browser-safe tier of thread 07 (word stress): the counts per tier, status,\n" +
    "// provenance and rank band, a few sample rows, the file list and hashes of\n" +
    "// the committed open-data bundle. The full 12,000-row table is a download.\n" +
    "// Re-derives from the committed snapshot; the build script's --check mode\n" +
    "// verifies byte-for-byte reproduction and CI re-hashes the files.\n" +
    "export const STRESS = " +
    JSON.stringify(
      {
        version: STRESS_VERSION,
        dataset: STRESS_DATASET,
        license: STRESS_LICENSE,
        list: STRESS_LIST,
        snapshot: snapshot.snapshot,
        citation: CITATION,
        library: snapshot.library,
        stats,
        samples,
        files: FILES,
        sha256: sha,
        downloadBase: `/downloads/ukrainian-frequency/stress/${STRESS_VERSION}`,
      },
      null,
      2,
    ) +
    ";\n";

  const expected = [...FILES.map((f) => [f, bodies[f]]), ["manifest.json", manifestBody], ["SHA256SUMS", sumsBody]];

  if (CHECK) {
    const committed = existsSync(path.join(LIB, "stress.data.mjs")) ? readFileSync(path.join(LIB, "stress.data.mjs"), "utf8") : "";
    if (committed !== dataBody) {
      console.error("DRIFT: src/lib/ukrainian-frequency/stress.data.mjs does not match a fresh build. Run `npm run uk-freq:build-stress`.");
      process.exit(1);
    }
    for (const [f, body] of expected) {
      if (!existsSync(path.join(OUT, f)) || readFileSync(path.join(OUT, f), "utf8") !== body) {
        console.error(`DRIFT: committed stress/${STRESS_VERSION}/${f} does not match a fresh build. Run \`npm run uk-freq:build-stress\`.`);
        process.exit(1);
      }
    }
    if (!existsSync(path.join(BASE, "latest.json")) || readFileSync(path.join(BASE, "latest.json"), "utf8") !== latestBody) {
      console.error(`DRIFT: stress/latest.json does not point at ${STRESS_VERSION}. Run \`npm run uk-freq:build-stress\`.`);
      process.exit(1);
    }
    console.log("Ukrainian Frequency stress overlay verified: committed tier re-derives byte-for-byte.");
    return;
  }

  const indexBody = renderReleaseIndex({
    kicker: "Open data / Ukrainian Frequency",
    title: "Word stress for the top-12,000 lemmas",
    subject: SUBJECT,
    version: STRESS_VERSION,
    license: STRESS_LICENSE,
    canonical: "/research/ukrainian-frequency#stress",
    citation: CITATION,
    files: FILES,
  });

  mkdirSync(OUT, { recursive: true });
  for (const [f, body] of expected) writeFileSync(path.join(OUT, f), body);
  writeFileSync(path.join(OUT, "index.html"), indexBody);
  writeFileSync(path.join(BASE, "latest.json"), latestBody);
  writeFileSync(path.join(LIB, "stress.data.mjs"), dataBody);

  console.log(`stress ${STRESS_VERSION}: ${n(stats.lemmas)} rows`);
  console.log(`  one confident stress ${n(stats.tiers.one)} (${stats.onePct}% of ${n(stats.polysyllabic)} in-scope polysyllabic) | labeled ${stats.tiers.labeled} | missing ${stats.tiers.missing} | proper nouns out of scope ${n(stats.tiers.scope)} | doublets open ${stats.doubletsOpen}`);
  console.log(`  goroh tiebreaks ${stats.goroh} | overrides ${stats.overrides} | paradigm disagreements ${stats.paradigmDisagreements} (${stats.paradigmCorrections} corrected here)`);
  console.log(`  files ${FILES.length} | license ${STRESS_LICENSE}`);
}

main();
