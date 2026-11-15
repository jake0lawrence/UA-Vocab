// ============================================================
// UKRAINIAN FREQUENCY : thread 07, word stress (pure builder)
//
// Turns the committed, reviewed stress snapshot (src/data/ukrainian-frequency/
// stress.json) into the versioned, hashed open-data overlay at
// public/downloads/ukrainian-frequency/stress/<version>/, keyed on the v0.2.0
// list's ranks. Every manual decision lives in stress-overrides.json and is
// applied LAST here, so a rebuilt pipeline reproduces it and a row backed by a
// goroh.pp.ua lookup cannot change without an entry in that file (a test holds
// this).
//
// Why an overlay and not a column on lemmas.csv: the Wiktionary-derived rows
// make the stress data CC-BY-SA, while the list itself is CC-BY. A share-alike
// column folded into the list file would relicense the list (and its Zenodo
// deposit). Keeping stress as its own file, joined on rank, keeps each dataset
// under its own terms, the posture every other overlay here already takes.
//
// Pure: inputs are passed in, nothing is read from disk. Imported by the build
// script and the drift-guard test, never by the client page (the page reads the
// generated stress.data.mjs through stress-view.mjs). House rule: no em-dashes.
// ============================================================

export const STRESS_VERSION = "v1.0.2";
export const STRESS_DATASET = "ukrainian-frequency-stress";
export const STRESS_LICENSE = "CC-BY-SA-4.0";
export const STRESS_LIST = "v0.2.0";

export const ACUTE = "\u0301";
export const GRAVE = "\u0300";

// The status taxonomy, in the order the page and the README list it. The
// `tier` is the confidence reading: `one` means a single stress the row is
// confident about, `labeled` means more than one valid or possible stress and
// the row says so, `trivial` is a monosyllable, `missing` is unresolved.
export const STATUSES = {
  dictionary: { tier: "one", about: "the ukrainian-word-stress dictionary (lang-uk), one reading for this lemma, reproducible from the trie alone" },
  dictionary_pos: { tier: "one", about: "the dictionary lists several readings; filtered to one by the list's own UD part of speech and lemma features" },
  library_context: { tier: "one", about: "the dictionary is ambiguous for this part of speech and the library's context model chose; not reproducible from the trie alone" },
  wiktionary: { tier: "one", about: "a dictionary doublet resolved by en.wiktionary (the other stress is a minor, dated or dialectal variant)" },
  wiktionary_filled: { tier: "one", about: "absent from the dictionary, filled from en.wiktionary" },
  adjudicated: { tier: "one", about: "sources disagreed and a two-of-three vote, a rule or a goroh.pp.ua tiebreak decided; see source" },
  compound: { tier: "one", about: "a hyphenated compound the library stressed as a whole; the main stress is kept, any secondary stress is in the note" },
  compound_rule: { tier: "one", about: "a hyphenated or stump compound: stress on the last component" },
  compound_main_stress: { tier: "one", about: "the dictionary listed the main and the secondary stress as alternatives; the main (last component) is kept, the secondary is in the note" },
  abbreviation_rule: { tier: "one", about: "an acronym read letter by letter: final syllable" },
  spelling_variant: { tier: "one", about: "looked up under the standard spelling (the list's spelling is nonstandard); the standard spelling is in the note" },
  surname_enko_rule: { tier: "one", about: "a surname in -енко, stressed on -е́нко" },
  wikipedia_lead: { tier: "one", about: "a proper noun stressed from the uk.wikipedia lead sentence; the article title is in source" },
  free_variant: { tier: "labeled", about: "both stresses are accepted (та́кож / тако́ж); the primary is listed first" },
  homograph: { tier: "labeled", about: "different words with different stress (о́рган body / орга́н instrument) whose forms are spelled alike in every cell, so the corpus cannot tell them apart; the primary is the first en.wiktionary entry, not corpus-verified" },
  homograph_corpus: { tier: "labeled", about: "different words with different stress whose paradigms differ in spelling somewhere (прохо́дити / проходи́ти); the primary is the reading whose distinguishing forms occur more in UberText 2.0, with the counts in source" },
  doublet_dictionary_only: { tier: "labeled", about: "the dictionary lists two stresses and no other source covers the word; the primary is the first listed" },
  name_variable: { tier: "labeled", about: "a surname or place whose stress varies by bearer (Мака́ренко / Макаре́нко)" },
  wiktionary_filled_variant: { tier: "labeled", about: "absent from the dictionary, filled from en.wiktionary, which gives more than one stress" },
  wikipedia_lead_variants: { tier: "labeled", about: "a proper noun whose uk.wikipedia leads stress it two ways" },
  monosyllabic: { tier: "trivial", about: "one syllable; no mark needed" },
  missing: { tier: "missing", about: "no source resolved it" },
  proper_noun: { tier: "scope", about: "a proper noun: out of scope by owner decision (2026-10-01), as most learner lists leave names out; the stress the pipeline found is kept for reference and the pipeline's own status is in the note, but the row is not counted" },
};
export const TIERS = ["one", "labeled", "trivial", "missing", "scope"];

