// ---------------------------------------------------------------------------
// Ukrainian Frequency - freeze the lexical-minimum crosswalk. No network.
//
// Runs the committed snapshots (the two "1000 i 1 slovo" minimums, the PULS
// validated CEFR profile, the thread-01 frequency list, the Wiktionary family
// graph) through the pure builder in src/lib/ukrainian-frequency/minimums.mjs
// and writes:
//   public/downloads/ukrainian-frequency/minimums-crosswalk/<version>/
//     crosswalk.csv / crosswalk.json / README.md / manifest.json / SHA256SUMS
//   src/lib/ukrainian-frequency/minimums.data.mjs   (browser-safe tier)
//
//   node scripts/ukrainian-frequency/build-minimums.mjs
//   node scripts/ukrainian-frequency/build-minimums.mjs --check   (verify only)
//
// House rule: no em-dashes in the files this writes.
// ---------------------------------------------------------------------------

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildCrosswalk, crosswalkCsv, parseCsv, CLASSES, CSV_COLUMNS } from "../../src/lib/ukrainian-frequency/minimums.mjs";
import { renderReleaseIndex } from "./lib/release-index.mjs";

const CHECK = process.argv.includes("--check");

const VERSION = "v1.3.0";
const DATASET = "ukrainian-lexical-minimums-crosswalk";
// CC-BY-NC-SA, because every row of this table carries a PULS level and the
// PULS levels are CC BY-NC-SA 4.0 at the authors' decision (2026-09-24). v1.0.0
// first shipped CC-BY-4.0 by mistake and was corrected in place; v1.0.0 and
// v1.1.0 both read CC-BY-SA-4.0, matched to the paper, and both markings are
// superseded while both bundles stay frozen. The Borodin
// volumes remain CC-BY-4.0 in their own right: only the combined table carries
// the profile's terms.
const LICENSE = "CC-BY-NC-SA-4.0";
const SNAPSHOT = "2026-11-20";
const CITATION =
  `Lawrence, J. (2026). A crosswalk between the "1000 i 1 slovo" A1 and A2 lexical minimums and the validated Ukrainian Vocabulary Profile (${VERSION}). jakelawrence.xyz/research/ukrainian-frequency.`;

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DATA = path.join(ROOT, "src", "data", "ukrainian-frequency");
const LIB = path.join(ROOT, "src", "lib", "ukrainian-frequency");
const BASE = path.join(ROOT, "public", "downloads", "ukrainian-frequency", "minimums-crosswalk");
const OUT = path.join(BASE, VERSION);

const sha256 = (body) => createHash("sha256").update(body).digest("hex");
const readJson = (f) => JSON.parse(readFileSync(path.join(DATA, f), "utf8"));

const README = (counts) => `# A crosswalk of the Ukrainian lexical minimums against the validated CEFR profile

Ukrainian has two independent published answers to "which words come first",
built by different methods. This joins them, lemma by lemma, on a corpus
frequency spine, and classifies every place they disagree.

## This version

v1.3.0 (2026-11-20) changes one column. The \`relative\` of an absent row is
partly drawn from the Wiktionary derived-term family graph, and that graph was
rebuilt on 2026-11-20 from the 2026-10-30 Wiktionary extraction with a fuller
reading of its etymologies (see \`../../wiktionary-families/README.md\`), so
129 absent rows name a different relative or gain one where they had none.
No row was added or removed, no class and no level changed. v1.2.0 and the
versions before it stay frozen beside this one.

## The two sides

**The minimums.** "1000 i 1 slovo", the corpus-informed expert lexical minimums
for Ukrainian as a foreign language, in two volumes:

- A1: Kseniia Borodin and Oksana Turkevych, Slavic Language Education 3,
  LANGUAGE-LAB, Humboldt-Universitat zu Berlin. https://doi.org/10.18452/28236
- A2: Kseniia Borodin and Olesia Lazarenko, Europa-Universitat Viadrina
  Frankfurt (Oder), 2026. https://doi.org/10.11584/opus4-1448

Both CC-BY-4.0. Selection mixes GRAK and Ukrainian Web 2022 corpus frequency
with usefulness at the learning stage (method published separately: Borodin and
Lazarenko, New Directions in Slavic Studies, Editorial Universidad de Granada,
2026, 41-52). A teaching syllabus, about 2,000 words.

**The profile.** The Ukrainian Vocabulary Profile on PULS (O. Synchak,
V. Starko, M. Burak, M. Svystun; eLex 2025), the one corpus-VALIDATED
CEFR profile for Ukrainian. ${counts.profileLemmas.toLocaleString("en-US")} lemma strings, A1 to C1. Redistributed
here by permission of the authors. A descriptive map, not a syllabus.

**The spine.** Frequency ranks are the top-12,000 lemma list at
jakelawrence.xyz/research/ukrainian-frequency, derived from UberText 2.0
(Chaplynskyi 2023, lang-uk), CC-BY-4.0.

## What one row is

One row per lemma string in the union of the two sides:
${counts.universe.toLocaleString("en-US")} rows.

| column | meaning |
|---|---|
| \`lemma\` | the lemma string, stress accent stripped, apostrophe folded to U+2019 |
| \`rank\` | frequency rank on the top-12,000 list, blank if the corpus never reached it |
| \`pos\` | UD part of speech from the frequency list, blank if off-list |
| \`volume\` | \`A1\` or \`A2\` if a minimum carries it, blank otherwise (a word in both counts as A1) |
| \`entry\` | the published entry line it came from, verbatim |
| \`validatedLevel\` | the profile's level, blank where the profile does not cover it |
| \`class\` | see below |
| \`relative\` | for an absent row, where a minimum does reach the word after all |
| \`relativeVia\` | \`phrase\` (it appears inside a multi-word entry), or \`family\`, \`contains\`, \`stem\` (a headword plausibly on the same root) |

Classes:

${Object.entries(CLASSES).map(([k, v]) => `- \`${k}\` (${counts.byClass[k].toLocaleString("en-US")}): ${v}`).join("\n")}

