// ============================================================
// UKRAINIAN FREQUENCY : thread 07, word stress: the accuracy audit (pure)
//
// The column says 97.5 percent of the in-scope polysyllables carry one
// confident stress. "Confident" is a statement about the sources agreeing,
// not about a native speaker agreeing. This module is the pre-registered
// design that turns it into a measured accuracy: a seeded, stratified random
// sample of rows is drawn once and committed (build-stress-audit.mjs), each
// row becomes a priced task on the Validation Desk (kind stress.verdict), and
// the accepted verdicts come back as a committed overlay. The summary below
// re-derives the accuracy with a Wilson interval from sample + overlay, in the
// browser and in CI, so the number on the page is never typed.
//
// Pre-registered criterion (owner, 2026-10-02): the confident tier counts as
// validated when at least MIN_REVIEWED of its sampled rows are reviewed and
// the lower bound of the 95 percent Wilson interval of rows judged not wrong
// (correct, or both stresses in real use) is at least TARGET. A `wrong`
// verdict is a flag for the override ledger, never an automatic correction:
// a reviewer's word is evidence, a printed source settles it.
//
// Amendment 1 (owner, 2026-11-13, before any answer existed): every sampled
// row goes to a PANEL of three reviewers, not one, so one speaker's ear is not
// the whole measurement. The unit of the criterion stays the ROW (three
// answers about one word are not three independent observations): a row is
// judged once at least two of its reviewers gave a judged answer, and a judged
// row is not wrong only when its not-wrong answers outnumber its wrong ones (a
// tie counts as wrong, the reading that makes the target harder to reach).
// Sample, seed, target and floor are unchanged. docs/ukrainian-frequency/
// stress-audit.md, "Amendment 1".
//
// Deterministic: a seed string, a fixed PRNG, rows sorted by rank before the
// shuffle. No clock, no network. House rule: no em-dashes.
// ============================================================

import { STATUSES } from "./stress.mjs";

export const AUDIT_VERSION = "v1";
export const TARGET = 0.95;
export const MIN_REVIEWED = 150;
export const Z95 = 1.959964;
// Amendment 1: reviewers per row, and how many judged answers judge a row.
export const AMENDMENT = 1;
export const PANEL = 3;
export const MIN_JUDGED_ANSWERS = 2;

// The strata, each a predicate over built rows and a draw size (null = census).
// Proper nouns are out of scope and monosyllables need no mark, so neither is
// ever drawn; a missing row has nothing to judge.
export const STRATA = [
  {
    id: "confident",
    label: "one confident stress",
    about: "the headline claim: the sources agreed on one stress",
    size: 200,
    pick: (r) => STATUSES[r.status]?.tier === "one",
  },
  {
    id: "labeled",
    label: "labeled variant or doublet",
    about: "a free variant or a dictionary-only doublet; the primary is the first listed",
    size: 60,
    pick: (r) => ["free_variant", "doublet_dictionary_only", "wiktionary_filled_variant"].includes(r.status),
  },
  {
    id: "homograph_corpus",
    label: "homograph, primary from the corpus count",
    about: "every pair the UberText count decided; the reviewer checks the count's pick",
    size: null,
    pick: (r) => r.status === "homograph_corpus",
  },
  {
    id: "homograph",
    label: "homograph, primary unverified",
    about: "every pair the count could not settle; the reviewer says which reading a learner meets first",
    size: null,
    pick: (r) => r.status === "homograph",
  },
];