// The provenance families the page counts, by status. `goroh` is counted
// separately off the source string, because the handful of goroh-backed rows
// is the one place a lookup against a non-open reference enters the data.
export const PROVENANCE = {
  library: ["dictionary", "dictionary_pos", "library_context", "compound", "doublet_dictionary_only"],
  wiktionary: ["wiktionary", "wiktionary_filled", "wiktionary_filled_variant", "homograph", "free_variant"],
  adjudicated: ["adjudicated", "name_variable"],
  rule: ["compound_rule", "compound_main_stress", "abbreviation_rule", "spelling_variant", "surname_enko_rule", "monosyllabic"],
  wikipedia: ["wikipedia_lead", "wikipedia_lead_variants"],
  corpus: ["homograph_corpus"],
  missing: ["missing"],
  scope: ["proper_noun"],
};

export const CSV_COLUMNS = ["rank", "lemma", "pos", "stress", "stress_variants", "stress_status", "note", "source"];
export const FILES = ["stress.csv", "stress.json", "stress.anki.tsv", "adjudication.csv", "paradigm-disagreements.csv", "doublets.csv", "README.md"];

// A source that is not an open license may only enter a row through the
// manual ledger: the goroh.pp.ua tiebreaks and the printed orthoepic
// dictionary (Pohribnyi) the dictionary-only doublets are being settled from.
export const LEDGERED_SOURCES = /goroh|Погрібний|Pohribnyi/i;

const VOWELS = /[аеєиіїоуюяАЕЄИІЇОУЮЯ]/g;

export function stripAccents(s) {
  return String(s).replace(new RegExp(ACUTE, "g"), "").replace(new RegExp(GRAVE, "g"), "");
}

// Index of every acute mark, counted on the string with the marks removed.
export function accentPositions(s) {
  const out = [];
  let i = 0;
  for (const c of String(s)) {
    if (c === ACUTE) out.push(i);
    else if (c !== GRAVE) i += 1;
  }
  return out;
}

// Every acute sits on a vowel. A mark after a consonant (Н́іколас, a typo a
// Wikipedia lead can carry) is not a stress and is refused.
export function marksFollowVowels(s) {
  const str = String(s);
  for (let i = 0; i < str.length; i += 1) {
    if (str[i] === ACUTE && !/[аеєиіїоуюяАЕЄИІЇОУЮЯ]/.test(str[i - 1] || "")) return false;
  }
  return true;
}

export function syllables(s) {
  const m = stripAccents(s).match(VOWELS);
  return m ? m.length : 0;
}

