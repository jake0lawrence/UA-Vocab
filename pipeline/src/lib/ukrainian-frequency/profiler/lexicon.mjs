// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. The lexicon.
//
// Two halves. `buildLexicon` is the Node-side assembler the build script runs
// over the committed source tiers (the top-12000 seed, the Wiktionary paradigm
// forms, the validated PULS levels, the Wiktionary family graph, the B1 aspect
// relations, the two Borodin minimums); it returns the two JSON artifacts the
// page downloads (lexicon.json, forms.json). `loadLexicon` is the browser-side
// reader that turns those two artifacts into lookup maps. Both are pure.
//
// Levels are the validated PULS levels only (A1 to C1, 6403 of 12000 lemmas);
// the unlabeled rest carry null and are never guessed. Family ids come from the
// Wiktionary derivational graph; aspect links from the B1 relation table
// (partners, plus the hand-curated suppletive pairs), so they cover verbs that
// touch a validated B1 verb and no others. The page says both.
//
// House rule: no em-dashes.
// ============================================================

import { normalizeToken } from "./tokenize.mjs";

export const LEVELS = ["A1", "A2", "B1", "B2", "C1"];
export const LEVEL_ORDER = { A1: 1, A2: 2, B1: 3, B2: 4, C1: 5 };
export const PUBLISHED_SETS = ["borodinA1", "borodinA2"];

// Surface forms the source dictionary never lists as lemmas because its
// tokenizer splits them: немає / нема ("there is no", "has not") is counted
// upstream under мати, so a text's немає resolves there. Kept tiny and
// documented; nothing else is aliased.
export const ALIASES = { "немає": "мати", "нема": "мати" };

// ------------------------------------------------------------
// Build (Node). Inputs are the parsed committed files.
//  seed:      ubertext-lemmas-top12k.json ({ rows: [{lemma,pos,count,docs}] })
//  formRows:  [{ rank, lemma, pos, form }] from paradigms/forms.csv
//  puls:      puls-cefr.json ({ rows: [{rank,lemma,pos,level}] })
//  families:  wiktionary-families.json ({ families: [{id, listMembers:[{lemma,rank,pos,level}]}] })
//  aspect:    b1-aspect.json ({ relations: [...], suppletiveTable: [[a,b]] })
//  borodinA1 / borodinA2: borodin-*.json ({ rows: [{entry, kind, headwords, matched, rank, lemma}] })
// ------------------------------------------------------------
export function buildLexicon({ seed, formRows, puls, families, aspect, borodinA1, borodinA2, crosswalk = null, listVersion = null }) {
  const rows = seed.rows;
  const n = rows.length;
  // rank i+1 is row i (the seed is frequency-ordered; the release ranks it the same way)
  const lemmas = rows.map((r, i) => ({ lemma: normalizeToken(r.lemma), pos: r.pos, rank: i + 1, level: null, family: null }));
  const byRank = (rank) => (rank >= 1 && rank <= n ? lemmas[rank - 1] : null);

  // validated levels, by rank (the PULS join is rank-keyed and POS-aware already)
  for (const r of puls.rows) {
    const L = byRank(r.rank);
    if (L && normalizeToken(r.lemma) === L.lemma) L.level = r.level;
  }

  // families
  const familyMembers = {};
  for (const f of families.families) {
    const members = f.listMembers.map((m) => m.rank).filter((rank) => byRank(rank)).map((rank) => rank - 1);
    if (members.length < 2) continue;
    familyMembers[f.id] = members;
    for (const idx of members) lemmas[idx].family = f.id;
  }

  // aspect links: partner relations both on list, plus suppletive pairs
  const lemmaIdx = new Map();
  lemmas.forEach((L, i) => {
    if (!lemmaIdx.has(L.lemma)) lemmaIdx.set(L.lemma, []);
    lemmaIdx.get(L.lemma).push(i);
  });
  const verbIdx = (lemma) => {
    const c = (lemmaIdx.get(normalizeToken(lemma)) || []).filter((i) => lemmas[i].pos === "VERB");
    return c.length ? c[0] : null;
  };
  const pairKey = new Set();
  const aspectPairs = [];
  const addPair = (a, b) => {
    if (a == null || b == null || a === b) return;
    const k = a < b ? `${a}:${b}` : `${b}:${a}`;
    if (pairKey.has(k)) return;
    pairKey.add(k);
    aspectPairs.push(a < b ? [a, b] : [b, a]);
  };
  for (const r of aspect.relations) {
    if (r.kind !== "partner" || !r.relatedOnList) continue;
    addPair(verbIdx(r.b1), verbIdx(r.related));
  }
  for (const [a, b] of aspect.suppletiveTable || []) addPair(verbIdx(a), verbIdx(b));

  // Published sets. EVERY headword of an entry counts, not just the entry's
  // best-ranked one. The authors' unit is the entry line, and an entry can name
  // several words: an aspect pair ("бачити - побачити"), a gender pair ("автор /
  // авторка"), a spelling variant set ("в, у"). A reader who has studied the
  // entry knows all of them, so a known-word set that kept only the commonest
  // member marked the others unknown: 58 A1 and 119 A2 lemmas, including у from
  // the list's own first entry. Each headword resolves the way the published
  // join does, to the highest-frequency seed lemma with that spelling.
  const setFrom = (b) => {
    const idx = new Set();
    const offList = new Set();
    for (const r of b.rows) {
      if (r.kind !== "word") continue;
      for (const h of r.headwords || []) {
        const w = normalizeToken(h);
        if (!w) continue;
        const hits = lemmaIdx.get(w);
        if (hits && hits.length) idx.add(hits[0]);
        else offList.add(w);
      }
    }
    return { idx: [...idx].sort((a, c) => a - c), offList: [...offList].sort() };
  };
  const sets = { borodinA1: setFrom(borodinA1), borodinA2: setFrom(borodinA2) };

  // forms: surface form -> lemma index list (frequency order), only where the
  // form differs from its lemma (the lemma matches itself without a table)
  const forms = {};
  for (const r of formRows) {
    const L = byRank(Number(r.rank));
    if (!L) continue;
    const f = normalizeToken(r.form);
    if (!f || f === L.lemma) continue;
    const i = L.rank - 1;
    const cur = forms[f];
    if (cur === undefined) forms[f] = i;
    else if (Array.isArray(cur)) { if (!cur.includes(i)) cur.push(i); }
    else if (cur !== i) forms[f] = [cur, i];
  }
  for (const k of Object.keys(forms)) if (Array.isArray(forms[k])) forms[k].sort((a, b) => a - b);

  const lexicon = {
    lemmas: lemmas.map((L) => [L.lemma, L.pos, L.level, L.family]),
    families: familyMembers,
    aspectPairs,
    sets,
  };
  // A saved known set stores lemma INDICES, which are ranks on one list. The
  // bundle names its list, and carries the crosswalk from the previous list as
  // a flat index map (old index -> new index, -1 where the cleanup dropped the
  // row) so sets saved under the old list migrate on load.
  if (listVersion) lexicon.listVersion = listVersion;
  if (crosswalk) {
    const toIndex = new Array(crosswalk.rows.length).fill(-1);
    for (const r of crosswalk.rows) toIndex[r.v1Rank - 1] = r.v2Rank ? r.v2Rank - 1 : -1;
    lexicon.migrate = { from: crosswalk.from, toIndex };
  }
  return { lexicon, forms: { forms } };
}