## How a row is matched, and what that costs

Both sides join by lemma string. The stress accent (U+0301) is pedagogical, not
lexical, so it is stripped; the apostrophe is folded across all four glyphs the
sources use and the one HTML entity the PULS harvest preserved. Two limits
follow, and no claim here survives ignoring them:

- **No part of speech on the minimum side.** The published lists carry none, so
  homographs collapse into one row.
- **Onset, not sense.** A profile level is the level of the lexeme's earliest
  sense. A word can be validated A1 for a basic sense while a minimum teaches a
  different sense of it. A string crosswalk cannot see that.
- **The frequency spine is lemmatized automatically** and carries its own
  errors. \`rok\` at rank 97 is the clearest: it absorbs tokens of \`rik\` (year,
  rank 13). Ranks are a rough ordering, not evidence about a word.
- **The three sources do not agree on what counts as one lemma.** \`te\` heads the
  absent list at rank 27, and it is not a word the minimums forgot: the spine
  and the profile both treat it as a lemma, while the minimums treat it as the
  neuter of \`toi\`, which the A2 volume carries. Read the absent list as
  candidates to check, never as a list of omissions.

A word that appears only inside a multi-word entry is not a member (the volume
does not list it as a word) but its absent row names the phrase, so \`takyi\` reads
against \`takyi samyi\` and \`zhal\` against \`Na zhal\`. ${counts.absentInPhrase} rows are of that kind.

An entry line can name several words (an aspect pair, a gender pair, a spelling
variant set), and every one of them counts as carried. Inside a parenthesis the
authors separate alternatives with a semicolon and paradigm forms with a comma,
and a parenthesis with no space in front of it continues the word it touches
(\`vmyvaty(sia)\` gives both \`vmyvaty\` and \`vmyvatysia\`); the parser follows
that.

## Reading the \`unprofiled\` class fairly

${counts.byClass.unprofiled.toLocaleString("en-US")} minimum words carry no validated level. They are mostly proper nouns and
the adjectives built on them (Ukraine, Kyiv, Poland, Ukrainian, German), which a
vocabulary profile does not set out to cover. This is a note about scope, not a
gap in the profile.

## Where it fits

The per-volume joins are \`../../borodin-a1/\` and \`../../borodin-a2/\`, which
compare each minimum with the frequency list only. This file reads both volumes
against the whole validated profile; \`../../validated-cefr/\` is the same
profile cut to the top-12,000 list. To attach any other list column, join
\`rank\` to \`../../v0.2.0/lemmas.csv\` (a blank rank is a word the list never
reached).

The research page renders the classes as a contingency grid at
/research/ukrainian-frequency/crosswalk, where every cell is a selectable word
set, with the method at /research/ukrainian-frequency/crosswalk/method. The
\`ukvocab\` Python package ships this table, and it is a Zenodo deposit. The
same entry-reading fix was applied to the text profiler's Borodin known-word
sets.

## Reproduce

\`\`\`
node scripts/ukrainian-frequency/build-minimums.mjs
node scripts/ukrainian-frequency/build-minimums.mjs --check
\`\`\`

Deterministic, offline, from committed snapshots only. \`--check\` verifies the
committed bundle re-derives byte for byte. CI enforces the same thing through
the test suite, which rebuilds the crosswalk from the snapshots and compares it
to the frozen files and their hashes.

## License and attribution

**This crosswalk: CC-BY-NC-SA-4.0.** Every row carries a PULS level, and the
PULS levels are CC BY-NC-SA 4.0 at the authors' decision (2026-09-24), so the
NonCommercial and share-alike terms propagate to the combined table. The
Borodin volumes stay CC-BY-4.0 in their own right; the profile's terms apply to
this joined file, not to its sources. Versions before v1.2.0 carry a superseded
CC-BY-SA marking; the levels in them are under these same terms.

It is a derived, factual join. Attribute the sources it joins, not only this
file:

- Minimums: Borodin and Turkevych (A1, DOI 10.18452/28236); Borodin and
  Lazarenko (A2, DOI 10.11584/opus4-1448). Both CC-BY-4.0.
- Validated levels: Synchak, O., Starko, V., Burak, M., Svystun, M., Ukrainian Vocabulary
  Profile / PULS. CC-BY-NC-SA-4.0, redistributed by the authors' permission.
  Cite as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026.
- Frequency ranks: UberText 2.0 (Chaplynskyi 2023, lang-uk), CC-BY-4.0.

Cite as: ${CITATION}

Snapshot: ${SNAPSHOT}
`;

