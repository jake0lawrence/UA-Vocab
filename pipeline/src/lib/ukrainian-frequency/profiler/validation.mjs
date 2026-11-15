// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. Validation.
//
// Pure. Runs the profiler in level mode over a set of texts whose level is
// asserted by an independent source and reports, per text, the strict
// coverage against each validated level (A1 to C1), the coverage at the
// asserted level, the verdict level (the lowest level whose validated
// vocabulary reaches the threshold), and whether it matches the claim. The
// build script freezes the result; the test and the page re-derive it.
//
// Publish whichever way it comes out. A mismatch is a finding about the
// thresholds, the sources, or the texts, and the summary keeps all three
// readings visible: exact agreement, within one level, and the share of texts
// that never reach the threshold at any validated level (which, given that
// only 6403 of 12000 lemmas carry a validated level, is expected to be large).
// ============================================================

import { LEVELS, LEVEL_ORDER } from "./lexicon.mjs";
import { levelPart, composeKnownSet } from "./known-sets.mjs";
import { tokenize } from "./tokenize.mjs";
import { lemmatizeTokens } from "./lemmatize.mjs";
import { profileTokens, DEFAULT_THRESHOLD } from "./profile.mjs";

export function levelSets(lex) {
  const out = {};
  for (const L of LEVELS) out[L] = composeKnownSet([levelPart(lex, L)], `PULS up to ${L}`);
  return out;
}

export function runValidation(texts, lex, { threshold = DEFAULT_THRESHOLD } = {}) {
  const sets = levelSets(lex);
  const rows = texts.map((t) => {
    const lem = lemmatizeTokens(tokenize(t.text), lex);
    const byLevel = {};
    const leveledByLevel = {};
    let verdict = null;
    let leveledVerdict = null;
    let offListPct = 0;
    let unlabeledPct = 0;
    let tokens = 0;
    for (const L of LEVELS) {
      const p = profileTokens(lem, sets[L], lex, { threshold, level: L });
      byLevel[L] = p.counting.strict.coverage;
      leveledByLevel[L] = p.counting.leveledOnly.coverage;
      if (verdict == null && p.counting.strict.coverage >= threshold) verdict = L;
      if (leveledVerdict == null && p.counting.leveledOnly.coverage >= threshold) leveledVerdict = L;
      if (L === "C1") {
        tokens = p.tokens;
        offListPct = p.tokens ? Math.round((p.decomposition.offList / p.tokens) * 1000) / 10 : 0;
        unlabeledPct = p.tokens ? Math.round((p.decomposition.unlabeledOnList / p.tokens) * 1000) / 10 : 0;
      }
    }
    const atAsserted = byLevel[t.level];
    const gap = verdict ? LEVEL_ORDER[verdict] - LEVEL_ORDER[t.level] : null;
    const leveledGap = leveledVerdict ? LEVEL_ORDER[leveledVerdict] - LEVEL_ORDER[t.level] : null;
    return {
      id: t.id, title: t.title, level: t.level, tokens, byLevel, atAsserted, verdict,
      match: verdict === t.level, withinOne: gap != null && Math.abs(gap) <= 1, gap,
      leveledByLevel, leveledAtAsserted: leveledByLevel[t.level], leveledVerdict,
      leveledMatch: leveledVerdict === t.level, leveledWithinOne: leveledGap != null && Math.abs(leveledGap) <= 1, leveledGap,
      offListPct, unlabeledPct,
    };
  });
  const n = rows.length;
  const exact = rows.filter((r) => r.match).length;
  const withinOne = rows.filter((r) => r.withinOne).length;
  const unresolved = rows.filter((r) => r.verdict == null).length;
  const leveledExact = rows.filter((r) => r.leveledMatch).length;
  const leveledWithinOne = rows.filter((r) => r.leveledWithinOne).length;
  const leveledUnresolved = rows.filter((r) => r.leveledVerdict == null).length;
  const perLevel = {};
  for (const L of [...new Set(texts.map((t) => t.level))]) {
    const rs = rows.filter((r) => r.level === L);
    const mean = (k) => Math.round((rs.reduce((a, r) => a + r[k], 0) / rs.length) * 10) / 10;
    perLevel[L] = {
      n: rs.length,
      meanAtAsserted: mean("atAsserted"),
      meanLeveledAtAsserted: mean("leveledAtAsserted"),
      meanOffList: mean("offListPct"),
      meanUnlabeled: mean("unlabeledPct"),
      exact: rs.filter((r) => r.match).length,
      unresolved: rs.filter((r) => r.verdict == null).length,
      verdicts: countBy(rs.map((r) => r.verdict || "none")),
      leveledExact: rs.filter((r) => r.leveledMatch).length,
      leveledVerdicts: countBy(rs.map((r) => r.leveledVerdict || "none")),
    };
  }
  // Ordering check: read at one fixed level (A1 to B1 known), does mean coverage
  // fall as the asserted level rises? Reported at two grains, because the set
  // supports one and not the other. `ordersLevels` is the strict three-point
  // monotone read; `aGap` and `b1Drop` say what actually separates, since nine
  // A1 texts and ten A2 texts do not distinguish half a coverage point while the
  // B1 drop is an order of magnitude larger.
  const order = ["A1", "A2", "B1"].filter((L) => perLevel[L]);
  const meanAtB1 = order.map((L) => Math.round((rows.filter((r) => r.level === L).reduce((a, r) => a + r.byLevel.B1, 0) / perLevel[L].n) * 10) / 10);
  const monotone = meanAtB1.every((v, i) => i === 0 || v <= meanAtB1[i - 1]);
  const byAsserted = Object.fromEntries(order.map((L, i) => [L, meanAtB1[i]]));
  const aGap = byAsserted.A1 != null && byAsserted.A2 != null ? Math.round(Math.abs(byAsserted.A1 - byAsserted.A2) * 10) / 10 : null;
  const b1Drop =
    byAsserted.B1 != null && byAsserted.A1 != null && byAsserted.A2 != null
      ? Math.round((Math.min(byAsserted.A1, byAsserted.A2) - byAsserted.B1) * 10) / 10
      : null;
  return {
    threshold,
    n,
    exact,
    exactPct: n ? Math.round((exact / n) * 1000) / 10 : 0,
    withinOne,
    withinOnePct: n ? Math.round((withinOne / n) * 1000) / 10 : 0,
    unresolved,
    leveled: {
      exact: leveledExact,
      exactPct: n ? Math.round((leveledExact / n) * 1000) / 10 : 0,
      withinOne: leveledWithinOne,
      withinOnePct: n ? Math.round((leveledWithinOne / n) * 1000) / 10 : 0,
      unresolved: leveledUnresolved,
    },
    perLevel,
    meanAtB1ByAsserted: byAsserted,
    ordersLevels: monotone,
    aGap,
    b1Drop,
    rows,
  };
}

function countBy(list) {
  const o = {};
  for (const x of list) o[x] = (o[x] || 0) + 1;
  return o;
}