// One apostrophe glyph, for comparisons across sources.
export function foldApostrophe(s) {
  return String(s).replace(/[\u02bc'`]/g, "\u2019");
}

// Apply the manual decisions last. Throws when an override names a row the
// snapshot does not have at that rank (a rebuilt list would need new ranks).
export function applyOverrides(rows, overrides) {
  const byRank = new Map(rows.map((r) => [r.rank, r]));
  const out = rows.map((r) => ({ ...r, variants: [...r.variants] }));
  for (const o of overrides) {
    const r = byRank.get(o.rank);
    if (!r) throw new Error(`override rank ${o.rank} (${o.lemma}) is not on the list`);
    if (r.lemma !== o.lemma || r.pos !== o.pos) throw new Error(`override rank ${o.rank}: ${o.lemma}/${o.pos} but the list has ${r.lemma}/${r.pos}`);
    const t = out[o.rank - 1];
    t.stress = o.stress;
    t.variants = o.variants.length ? (o.variants[0] === o.stress ? [...o.variants] : [o.stress, ...o.variants.filter((v) => v !== o.stress)]) : [];
    t.status = o.status;
    t.source = o.evidence;
    t.overridden = true;
  }
  return out;
}

// The homograph corpus count (stress-homographs.json, owner decision
// 2026-10-01): where a homograph's two readings differ in spelling somewhere
// in the paradigm, the reading whose distinguishing forms occur more across
// the UberText 2.0 subcorpora becomes the primary, the counts go on the row
// and the status becomes `homograph_corpus`. A pair the count could not decide
// stays `homograph` and its note says why. Applied before the overrides, so a
// manual decision still wins.
export function applyHomographCounts(rows, homographs) {
  if (!homographs || !homographs.results) return rows;
  const byRank = homographs.results; // keyed by rank: пора is on the list twice
  return rows.map((r) => {
    if (r.status !== "homograph") return r;
    const h = byRank[String(r.rank)];
    if (!h || h.rank !== r.rank || h.lemma !== r.lemma) return r;
    const why = h.decision.why;
    if (!h.decision.primary) {
      return { ...r, note: r.note ? `${r.note} ; primary unverified: ${why}` : `primary unverified: ${why}` };
    }
    const primary = h.decision.primary;
    const accepted = new Set([r.stress, ...r.variants]);
    if (!accepted.has(primary)) throw new Error(`homograph count for ${r.lemma} names ${primary}, not one of the row's readings`);
    const ranked = [...h.readings].sort((a, b) => b.hits - a.hits);
    return {
      ...r,
      stress: primary,
      variants: [primary, ...[...accepted].filter((v) => v !== primary)],
      status: "homograph_corpus",
      source: `UberText 2.0: ${ranked.map((x) => `${x.stress} ${x.hits.toLocaleString("en-US")}`).join(" vs ")} (forms that differ in spelling)`,
    };
  });
}

// The ledger is applied after the count, so a manual decision always wins
// where it disagrees. Where it agrees (goroh picked зво́дити before the corpus
// could be asked, and the corpus says the same) the manual row must not erase
// the open evidence: the counted status and the counts stay on the row and the
// ledger's evidence rides along in source, so both are auditable.
export function keepCountsTheLedgerConfirms(counted, overridden, overrides) {
  const byRank = new Map(counted.map((r) => [r.rank, r]));
  return overridden.map((r) => {
    if (!r.overridden) return r;
    const c = byRank.get(r.rank);
    if (!c || c.status !== "homograph_corpus" || r.status !== "homograph" || r.stress !== c.stress) return r;
    const o = overrides.find((x) => x.rank === r.rank);
    return { ...r, status: "homograph_corpus", variants: [...c.variants], source: `${c.source}; ledger: ${o ? o.evidence : r.source}` };
  });
}

// Proper nouns are out of scope (owner decision, 2026-10-01). The pipeline's
// stress is kept on the row for anyone who wants it, its own status moves to
// the note, and the status becomes `proper_noun`, which no headline figure
// counts. Applied after the overrides and the row validation, so a name's
// stress is still held to the same invariants as every other row.
export function scopeProperNouns(rows) {
  return rows.map((r) => {
    if (r.pos !== "PROPN") return r;
    const pipeline = `pipeline: ${r.status}`;
    return { ...r, status: "proper_noun", note: r.note ? `out of scope; ${pipeline}; ${r.note}` : `out of scope; ${pipeline}` };
  });
}

// Every invariant a published row owes. Returns a list of problems; empty
// means the rows are publishable.
export function validateRows(rows, seed, overrides = []) {
  const problems = [];
  const seedRows = seed.rows;
  if (rows.length !== seedRows.length) problems.push(`row count ${rows.length} vs list ${seedRows.length}`);
  const overriddenRanks = new Set(overrides.map((o) => o.rank));
  rows.forEach((r, i) => {
    const s = seedRows[i];
    if (r.rank !== i + 1) problems.push(`rank ${r.rank} at index ${i}`);
    if (s && (r.lemma !== s.lemma || r.pos !== s.pos)) problems.push(`rank ${r.rank}: ${r.lemma}/${r.pos} is not the list's ${s.lemma}/${s.pos}`);
    if (!STATUSES[r.status]) problems.push(`rank ${r.rank}: unknown status ${r.status}`);
    const tier = STATUSES[r.status]?.tier;
    if (r.stress.normalize("NFC") !== r.stress) problems.push(`rank ${r.rank}: stress not NFC`);
    if (r.stress.includes(ACUTE + ACUTE)) problems.push(`rank ${r.rank}: doubled acute`);
    if (r.stress.includes(GRAVE)) problems.push(`rank ${r.rank}: grave accent in the primary form`);
    if (tier === "scope") {
      // a scoped name keeps whatever the pipeline found; only its shape is held
      if (r.stress && stripAccents(r.stress) !== r.lemma && !/standard spelling/.test(r.note)) problems.push(`rank ${r.rank}: ${r.stress} does not strip to ${r.lemma}`);
      if (r.stress && !marksFollowVowels(r.stress)) problems.push(`rank ${r.rank}: a mark in ${r.stress} does not follow a vowel`);
    } else if (tier === "missing") {
      if (r.stress !== "") problems.push(`rank ${r.rank}: missing but carries a form`);
    } else if (tier === "trivial") {
      if (r.stress !== r.lemma) problems.push(`rank ${r.rank}: monosyllable must be the bare lemma`);
      if (syllables(r.lemma) > 1) problems.push(`rank ${r.rank}: tagged monosyllabic with ${syllables(r.lemma)} vowels`);
    } else {
      const base = stripAccents(r.stress);
      const expected = r.status === "spelling_variant" ? (r.note.match(/standard spelling (\S+)/) || [])[1] : r.lemma;
      if (base !== expected) problems.push(`rank ${r.rank}: ${r.stress} does not strip to ${expected}`);
      const n = accentPositions(r.stress).length;
      if (n < 1) problems.push(`rank ${r.rank}: no stress mark on a polysyllable`);
      for (const v of [r.stress, ...r.variants]) if (!marksFollowVowels(v)) problems.push(`rank ${r.rank}: a mark in ${v} does not follow a vowel`);
      if (n > 1 && !r.lemma.includes("-")) problems.push(`rank ${r.rank}: ${n} marks on a hyphenless lemma`);
      if (tier === "labeled" && r.variants.length < 2) problems.push(`rank ${r.rank}: ${r.status} with fewer than two variants`);
    }
    if (r.variants.length && r.variants[0] !== r.stress) problems.push(`rank ${r.rank}: the primary stress is not the first variant`);
    for (const v of r.variants) if (stripAccents(v) !== stripAccents(r.stress) && r.status !== "spelling_variant") problems.push(`rank ${r.rank}: variant ${v} is a different word`);
    if (new Set(r.variants).size !== r.variants.length) problems.push(`rank ${r.rank}: duplicate variant`);
    if (LEDGERED_SOURCES.test(r.source) && !overriddenRanks.has(r.rank)) problems.push(`rank ${r.rank}: cites a ledgered source (goroh / Pohribnyi) without an override entry`);
    for (const f of ["note", "source"]) if (new RegExp("[\\u2014\\u2015\\u2012]").test(r[f])) problems.push(`rank ${r.rank}: em-dash in ${f}`);
  });
  return problems;
}

// The headword form per rank out of the thread-04 paradigms file, so the two
// datasets can be read against each other. Only the headword row counts
// (nominative singular, infinitive); a form whose base is not the lemma is
// skipped, so a declined form never stands in for the headword.
const HEADWORD_TAGS = new Set(["nominative singular", "nominative", "masculine nominative singular", "infinitive", "imperfective infinitive", "infinitive perfective", "perfective infinitive"]);
export function paradigmHeadwords(formsCsv) {
  const out = new Map();
  const lines = formsCsv.split("\n");
  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line) continue;
    const cells = line.split(",");
    if (cells.length < 6) continue;
    const [rank, lemma, , form, tags, inflectional] = cells;
    const r = Number(rank);
    if (out.has(r) || inflectional !== "1" || !HEADWORD_TAGS.has(tags)) continue;
    if (foldApostrophe(stripAccents(form)).toLowerCase() !== foldApostrophe(lemma).toLowerCase()) continue;
    out.set(r, form);
  }
  return out;
}

