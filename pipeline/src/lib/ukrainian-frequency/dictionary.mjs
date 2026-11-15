// ============================================================
// UKRAINIAN FREQUENCY : the word lookup and the dictionary's third reading.
//
// Pure. Two jobs over the committed dmklinger/ukrainian snapshot
// (src/data/ukrainian-frequency/dmk-dictionary.json, CC BY-SA 3.0):
//
//   1. The stress column's third reading. The dictionary carries a stressed
//      headword for most list lemmas. It is not independent evidence (it reads
//      the same Wiktionary the column's second stage reads), so it is scored,
//      not voted: agree, agree with the dictionary listing both marks, or
//      disagree, with every disagreement kept as a row. `buildDictionaryStats`
//      re-derives those counts; the build script freezes them and CI holds the
//      frozen figure to the recomputation.
//
//   2. The lookup. `buildLookupIndex` joins the tiers a reader wants in one
//      answer (rank, validated level, course gloss, stress, open audio, the
//      dictionary's definitions and gender) and `lookup` answers a typed or
//      dictated word, inflected forms included, through the profiler's own
//      form index. `formatText` is the plain-text shape a watch can show.
//
// No fs, no network, no React. House rule: no em dashes.
// ============================================================

import { normalizeToken } from "./profiler/tokenize.mjs";

export const ACUTE = "́";
export const DICTIONARY_LICENSE = "CC BY-SA 3.0";

const n = (x) => x.toLocaleString("en-US");

export function stripMarks(s) {
  return String(s || "").normalize("NFC").split(ACUTE).join("");
}

/**
 * The single-acute readings a headword stands for. Wiktionary writes a word
 * stressed either way with a mark on each vowel (та́ко́ж); the column keeps one
 * mark per form, so a two-mark headword is read as two readings.
 */
export function readings(head) {
  const s = String(head || "").normalize("NFC");
  // A hyphenated compound carries one mark per part (бі́льш-ме́нш): one reading.
  if (s.includes("-")) return [s];
  const chars = [...s];
  const marks = chars.map((c, i) => (c === ACUTE ? i : -1)).filter((i) => i >= 0);
  if (marks.length <= 1) return [s];
  return marks.map((keep) => chars.filter((c, i) => c !== ACUTE || i === keep).join(""));
}

/**
 * Compare one stress-column row against the dictionary's headwords for the
 * same lemma. `monosyllabic`: the column carries no mark (nothing to compare).
 * `unmarked`: the dictionary's headwords carry none (nothing to compare
 * either; the dictionary is silent, not dissenting). `agree`: the column's
 * primary stress is one of the dictionary's readings. `agree_variant`: a
 * column variant other than the primary is. `disagree`: none of the column's
 * forms appears among the dictionary's readings.
 */
export function compareRow(row, heads) {
  if (!row.stress || !row.stress.includes(ACUTE)) return "monosyllabic";
  if (!heads.some((h) => String(h).includes(ACUTE))) return "unmarked";
  if (row.lemma.includes("-")) return compareHyphenated(row, heads);
  const theirs = new Set(heads.flatMap(readings).map(stressKey));
  if (theirs.has(stressKey(row.stress))) return "agree";
  if ((row.variants || []).some((v) => theirs.has(stressKey(v)))) return "agree_variant";
  return "disagree";
}

/**
 * A hyphenated compound is compared part by part. The dictionary marks every
 * part (іва́но-франкі́вський); the column marks either every part or the main
 * stress alone (Івано-Франкі́вський, status compound_main_stress), so a form
 * agrees when each part it does mark carries the dictionary's mark for that
 * part. A part the column leaves unmarked is silence, not dissent.
 */
export function compareHyphenated(row, heads) {
  const partsAgree = (ours, theirs) => {
    const a = stressKey(ours).split("-");
    const b = stressKey(theirs).split("-");
    if (a.length !== b.length) return false;
    return a.every((part, i) => !part.includes(ACUTE) || part === b[i]);
  };
  if (heads.some((h) => partsAgree(row.stress, h))) return "agree";
  if ((row.variants || []).some((v) => heads.some((h) => partsAgree(v, h)))) return "agree_variant";
  return "disagree";
}

