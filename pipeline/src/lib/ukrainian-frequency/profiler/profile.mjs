// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. The profile.
//
// Pure. Given lemmatized tokens and a known set, computes:
//  - strict coverage (the floor): only lemmas in the set count as known
//  - aspect-linked coverage: an unknown verb whose aspect partner is known
//    counts as partly known (reported as a delta, never merged into strict)
//  - family-linked coverage: an unknown lemma with a known family member
//    counts as partly known (same treatment)
//  - straddle warnings: the specific words where the family or aspect
//    assumption is known to break, because the two relatives sit two or more
//    validated levels apart
//  - the token decomposition (known / above level / unlabeled / off-list /
//    names), the verdict against the threshold, and the gloss list
//
// Coverage is running-text (token) coverage, the measure the 95 and 98 percent
// thresholds were stated for (Laufer 1989; Hu and Nation 2000; Nation 2006).
// Names sit outside the denominator by default. Off-list tokens stay in it:
// a word the list does not carry is unknown to the reader too.
// ============================================================

import { LEVEL_ORDER } from "./lexicon.mjs";
import { isKnown } from "./known-sets.mjs";

export const DEFAULT_THRESHOLD = 95;
export const THRESHOLDS = [95, 98];
export const STRADDLE_GAP = 2;

const pct = (a, b) => (b > 0 ? Math.round((a / b) * 1000) / 10 : 0);