// Where the adjudicated stress and the verbatim Wiktionary headword disagree.
// A row is listed when the paradigm headword's stress is not among the stresses
// this column accepts for the word (the primary or a labeled variant), compared
// only where the headword carries exactly one acute (a secondary grave is
// dropped) and the lemma has no hyphen, so a compound's two marks or a
// two-stress Wiktionary form (Ма́нче́стер) is not read as a conflict. A row the
// goroh-backed corrections ledger covers is always listed and reads
// `stress_column` (the paradigm headword is the one to fix: музи́ка is the
// musician, the list's word is the music); the rest read `open`: neither side
// has been adjudicated, and the row is a review queue, not a verdict.
export function paradigmDisagreements(rows, headwords, corrections = []) {
  const byRank = new Map(corrections.map((c) => [c.rank, c]));
  const out = [];
  for (const r of rows) {
    const h = headwords.get(r.rank);
    if (!h || !r.stress || r.lemma.includes("-") || r.status === "spelling_variant") continue;
    const headword = h.replace(new RegExp(GRAVE, "g"), "");
    const c = byRank.get(r.rank);
    const hp = accentPositions(headword);
    const accepted = new Set([r.stress, ...r.variants].map((v) => accentPositions(v).join("+")));
    const conflict = hp.length === 1 && !accepted.has(String(hp[0]));
    if (!conflict && !c) continue;
    out.push({
      rank: r.rank,
      lemma: r.lemma,
      pos: r.pos,
      stressColumn: r.stress,
      paradigmsFile: headword,
      verdict: c ? "stress_column" : "open",
      evidence: c ? c.evidence : "",
    });
  }
  return out;
}