// A small, fixed PRNG: xmur3 hashes the seed string, mulberry32 streams.
export function seededRandom(seed) {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  h = Math.imul(h ^ (h >>> 16), 2246822507);
  h = Math.imul(h ^ (h >>> 13), 3266489909);
  let a = (h ^= h >>> 16) >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle(list, rnd) {
  const out = [...list];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function auditItem(r, stratum) {
  return {
    rank: r.rank,
    lemma: r.lemma,
    pos: r.pos,
    stress: r.stress,
    variants: [...(r.variants || [])],
    status: r.status,
    stratum,
    note: r.note || "",
  };
}

// Draw the sample from the built rows. One PRNG stream per stratum, seeded
// from the seed and the stratum id, so adding a stratum later never moves an
// earlier draw. Rows are sorted by rank first so the input order is fixed.
export function drawSample(rows, { seed, sizes = {} } = {}) {
  if (!seed) throw new Error("drawSample needs a seed");
  const items = [];
  const counts = {};
  for (const s of STRATA) {
    const pool = rows.filter((r) => r.pos !== "PROPN" && r.stress && s.pick(r)).sort((a, b) => a.rank - b.rank);
    const want = sizes[s.id] === undefined ? s.size : sizes[s.id];
    const drawn = want === null ? pool : shuffle(pool, seededRandom(`${seed}:${s.id}`)).slice(0, want);
    counts[s.id] = { pool: pool.length, drawn: drawn.length, census: want === null };
    for (const r of drawn.sort((a, b) => a.rank - b.rank)) items.push(auditItem(r, s.id));
  }
  return { seed, sizes: Object.fromEntries(STRATA.map((s) => [s.id, sizes[s.id] === undefined ? s.size : sizes[s.id]])), counts, items };
}

export function wilson(k, n, z = Z95) {
  if (!n) return { lo: 0, hi: 0, p: 0 };
  const p = k / n;
  const d = 1 + (z * z) / n;
  const c = p + (z * z) / (2 * n);
  const m = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return { p, lo: (c - m) / d, hi: (c + m) / d };
}

export const VERDICTS = ["correct", "wrong", "both", "unsure"];

// One row's panel reading from its answers (verdict ids, at most PANEL).
//   judged    at least MIN_JUDGED_ANSWERS answers that are not "unsure"
//   verdict   "wrong" unless not-wrong answers outnumber wrong ones; among
//             not-wrong rows, "both" when "both" answers are at least as many
//             as "correct"; null while the row is not judged
//   split     reviewers disagreed on wrong against not wrong
export function panelVerdict(verdicts = []) {
  const a = verdicts.filter((v) => VERDICTS.includes(v)).slice(0, PANEL);
  const n = { correct: 0, wrong: 0, both: 0, unsure: 0 };
  for (const v of a) n[v] += 1;
  const judgedAnswers = a.length - n.unsure;
  const notWrong = n.correct + n.both;
  const judged = judgedAnswers >= MIN_JUDGED_ANSWERS;
  let verdict = null;
  if (judged) verdict = notWrong > n.wrong ? (n.both >= n.correct ? "both" : "correct") : "wrong";
  return { answers: a.length, counts: n, judged, verdict, complete: a.length >= PANEL, split: n.wrong > 0 && notWrong > 0 };
}

// sample + accepted reviews -> per-stratum ROW counts, the interval, and the
// pre-registered verdict for the confident tier. Reviews are answers: up to
// PANEL per rank, read through panelVerdict(). An answer counts only when it
// names a rank in the sample and a known verdict.
//   n         rows sampled            reviewed  rows with at least one answer
//   complete  rows with a full panel  judged    rows the panel judged
//   correct / both / wrong            judged rows by panel verdict
//   unsure    full panel, still not judged (too many "not sure")
//   split     judged rows where reviewers disagreed on wrong
//   answers   every answer counted
export function auditSummary(sample, reviews = []) {
  const byRank = new Map((sample.items || []).map((it) => [it.rank, it]));
  const answersByRank = new Map();
  for (const rv of reviews) {
    if (!byRank.has(rv.rank) || !VERDICTS.includes(rv.verdict)) continue;
    if (!answersByRank.has(rv.rank)) answersByRank.set(rv.rank, []);
    answersByRank.get(rv.rank).push(rv.verdict);
  }
  const strata = Object.fromEntries(
    STRATA.map((s) => [s.id, { n: 0, reviewed: 0, complete: 0, answers: 0, judged: 0, correct: 0, wrong: 0, both: 0, unsure: 0, split: 0 }]),
  );
  for (const it of sample.items || []) strata[it.stratum].n += 1;
  for (const [rank, verdicts] of answersByRank) {
    const s = strata[byRank.get(rank).stratum];
    const p = panelVerdict(verdicts);
    s.reviewed += 1;
    s.answers += p.answers;
    if (p.complete) s.complete += 1;
    if (p.judged) {
      s.judged += 1;
      s[p.verdict] += 1;
      if (p.split) s.split += 1;
    } else if (p.complete) {
      s.unsure += 1;
    }
  }
  for (const s of Object.values(strata)) {
    s.notWrong = s.correct + s.both;
    s.interval = wilson(s.notWrong, s.judged);
    s.accuracy = s.judged ? Math.round((s.notWrong / s.judged) * 1000) / 10 : null;
  }
  const c = strata.confident;
  let verdict = "pending";
  if (c.judged >= MIN_REVIEWED) verdict = c.interval.lo >= TARGET ? "validated" : "below target";
  const total = (k) => Object.values(strata).reduce((a, s) => a + s[k], 0);
  return {
    version: AUDIT_VERSION,
    amendment: AMENDMENT,
    panel: PANEL,
    target: TARGET,
    minReviewed: MIN_REVIEWED,
    strata,
    verdict,
    reviewed: answersByRank.size,
    answers: total("answers"),
    complete: total("complete"),
  };
}