export function profileTokens(lemmatized, knownSet, lex, { threshold = DEFAULT_THRESHOLD, countNames = false, level = null } = {}) {
  const inScope = lemmatized.filter((t) => countNames || t.kind !== "name");
  const names = lemmatized.length - inScope.length;
  const N = inScope.length;

  // strict pass + per-lemma tallies
  const unknownCounts = new Map(); // key: lemma idx (number) or off-list string
  let known = 0;
  let unknownOnList = 0;
  let unknownOffList = 0;
  let unlabeledOnList = 0; // on-list, no validated level (level mode's blind spot)
  let aboveLevel = 0;
  const knownLemmas = new Set();
  const unknownLemmas = new Set();
  const maxLevel = level ? LEVEL_ORDER[level] : null;
  for (const t of inScope) {
    if (isKnown(knownSet, t)) {
      known++;
      if (t.i != null) knownLemmas.add(t.i);
      continue;
    }
    const key = t.i != null ? t.i : t.norm;
    unknownCounts.set(key, (unknownCounts.get(key) || 0) + 1);
    if (t.i != null) {
      unknownOnList++;
      unknownLemmas.add(t.i);
      const L = lex.lemmas[t.i];
      if (!L.level) unlabeledOnList++;
      else if (maxLevel && LEVEL_ORDER[L.level] > maxLevel) aboveLevel++;
    } else unknownOffList++;
  }

  // linked passes: which unknown lemmas have a known relative
  const aspectLinked = new Set();
  const familyLinked = new Set();
  const straddleWarnings = [];
  const seenWarn = new Set();
  for (const i of unknownLemmas) {
    const L = lex.lemmas[i];
    for (const p of lex.aspectPartners(i)) {
      if (!knownSet.lemmas.has(p)) continue;
      aspectLinked.add(i);
      const P = lex.lemmas[p];
      if (L.level && P.level && Math.abs(LEVEL_ORDER[L.level] - LEVEL_ORDER[P.level]) >= STRADDLE_GAP && !seenWarn.has(`a:${i}:${p}`)) {
        seenWarn.add(`a:${i}:${p}`);
        straddleWarnings.push({ kind: "aspect", lemma: L.lemma, level: L.level, relative: P.lemma, relativeLevel: P.level, levelGap: Math.abs(LEVEL_ORDER[L.level] - LEVEL_ORDER[P.level]) });
      }
    }
    let bestGap = null;
    for (const f of lex.familyMembers(i)) {
      if (!knownSet.lemmas.has(f)) continue;
      familyLinked.add(i);
      const Fm = lex.lemmas[f];
      if (L.level && Fm.level) {
        const gap = Math.abs(LEVEL_ORDER[L.level] - LEVEL_ORDER[Fm.level]);
        if (gap >= STRADDLE_GAP && (bestGap == null || gap > bestGap.levelGap)) bestGap = { kind: "family", lemma: L.lemma, level: L.level, relative: Fm.lemma, relativeLevel: Fm.level, levelGap: gap };
      }
    }
    if (bestGap) straddleWarnings.push(bestGap);
  }
  let aspectTokens = 0;
  let familyTokens = 0;
  for (const [key, c] of unknownCounts) {
    if (typeof key !== "number") continue;
    if (aspectLinked.has(key)) aspectTokens += c;
    if (familyLinked.has(key)) familyTokens += c;
  }

  const strictCoverage = pct(known, N);
  // the conditional reading for level mode: among the tokens that carry a
  // validated level at all, the share at or below the chosen level. Removes
  // the map's blind spot (unlabeled and off-list tokens) from the denominator,
  // so it answers "is the leveled vocabulary of this text at this level" and
  // nothing about the words the map has not reached. Reported beside strict,
  // never in its place.
  let leveledTokens = 0;
  let leveledAtOrBelow = 0;
  if (maxLevel) {
    for (const t of inScope) {
      if (t.i == null) continue;
      const lv = lex.lemmas[t.i].level;
      if (!lv) continue;
      leveledTokens++;
      if (LEVEL_ORDER[lv] <= maxLevel) leveledAtOrBelow++;
    }
  }
  const leveledCoverage = maxLevel ? pct(leveledAtOrBelow, leveledTokens) : null;
  const aspectCoverage = pct(known + aspectTokens, N);
  const familyCoverage = pct(known + familyTokens, N);

  // gloss list: unknown items, most frequent in this text first
  const gloss = [...unknownCounts.entries()]
    .map(([key, count]) => {
      if (typeof key === "number") {
        const L = lex.lemmas[key];
        return { lemma: L.lemma, pos: L.pos, rank: L.rank, level: L.level, count, matched: true, aspectLinked: aspectLinked.has(key), familyLinked: familyLinked.has(key) };
      }
      // `matched: false` is the honest claim. The token did not reach a lemma;
      // whether that is because the list lacks the word, or has it with no
      // paradigm table, or has a table missing this form, the profiler carries
      // no morphology and cannot tell. Never label these "off the list".
      return { lemma: key, pos: null, rank: null, level: null, count, matched: false, aspectLinked: false, familyLinked: false };
    })
    .sort((a, b) => b.count - a.count || (a.rank ?? 1e9) - (b.rank ?? 1e9) || a.lemma.localeCompare(b.lemma, "uk"));

  const verdict = strictCoverage >= threshold ? "meets" : strictCoverage >= threshold - 5 ? "near" : "below";

  return {
    tokens: N,
    names,
    types: new Set(inScope.map((t) => (t.i != null ? `i${t.i}` : `s${t.norm}`))).size,
    known,
    unknown: N - known,
    knownLemmaTypes: knownLemmas.size,
    unknownTypes: gloss.length,
    decomposition: {
      known,
      aboveLevel,
      unlabeledOnList,
      unknownOnListLeveled: unknownOnList - unlabeledOnList - aboveLevel,
      offList: unknownOffList,
      names,
    },
    counting: {
      strict: { coverage: strictCoverage, known, unknown: N - known },
      leveledOnly: maxLevel ? { coverage: leveledCoverage, tokens: leveledTokens, atOrBelow: leveledAtOrBelow } : null,
      aspectLinked: { coverage: aspectCoverage, delta: Math.round((aspectCoverage - strictCoverage) * 10) / 10, lemmas: aspectLinked.size, tokens: aspectTokens },
      familyLinked: { coverage: familyCoverage, delta: Math.round((familyCoverage - strictCoverage) * 10) / 10, lemmas: familyLinked.size, tokens: familyTokens },
      straddleWarnings: straddleWarnings.sort((a, b) => b.levelGap - a.levelGap || a.lemma.localeCompare(b.lemma, "uk")),
    },
    threshold,
    verdict,
    gloss,
  };
}

// Level mode helper: the lowest validated level at which strict coverage of
// this text reaches the threshold, or null when even A1 to C1 does not.
export function verdictLevel(lemmatized, lex, levelSets, { threshold = DEFAULT_THRESHOLD, countNames = false } = {}) {
  const out = { byLevel: {}, verdict: null };
  for (const level of Object.keys(levelSets)) {
    const p = profileTokens(lemmatized, levelSets[level], lex, { threshold, countNames, level });
    out.byLevel[level] = p.counting.strict.coverage;
    if (out.verdict == null && p.counting.strict.coverage >= threshold) out.verdict = level;
  }
  return out;
}
