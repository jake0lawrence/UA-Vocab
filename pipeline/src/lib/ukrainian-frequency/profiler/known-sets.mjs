// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. Known-word sets.
//
// A known set is what a specific learner (or class) has covered: a level's
// validated vocabulary, a published minimum, a pasted list, or a stack of
// those. It is composed from named parts so the number it produces stays
// interpretable ("Borodin A1 plus units 1 to 6 plus last week's 40 words").
//
// Shape:  { name, parts: [{ kind, id?, label, size }], lemmas: Set<idx>,
//           offList: Set<string>, size }
// `lemmas` are indices on the top-12000 list; `offList` are normalized strings
// the list does not carry (a pasted word the list lacks still counts as known
// when it appears verbatim in a text).
// ============================================================

import { LEVELS, LEVEL_ORDER } from "./lexicon.mjs";
import { tokenize } from "./tokenize.mjs";
import { resolveToken } from "./lexicon.mjs";

// Level mode: every lemma the validated map places at or below `level`.
export function levelPart(lex, level) {
  const max = LEVEL_ORDER[level];
  if (!max) throw new Error(`unknown level ${level}`);
  const lemmas = new Set();
  for (const L of lex.lemmas) if (L.level && LEVEL_ORDER[L.level] <= max) lemmas.add(L.i);
  return { kind: "level", id: level, label: `PULS ${level === "A1" ? "A1" : `A1 to ${level}`}`, lemmas, offList: new Set(), size: lemmas.size };
}

// A published set shipped in the lexicon (Borodin A1 / A2).
export function publishedPart(lex, id) {
  const s = lex.sets[id];
  if (!s) throw new Error(`unknown published set ${id}`);
  const lemmas = new Set(s.idx);
  const offList = new Set(s.offList || []);
  const label = id === "borodinA1" ? "Borodin A1 (1000 i 1 slovo)" : id === "borodinA2" ? "Borodin A2 (1000 i 1 slovo)" : id;
  return { kind: "published", id, label, lemmas, offList, size: lemmas.size + offList.size };
}

// A pasted list or an uploaded CSV. Every Cyrillic token in the text is a
// candidate: it is lemmatized against the list (so an inflected form on the
// teacher's list still lands on its lemma), and anything the list does not
// know is kept verbatim as an off-list known word. Returns the part plus the
// resolution counts so the UI can show "312 words: 290 on the list, 22 not".
export function listPart(lex, text, label = "Pasted list") {
  const lemmas = new Set();
  const offList = new Set();
  let entries = 0;
  const seen = new Set();
  for (const t of tokenize(text)) {
    if (seen.has(t.norm)) continue;
    seen.add(t.norm);
    entries++;
    const hit = resolveToken(lex, t.norm);
    if (hit) lemmas.add(hit.i);
    else offList.add(t.norm);
  }
  return { kind: "list", id: null, label, lemmas, offList, size: lemmas.size + offList.size, entries };
}

// Stack parts into one named set. Union semantics; the composition is kept.
export function composeKnownSet(parts, name) {
  const lemmas = new Set();
  const offList = new Set();
  for (const p of parts) {
    for (const i of p.lemmas) lemmas.add(i);
    for (const w of p.offList) offList.add(w);
  }
  const autoName = parts.map((p) => p.label).join(" + ");
  return {
    name: name || autoName || "Empty set",
    parts: parts.map((p) => ({ kind: p.kind, id: p.id, label: p.label, size: p.size })),
    lemmas,
    offList,
    size: lemmas.size + offList.size,
  };
}

export function isKnown(set, tok) {
  if (tok.i != null) return set.lemmas.has(tok.i);
  return set.offList.has(tok.norm);
}

// Serialize / revive a set for client-side storage (indices + strings only;
// no text of any analyzed passage is ever part of a set). A saved set records
// the list version its indices point into, because an index is a rank.
export function serializeKnownSet(set, listVersion = null) {
  const out = { name: set.name, parts: set.parts, lemmas: [...set.lemmas].sort((a, b) => a - b), offList: [...set.offList].sort() };
  if (listVersion) out.listVersion = listVersion;
  return out;
}
export function reviveKnownSet(obj) {
  return { name: obj.name, parts: obj.parts || [], lemmas: new Set(obj.lemmas || []), offList: new Set(obj.offList || []), size: (obj.lemmas || []).length + (obj.offList || []).length };
}

// Sets saved before a list refresh point their indices into the old list.
// The lexicon bundle carries `migrate` ({ from, toIndex }): the old index of
// every row mapped to its index on the current list, or -1 where the cleanup
// dropped the row. A set without a recorded version is from the first list
// (v0.1.0). Returns the entry re-indexed and stamped, plus how many indices
// were lost; a set already on the current list comes back untouched, and one
// from a list the bundle cannot map keeps its indices and its old stamp.
export function migrateKnownSetEntry(entry, lex) {
  const current = lex.listVersion;
  if (!current) return { entry, dropped: 0, migrated: false };
  const from = entry.listVersion || (lex.migrate && lex.migrate.from) || null;
  if (from === current) return { entry, dropped: 0, migrated: false };
  if (!lex.migrate || lex.migrate.from !== from) return { entry, dropped: 0, migrated: false };
  const to = lex.migrate.toIndex;
  const seen = new Set();
  let dropped = 0;
  for (const i of entry.lemmas || []) {
    const j = to[i];
    if (j == null || j < 0) dropped += 1;
    else seen.add(j);
  }
  return { entry: { ...entry, lemmas: [...seen].sort((a, b) => a - b), listVersion: current }, dropped, migrated: true };
}

export { LEVELS };