/**
 * A stressed form as a comparison key: the mark stays, but the apostrophe
 * glyph (the dictionary writes U+0027, the list U+2019) and the case (the
 * list capitalizes proper nouns, the dictionary does not) are folded, so
 * only the place of the stress can make two forms differ.
 */
export function stressKey(s) {
  return String(s || "").normalize("NFC").replace(/['ʼ`]/g, "’").toLowerCase();
}

/** Headwords per list rank from the snapshot's entries. */
export function headsByRank(snapshot) {
  const out = new Map();
  for (const e of snapshot.entries) {
    for (const r of e.ranks) {
      if (!out.has(r)) out.set(r, []);
      out.get(r).push(e);
    }
  }
  return out;
}

/**
 * The third reading: how the dictionary's stressed headwords score against
 * the column, over the polysyllabic rows the dictionary covers.
 */
export function buildDictionaryStats(snapshot, stressRows) {
  const by = headsByRank(snapshot);
  const stats = { lemmas: stressRows.length, covered: 0, missing: 0, compared: 0, agree: 0, agreeVariant: 0, disagree: 0, monosyllabic: 0, unmarked: 0, eitherStress: 0 };
  const byStatus = {};
  const disagreements = [];
  for (const row of stressRows) {
    const entries = by.get(row.rank);
    if (!entries) {
      stats.missing += 1;
      continue;
    }
    stats.covered += 1;
    const heads = entries.map((e) => e.word);
    if (heads.some((h) => [...h].filter((c) => c === ACUTE).length > 1)) stats.eitherStress += 1;
    const verdict = compareRow(row, heads);
    if (verdict === "monosyllabic" || verdict === "unmarked") {
      stats[verdict] += 1;
      continue;
    }
    stats.compared += 1;
    if (verdict === "agree") stats.agree += 1;
    else if (verdict === "agree_variant") stats.agreeVariant += 1;
    else {
      stats.disagree += 1;
      byStatus[row.status] = (byStatus[row.status] || 0) + 1;
      disagreements.push({
        rank: row.rank,
        lemma: row.lemma,
        pos: row.pos,
        status: row.status,
        ours: row.stress,
        variants: row.variants || [],
        theirs: [...new Set(heads.map((h) => h.normalize("NFC")))],
      });
    }
  }
  disagreements.sort((a, b) => a.rank - b.rank);
  const pct = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : 0);
  return {
    ...stats,
    coveredPct: pct(stats.covered, stats.lemmas),
    agreePct: pct(stats.agree + stats.agreeVariant, stats.compared),
    disagreeByStatus: byStatus,
    disagreements,
  };
}

/** The list lemmas the dictionary has no entry for, in rank order. */
export function dictionaryGaps(snapshot, stressRows, levelOf = () => null) {
  const by = headsByRank(snapshot);
  return stressRows
    .filter((r) => !by.has(r.rank))
    .map((r) => ({ rank: r.rank, lemma: r.lemma, pos: r.pos, level: levelOf(r.rank) }));
}

// ---------- the lookup ----------

/**
 * Join the tiers into one index.
 *   stressRows: the stress release rows (rank, lemma, pos, stress, variants, status)
 *   forms:      the profiler's forms.json map (surface form -> 0-based lemma index or indices)
 *   course:     Map rank -> { level, gloss, ppm } from the Learn Ukrainian tier (validated lemmas only)
 *   audio:      Map rank -> Wikimedia Commons URL (thread 04)
 *   snapshot:   the dmk snapshot
 */
export function buildLookupIndex({ stressRows, forms, course, audio, snapshot }) {
  const entries = new Map();
  const lemmaIdx = new Map();
  const dict = headsByRank(snapshot);
  for (const r of stressRows) {
    const c = course.get(r.rank) || null;
    entries.set(r.rank, {
      rank: r.rank,
      lemma: r.lemma,
      pos: r.pos,
      level: c ? c.level : null,
      gloss: c ? c.gloss : null,
      ppm: c ? c.ppm : null,
      stress: { form: r.stress, variants: r.variants || [], status: r.status },
      audio: audio.get(r.rank) || null,
      // The entry whose headword carries the column's primary stress reads
      // first (за́мок the castle before замо́к the lock when the column says
      // за́мок); the rest keep the snapshot's order.
      dictionary: (dict.get(r.rank) || [])
        .map((e, i) => ({ head: e.word, pos: e.pos, info: e.info, defs: e.defs, i, hit: readings(e.word).map(stressKey).includes(stressKey(r.stress)) ? 0 : 1 }))
        .sort((a, b) => a.hit - b.hit || a.i - b.i)
        .map(({ i, hit, ...e }) => e),
    });
    const key = normalizeToken(r.lemma);
    if (!lemmaIdx.has(key)) lemmaIdx.set(key, []);
    lemmaIdx.get(key).push(r.rank);
  }
  const formIdx = new Map();
  for (const [f, v] of Object.entries(forms || {})) {
    const idx = Array.isArray(v) ? v : [v];
    formIdx.set(f, idx.map((i) => i + 1));
  }
  return { entries, lemmaIdx, formIdx, size: entries.size };
}

/**
 * Answer one word. The key is the profiler's own normalization (NFC, stress
 * stripped, apostrophe folded, lowercased), so a dictated or stressed form
 * and the list's spelling meet in the middle. A lemma match wins; otherwise
 * the form index; the answer carries which.
 */
export function lookup(index, raw) {
  const query = String(raw || "").trim();
  const key = normalizeToken(query);
  if (!key) return { query, key, via: null, entries: [] };
  let ranks = index.lemmaIdx.get(key);
  let via = "lemma";
  if (!ranks || !ranks.length) {
    ranks = index.formIdx.get(key) || [];
    via = ranks.length ? "form" : null;
  }
  const seen = new Set();
  const entries = [];
  for (const r of ranks) {
    if (seen.has(r)) continue;
    seen.add(r);
    const e = index.entries.get(r);
    if (e) entries.push(e);
  }
  entries.sort((a, b) => a.rank - b.rank);
  return { query, key, via: entries.length ? via : null, entries };
}

export const POS_LABEL = {
  NOUN: "noun", VERB: "verb", ADJ: "adjective", ADV: "adverb", PRON: "pronoun", DET: "determiner",
  ADP: "preposition", CCONJ: "conjunction", SCONJ: "conjunction", PART: "particle", NUM: "numeral",
  INTJ: "interjection", PROPN: "proper noun", AUX: "auxiliary", X: "other", SYM: "symbol",
};

const DEF_CAP = 3;
const DEF_CHARS = 120;

function trimDef(d) {
  const s = String(d).replace(/\s+/g, " ").trim();
  return s.length > DEF_CHARS ? s.slice(0, DEF_CHARS - 1).replace(/\s+\S*$/, "") + "…" : s;
}

/**
 * The plain-text answer: one block per entry, the stressed form first, then
 * what a reader needs to keep reading. Built for a watch face, so three
 * definitions at most and nothing a screen reader would stumble over.
 */
export function formatText(result) {
  if (!result.entries.length) return `Not in the 12,000-word list: ${result.query}`;
  return result.entries
    .map((e) => {
      const head = e.stress.form || e.lemma;
      const meta = [POS_LABEL[e.pos] || e.pos.toLowerCase(), e.level, `rank ${n(e.rank)}`].filter(Boolean).join(" · ");
      const lines = [`${head}  ${meta}`];
      if (e.stress.variants.length > 1) lines.push(`also ${e.stress.variants.filter((v) => v !== e.stress.form).join(", ")}`);
      const defs = e.dictionary.flatMap((d) => d.defs).slice(0, DEF_CAP).map(trimDef);
      if (defs.length) lines.push(defs.join("; "));
      else if (e.gloss) lines.push(e.gloss);
      const info = e.dictionary.map((d) => d.info).filter(Boolean)[0];
      if (info) lines.push(info);
      return lines.join("\n");
    })
    .join("\n\n");
}

/** The share of list lemmas with a dictionary entry, for a sentence. */
export function coverageSentence(stats) {
  return `${n(stats.covered)} of ${n(stats.lemmas)} list lemmas have an entry (${stats.coveredPct} percent); of the ${n(stats.compared)} polysyllabic ones the dictionary stresses, ${n(stats.agree + stats.agreeVariant)} agree with the column (${stats.agreePct} percent) and ${n(stats.disagree)} do not.`;
}
