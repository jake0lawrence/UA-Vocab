#!/usr/bin/env node
// ---------------------------------------------------------------------------
// Snapshot the dmklinger/ukrainian dictionary for the list's lemmas.
//
//   node scripts/ukrainian-frequency/fetch-dmk-dictionary.mjs            # fetch + write
//   node scripts/ukrainian-frequency/fetch-dmk-dictionary.mjs --from f   # from a local words.json
//
// The upstream is Daniel Klinger's Ukrainian-to-English dictionary
// (github.com/dmklinger/ukrainian, CC BY-SA 3.0): 30,000-odd headwords with
// stress marks, English definitions, gender and animacy, scraped from
// Wiktionary and DBnary with forms from the ULIF national dictionary. Andrij
// Rudnitsky hosts it behind a lookup API he reads from his watch; this snapshot
// is what lets this site answer the same question from committed data.
//
// Only entries whose headword (stress stripped, apostrophe folded) is one of
// the 12,000 list lemmas are kept, without the forms (thread 04 carries the
// list's own paradigms). The raw file's SHA-256 and entry count are recorded
// so the snapshot can be reproduced and told apart from a later upstream.
// Network only here; everything downstream reads the committed snapshot.
// House rule: no em dashes.
// ---------------------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { normalizeToken } from "../../src/lib/ukrainian-frequency/profiler/tokenize.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DATA = path.join(ROOT, "src/data/ukrainian-frequency");
const OUT = path.join(DATA, "dmk-dictionary.json");
const SOURCE_MD = path.join(DATA, "dmk-dictionary.SOURCE.md");

export const UPSTREAM = {
  repo: "https://github.com/dmklinger/ukrainian",
  file: "words.json",
  url: "https://raw.githubusercontent.com/dmklinger/ukrainian/master/words.json",
  license: "CC BY-SA 3.0",
  author: "Daniel Klinger",
};

const args = process.argv.slice(2);
const fromIdx = args.indexOf("--from");
const local = fromIdx >= 0 ? args[fromIdx + 1] : null;

async function readUpstream() {
  if (local) return fs.readFileSync(local);
  const res = await fetch(UPSTREAM.url, { signal: AbortSignal.timeout(120_000) });
  if (!res.ok) throw new Error(`upstream ${res.status} for ${UPSTREAM.url}`);
  return Buffer.from(await res.arrayBuffer());
}

function readList() {
  const seed = JSON.parse(fs.readFileSync(path.join(DATA, "ubertext-lemmas-top12k.json"), "utf8"));
  const byKey = new Map();
  const lemmaOf = [];
  seed.rows.forEach((r, i) => {
    const key = normalizeToken(r.lemma);
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(i + 1);
    lemmaOf[i + 1] = r.lemma;
  });
  return { byKey, lemmaOf, n: seed.rows.length };
}

// House rule, applied to quoted definitions too: no em dashes leave the site.
// A spaced dash becomes a comma, an unspaced one a hyphen; recorded in the
// SOURCE note so the snapshot is never mistaken for the upstream text.
function plainDash(s) {
  return s.replace(/\s*\u2014\s*/g, (m) => (/\s/.test(m) ? ", " : "-"));
}

const raw = await readUpstream();
const sha256 = crypto.createHash("sha256").update(raw).digest("hex");
const words = JSON.parse(raw.toString("utf8"));
if (!Array.isArray(words)) throw new Error("words.json is not an array");
const list = readList();