function main() {
  const built = buildCrosswalk({
    seed: readJson("ubertext-lemmas-top12k.json"),
    a1raw: readJson("borodin-a1.raw.json"),
    a2raw: readJson("borodin-a2.raw.json"),
    pulsRaw: parseCsv(readFileSync(path.join(DATA, "puls-cefr.raw.csv"), "utf8")),
    families: readJson("wiktionary-families.json"),
  });
  const { rows, counts, sets } = built;

  const csvBody = crosswalkCsv(rows);
  const jsonBody = `${JSON.stringify({ version: VERSION, dataset: DATASET, license: LICENSE, snapshot: SNAPSHOT, citation: CITATION, columns: CSV_COLUMNS, classes: CLASSES, counts, rows }, null, 2)}\n`;
  const readmeBody = README(counts);

  const sha = {
    "crosswalk.csv": sha256(csvBody),
    "crosswalk.json": sha256(jsonBody),
    "README.md": sha256(readmeBody),
  };
  const manifest = {
    version: VERSION,
    dataset: DATASET,
    subject:
      "Every lemma in the union of the two published Ukrainian A1/A2 lexical minimums and the validated Ukrainian Vocabulary Profile, joined on a corpus frequency spine, with each agreement and disagreement classified",
    tier: "public",
    method:
      "Both sides joined by lemma string with the pedagogical stress accent stripped and the apostrophe folded across glyphs and the one HTML entity. Minimum membership is per headword, so every word an entry line names counts; a word in both volumes counts as A1. The profile level is the onset level of the lexeme's earliest sense, taken from the whole published profile rather than its top-12000 slice, so a minimum word off the frequency list can still be compared. Absent rows carry a deliberately over-matching relative flag (derivational family, substring, or shared stem) so the unflagged residue is conservative.",
    canonical: "/research/ukrainian-frequency",
    snapshot: SNAPSHOT,
    counts,
    license: LICENSE,
    files: [
      { file: "crosswalk.csv", about: `one row per lemma: ${CSV_COLUMNS.join(", ")}` },
      { file: "crosswalk.json", about: "the same rows plus the contingency table and per-class counts" },
      { file: "README.md", about: "provenance, the join's two limits, and attribution for all four sources" },
    ],
    citation: CITATION,
    sha256: sha,
  };
  const manifestBody = `${JSON.stringify(manifest, null, 2)}\n`;
  const sumsBody = `${Object.entries(sha).map(([f, h]) => `${h}  ${f}`).join("\n")}\n`;
  const latestBody = `${JSON.stringify({ latest: VERSION, path: `/downloads/ukrainian-frequency/minimums-crosswalk/${VERSION}/` }, null, 2)}\n`;

  const top = (list, n) => list.slice(0, n).map((r) => ({ lemma: r.lemma, rank: r.rank, pos: r.pos, volume: r.volume, level: r.level }));
  const dataBody =
    "// GENERATED by scripts/ukrainian-frequency/build-minimums.mjs - do not edit by hand.\n" +
    "// Browser-safe tier of the lexical-minimum crosswalk: the contingency table,\n" +
    "// the per-class counts, and a frequency-ordered head of each disagreement set.\n" +
    "// The full row table is a download. Re-derives from the committed snapshots;\n" +
    "// the build script's --check mode verifies byte-for-byte reproduction.\n" +
    "export const MINIMUMS = " +
    JSON.stringify(
      {
        version: VERSION,
        dataset: DATASET,
        license: LICENSE,
        snapshot: SNAPSHOT,
        citation: CITATION,
        counts,
        classes: CLASSES,
        files: ["crosswalk.csv", "crosswalk.json", "README.md"],
        sha256: sha,
        downloadBase: `/downloads/ukrainian-frequency/minimums-crosswalk/${VERSION}`,
        samples: {
          later: top(sets.later, 24),
          absentA1: top(sets.absentA1.filter((r) => !r.relative), 24),
          absentA2: top(sets.absentA2.filter((r) => !r.relative), 24),
          earlier: top(sets.earlier, 24),
          unprofiled: top(sets.unprofiled, 24),
        },
      },
      null,
      2,
    ) +
    ";\n";

  if (CHECK) {
    const committed = readFileSync(path.join(LIB, "minimums.data.mjs"), "utf8");
    if (committed !== dataBody) {
      console.error("DRIFT: src/lib/ukrainian-frequency/minimums.data.mjs does not match a fresh build. Run `npm run uk-freq:build-minimums`.");
      process.exit(1);
    }
    for (const [f, body] of [["crosswalk.csv", csvBody], ["crosswalk.json", jsonBody], ["README.md", readmeBody], ["manifest.json", manifestBody], ["SHA256SUMS", sumsBody]]) {
      if (readFileSync(path.join(OUT, f), "utf8") !== body) {
        console.error(`DRIFT: committed crosswalk ${f} does not match a fresh build. Run \`npm run uk-freq:build-minimums\`.`);
        process.exit(1);
      }
    }
    console.log("Ukrainian Frequency minimum crosswalk verified: committed tier re-derives byte-for-byte.");
    return;
  }

  const indexBody = renderReleaseIndex({
    kicker: "Open data / Ukrainian Frequency",
    title: "The lexical-minimum crosswalk",
    subject: manifest.subject,
    version: VERSION,
    license: LICENSE,
    canonical: "/research/ukrainian-frequency",
    citation: CITATION,
    files: ["crosswalk.csv", "crosswalk.json", "README.md"],
  });

  mkdirSync(OUT, { recursive: true });
  writeFileSync(path.join(OUT, "crosswalk.csv"), csvBody);
  writeFileSync(path.join(OUT, "crosswalk.json"), jsonBody);
  writeFileSync(path.join(OUT, "README.md"), readmeBody);
  writeFileSync(path.join(OUT, "manifest.json"), manifestBody);
  writeFileSync(path.join(OUT, "SHA256SUMS"), sumsBody);
  writeFileSync(path.join(OUT, "index.html"), indexBody);
  writeFileSync(path.join(BASE, "latest.json"), latestBody);
  writeFileSync(path.join(LIB, "minimums.data.mjs"), dataBody);

  const t = counts.table;
  console.log(`crosswalk ${VERSION}: ${counts.universe.toLocaleString("en-US")} rows`);
  console.log(`  agree ${counts.byClass.agree}  earlier ${counts.byClass.earlier}  later ${counts.byClass.later}  absent ${counts.byClass.absent}  unprofiled ${counts.byClass.unprofiled}  beyond ${counts.byClass.beyond}`);
  console.log(`  A1 volume: ${counts.a1Headwords} headwords, ${t.A1.A1} validated A1`);
  console.log(`  A2 volume: ${counts.a2Headwords} headwords, ${t.A2.A2} validated A2`);
  console.log(`  validated A1 the A1 volume defers to A2: ${counts.laterAtA1}; in neither volume: ${counts.absentA1} (${counts.absentA1NoRelative} with no relative carried)`);
}

main();