function csvCell(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function toCsv(cols, rows) {
  const lines = [cols.join(",")];
  for (const row of rows) lines.push(cols.map((c) => csvCell(row[c])).join(","));
  return lines.join("\n") + "\n";
}
const pct1 = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : 0);

export function stressCsv(rows) {
  return toCsv(
    CSV_COLUMNS,
    rows.map((r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, stress: r.stress, stress_variants: r.variants.join("|"), stress_status: r.status, note: r.note, source: r.source })),
  );
}

// Build the overlay from its committed inputs. Deterministic, network-free.
export function buildStress({ snapshot, overrides, adjudication, seed, homographs = null, paradigmForms = "", citation = "" }) {
  const counted = applyHomographCounts(snapshot.rows, homographs);
  const resolved = keepCountsTheLedgerConfirms(counted, applyOverrides(counted, overrides.rows), overrides.rows);
  const problems = validateRows(resolved, seed, overrides.rows);
  if (problems.length) throw new Error(`stress rows are not publishable:\n${problems.slice(0, 20).join("\n")}`);
  const rows = scopeProperNouns(resolved);

  const byStatus = {};
  for (const k of Object.keys(STATUSES)) byStatus[k] = 0;
  for (const r of rows) byStatus[r.status] += 1;

  const tiers = { one: 0, labeled: 0, trivial: 0, missing: 0, scope: 0 };
  for (const r of rows) tiers[STATUSES[r.status].tier] += 1;
  // the denominator every share is read against: in scope and needing a mark
  const polysyllabic = rows.length - tiers.trivial - tiers.scope;

  const provenance = {};
  for (const [fam, statuses] of Object.entries(PROVENANCE)) provenance[fam] = statuses.reduce((a, s) => a + byStatus[s], 0);
  const goroh = rows.filter((r) => /goroh/i.test(r.source)).length;

  const byBand = [];
  for (let b = 1; b <= Math.ceil(rows.length / 1000); b += 1) {
    const slice = rows.filter((r) => Math.ceil(r.rank / 1000) === b);
    const missing = slice.filter((r) => r.status === "missing").length;
    const labeled = slice.filter((r) => STATUSES[r.status].tier === "labeled").length;
    const scoped = slice.filter((r) => STATUSES[r.status].tier === "scope").length;
    const inScope = slice.length - scoped;
    byBand.push({ band: b, lemmas: slice.length, inScope, scoped, resolved: inScope - missing, labeled, missing, resolvedPct: pct1(inScope - missing, inScope) });
  }

  const missingByPos = {};
  for (const r of rows) if (r.status === "missing") missingByPos[r.pos] = (missingByPos[r.pos] || 0) + 1;

  const headwords = paradigmForms ? paradigmHeadwords(paradigmForms) : new Map();
  // read against the in-scope rows: a name's paradigm is not this column's claim
  const disagreements = paradigmDisagreements(rows.filter((r) => r.status !== "proper_noun"), headwords, adjudication.paradigmCorrections || []);
  // the dictionary-only doublets still open, in scope, for the printed-source pass
  const doublets = rows.filter((r) => r.status === "doublet_dictionary_only");

  const stats = {
    lemmas: rows.length,
    polysyllabic,
    monosyllabic: tiers.trivial,
    tiers,
    onePct: pct1(tiers.one, polysyllabic),
    oneOrLabeledPct: pct1(tiers.one + tiers.labeled, polysyllabic),
    missingPct: pct1(tiers.missing, polysyllabic),
    byStatus,
    provenance,
    goroh,
    overrides: overrides.rows.length,
    byBand,
    missingByPos,
    adjudicated: adjudication.log.length,
    homographsCounted: byStatus.homograph_corpus,
    homographsFlipped: homographs && homographs.summary ? homographs.summary.flipped : 0,
    properNouns: tiers.scope,
    doubletsOpen: doublets.length,
    paradigmDisagreements: disagreements.length,
    paradigmCorrections: disagreements.filter((d) => d.verdict === "stress_column").length,
    paradigmsCompared: headwords.size,
  };

  const bodies = {
    "stress.csv": stressCsv(rows),
    "stress.json":
      JSON.stringify({
        version: STRESS_VERSION,
        dataset: STRESS_DATASET,
        license: STRESS_LICENSE,
        list: STRESS_LIST,
        snapshot: snapshot.snapshot,
        citation,
        columns: CSV_COLUMNS,
        statuses: Object.fromEntries(Object.entries(STATUSES).map(([k, v]) => [k, v.about])),
        counts: { lemmas: stats.lemmas, polysyllabic, tiers, byStatus, goroh },
        rows: rows.map((r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, stress: r.stress, variants: r.variants, status: r.status, note: r.note, source: r.source })),
      }) + "\n",
    "stress.anki.tsv": rows.map((r) => `${r.stress || r.lemma}\t${r.pos}\t${r.rank}\t${r.variants.join("|")}\t${r.status}`).join("\n") + "\n",
    "adjudication.csv": toCsv(["rank", "lemma", "pos", "decision", "chosen", "votes", "note"], adjudication.log),
    "paradigm-disagreements.csv": toCsv(["rank", "lemma", "pos", "stress_column", "paradigms_file", "verdict", "evidence"], disagreements.map((d) => ({ rank: d.rank, lemma: d.lemma, pos: d.pos, stress_column: d.stressColumn, paradigms_file: d.paradigmsFile, verdict: d.verdict, evidence: d.evidence }))),
    "doublets.csv": toCsv(["rank", "lemma", "pos", "variants", "settle_by"], doublets.map((r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, variants: r.variants.join("|"), settle_by: "Pohribnyi, Orfoepichnyi slovnyk (printed); enter the attested stress as an override with the page" }))),
  };

  return { rows, stats, bodies, disagreements, doublets };
}