const entries = [];
for (const w of words) {
  if (!w || typeof w.word !== "string") continue;
  // An affix entry (-ти, по-) is not a word; the tokenizer would strip its
  // hyphen and land it on a real lemma.
  if (/^-|-$/.test(w.word.normalize("NFC").replace(/\u0301/g, ""))) continue;
  const key = normalizeToken(w.word);
  // The tokenizer also trims a leading hyphen or a trailing apostrophe, and
  // the list keeps both (-то, the enclitic particle, is not то), so after the
  // match the bare headword has to spell the lemma exactly, case and
  // apostrophe glyph aside.
  const bare = w.word.normalize("NFC").replace(/\u0301/g, "").replace(/['ʼ`]/g, "\u2019").toLowerCase();
  const ranks = (list.byKey.get(key) || []).filter((r) => list.lemmaOf[r].normalize("NFC").toLowerCase() === bare);
  if (!ranks.length) continue;
  entries.push({
    word: w.word.normalize("NFC"),
    pos: w.pos || "",
    defs: Array.isArray(w.defs) ? w.defs.map((d) => plainDash(String(d).normalize("NFC"))) : [],
    info: typeof w.info === "string" ? w.info : "",
    freq: Number.isInteger(w.freq) ? w.freq : null,
    ranks,
  });
}
entries.sort((a, b) => a.ranks[0] - b.ranks[0] || a.word.localeCompare(b.word, "uk") || a.pos.localeCompare(b.pos));
const coveredRanks = new Set(entries.flatMap((e) => e.ranks));
const fetched = new Date().toISOString().slice(0, 10);

const snapshot = {
  source: { ...UPSTREAM, fetched, sha256, entries: words.length },
  list: "v0.2.0",
  lemmas: list.n,
  covered: coveredRanks.size,
  kept: entries.length,
  entries,
};
const body =
  "{\n" +
  Object.entries(snapshot)
    .map(([k, v]) =>
      k === "entries"
        ? `"entries": [\n${v.map((e) => JSON.stringify(e)).join(",\n")}\n]`
        : `"${k}": ${JSON.stringify(v)}`,
    )
    .join(",\n") +
  "\n}\n";
fs.writeFileSync(OUT, body);

const md = `# dmklinger/ukrainian dictionary snapshot (thread 07 companion)

\`dmk-dictionary.json\` is a SNAPSHOT of the open Ukrainian-to-English
dictionary at ${UPSTREAM.repo} (${UPSTREAM.author}, ${UPSTREAM.license}),
restricted to the headwords that are lemmas of list v0.2.0. It is the data
behind the word lookup (\`/research/ukrainian-frequency/lookup\`,
\`GET /api/uk/lookup/<word>\`) and the third reading of the stress column.
Regenerate with \`npm run uk-freq:fetch-dmk\` (network).

## Provenance

| field | value |
|---|---|
| upstream file | \`${UPSTREAM.file}\` at ${UPSTREAM.url} |
| fetched | ${fetched} |
| upstream SHA-256 | \`${sha256}\` |
| upstream entries | ${words.length.toLocaleString("en-US")} |
| kept entries | ${entries.length.toLocaleString("en-US")} (headword is a list lemma, stress stripped, apostrophe folded) |
| list lemmas covered | ${coveredRanks.size.toLocaleString("en-US")} of ${list.n.toLocaleString("en-US")} |

The upstream README states its sources: definitions scraped from the English
Wiktionary and from DBnary (which carries definitions for words Wiktionary has
no entry for yet), inflected forms filled from the ULIF national dictionary
(lcorp.ulif.org.ua) where a match was found. The headword carries the stress
mark the source gave it; an either-stress headword keeps both marks
(\`та́ко́ж\`), the Wiktionary notation the stress column splits into variants.

## What is kept per entry

\`word\` (the stressed headword, NFC), \`pos\` (the dictionary's own label:
noun, verb, adjective, adverb, particle, phrase, numeral, pronoun), \`defs\`
(the English definitions in the dictionary's order), \`info\` (gender and
animacy for nouns), \`freq\` (the dictionary's own frequency figure, kept for
reference, not this list's rank), \`ranks\` (the list ranks whose lemma this
headword spells; usually one, two where the list keeps a word under two tags).
The forms are dropped: thread 04 publishes the list's own paradigms. One
normalization is applied to the definitions: the em dash (U+2014), which the
upstream uses inside a few parentheticals, becomes a comma when spaced and a
hyphen when not, because nothing that leaves this site carries one. Everything
else is the upstream's text.

## License

The dictionary is CC BY-SA 3.0. Anything that re-publishes its definitions
(the lookup answers, this snapshot) carries that license and the attribution
above; the frequency list itself stays CC BY and is never merged with it.
`;
fs.writeFileSync(SOURCE_MD, md);
console.log(`dmk-dictionary.json: ${entries.length} entries covering ${coveredRanks.size} of ${list.n} lemmas (upstream ${words.length}, sha256 ${sha256.slice(0, 12)})`);