// ------------------------------------------------------------
// Load (browser + tests). Turns the two artifacts into lookups.
// ------------------------------------------------------------
export function loadLexicon(lexiconJson, formsJson) {
  const lemmas = lexiconJson.lemmas.map(([lemma, pos, level, family], i) => ({ i, lemma, pos, level, family, rank: i + 1 }));
  const lemmaIdx = new Map();
  for (const L of lemmas) {
    if (!lemmaIdx.has(L.lemma)) lemmaIdx.set(L.lemma, []);
    lemmaIdx.get(L.lemma).push(L.i);
  }
  const forms = new Map();
  for (const [f, v] of Object.entries(formsJson.forms || {})) forms.set(f, Array.isArray(v) ? v : [v]);
  const familyOf = new Map();
  for (const [id, members] of Object.entries(lexiconJson.families || {})) familyOf.set(id, members);
  const aspectOf = new Map();
  for (const [a, b] of lexiconJson.aspectPairs || []) {
    if (!aspectOf.has(a)) aspectOf.set(a, []);
    if (!aspectOf.has(b)) aspectOf.set(b, []);
    aspectOf.get(a).push(b);
    aspectOf.get(b).push(a);
  }
  return {
    lemmas,
    lemmaIdx,
    forms,
    familyOf,
    aspectOf,
    sets: lexiconJson.sets || {},
    size: lemmas.length,
    listVersion: lexiconJson.listVersion || null,
    migrate: lexiconJson.migrate || null,
    // relatives of a lemma index through the family graph (excluding itself)
    familyMembers(i) {
      const fid = lemmas[i]?.family;
      if (!fid) return [];
      return (familyOf.get(fid) || []).filter((j) => j !== i);
    },
    aspectPartners(i) {
      return aspectOf.get(i) || [];
    },
  };
}

// How many list lemmas inflect but carry no form in the index. A form of any of
// them cannot be reached, so it lands in the unmatched bucket looking exactly
// like a word the list does not have. Derived live rather than hardcoded, so it
// tracks whatever bundle the page actually loaded.
const INFLECTING_POS = new Set(["NOUN", "PROPN", "VERB", "ADJ", "DET", "PRON", "NUM"]);

export function unmatchableLemmas(lex) {
  const targets = new Set();
  for (const v of lex.forms.values()) for (const i of v) targets.add(i);
  const missing = lex.lemmas.filter((L) => !targets.has(L.i));
  return { total: missing.length, inflecting: missing.filter((L) => INFLECTING_POS.has(L.pos)).length };
}

// Resolve one normalized token to a lemma index, or null. Exact lemma match
// wins; otherwise the most frequent lemma the form belongs to. Returns the
// index and how it was found.
export function resolveToken(lex, norm) {
  if (ALIASES[norm]) {
    const a = lex.lemmaIdx.get(ALIASES[norm]);
    const verb = (a || []).find((i) => lex.lemmas[i].pos === "VERB");
    if (verb != null) return { i: verb, via: "alias", ambiguous: false };
  }
  const exact = lex.lemmaIdx.get(norm);
  if (exact && exact.length) return { i: exact[0], via: "lemma", ambiguous: exact.length > 1 };
  const viaForm = lex.forms.get(norm);
  if (viaForm && viaForm.length) return { i: viaForm[0], via: "form", ambiguous: viaForm.length > 1 };
  // a hyphenated compound: take the part the list knows, if exactly one part resolves
  if (norm.includes("-")) {
    const parts = norm.split("-").filter(Boolean);
    const hits = parts.map((p) => resolveToken(lex, p)).filter(Boolean);
    if (hits.length === parts.length && hits.length > 0) return { ...hits[0], via: "compound", ambiguous: true };
  }
  return null;
}
