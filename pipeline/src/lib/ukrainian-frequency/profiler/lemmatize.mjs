// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. Lemmatizer.
//
// Pure. Maps tokenizer output onto the lexicon: each token becomes a lemma
// index (on the top-12000 list) or one of two off-list kinds. `name` is a
// capitalized token that is not sentence-initial and that the list does not
// know (or knows only as a proper noun); by default names sit outside the
// coverage denominator, the convention of the lexical frequency profile
// (Laufer and Nation 1995), and the page reports how many there were.
//
// Honesty limit, stated on the page: a form is recognized only when the
// Wiktionary paradigm table lists it (70.6 percent of the lemmas carry a
// table) or when it is the lemma string itself. A real inflected form of a
// lemma without a table reads as off-list, so off-list counts are an upper
// bound and coverage a lower bound.
// ============================================================

import { resolveToken } from "./lexicon.mjs";

export function lemmatizeTokens(tokens, lex) {
  return tokens.map((t) => {
    const hit = resolveToken(lex, t.norm);
    if (hit) {
      const L = lex.lemmas[hit.i];
      const isName = L.pos === "PROPN" || (t.capitalized && !t.sentenceInitial && hit.via !== "lemma" && hit.via !== "form");
      return { ...t, i: hit.i, via: hit.via, ambiguous: hit.ambiguous, kind: isName ? "name" : "list" };
    }
    if (t.capitalized && !t.sentenceInitial) return { ...t, i: null, via: null, ambiguous: false, kind: "name" };
    return { ...t, i: null, via: null, ambiguous: false, kind: "offlist" };
  });
}

// Fold lemmatized tokens into a bag: lemma index -> count, plus off-list
// strings -> count and the name count. The unit sequence planning works on.
export function toBag(lemmatized, { countNames = false } = {}) {
  const lemmaCounts = new Map();
  const offList = new Map();
  let names = 0;
  let tokens = 0;
  for (const t of lemmatized) {
    if (t.kind === "name" && !countNames) { names++; continue; }
    tokens++;
    if (t.i != null) lemmaCounts.set(t.i, (lemmaCounts.get(t.i) || 0) + 1);
    else offList.set(t.norm, (offList.get(t.norm) || 0) + 1);
  }
  return { lemmaCounts, offList, names, tokens };
}
