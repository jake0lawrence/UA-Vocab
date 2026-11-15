// ============================================================
// UKRAINIAN FREQUENCY : thread 06, the text profiler. Tokenizer.
//
// Pure, browser-safe. Splits Ukrainian running text into word tokens and
// normalizes each one the way the lemma list is keyed: lowercase, stress mark
// (U+0301) stripped, the three apostrophe glyphs folded to U+2019 (the list's
// own glyph; see the 2026-09-13 refresh note in dataset.mjs), soft hyphen and
// zero-width marks dropped. Latin words and numbers are not tokens: the
// profiler measures Ukrainian vocabulary, so a stray English word or a year is
// neither known nor unknown, it is simply not counted.
//
// House rule: no em-dashes in this file.
// ============================================================

const WORD_RE = /[Ѐ-ӿ́][Ѐ-ӿ́'’ʼ`-]*/gu;
const STRIP_RE = /[́­​-‍﻿]/g;
const APOS_RE = /['ʼ`]/g;
const CYR_LETTER_RE = /[Ѐ-ӿ]/;
const UPPER_RE = /^[Ѐ-ЯЀ-Џ]/;

export function normalizeToken(raw) {
  let t = String(raw || "").normalize("NFC").replace(STRIP_RE, "").replace(APOS_RE, "’").toLowerCase();
  // trailing / leading punctuation that rode along (a hyphen used as a dash)
  t = t.replace(/^[-’]+|[-’]+$/g, "");
  return t;
}

// True when the raw token starts with an upper-case Cyrillic letter.
export function isCapitalized(raw) {
  const s = String(raw || "").replace(STRIP_RE, "");
  return UPPER_RE.test(s) && s[0] !== s[0].toLowerCase();
}

// Tokenize a text. Each token carries the raw surface form, its normalized key,
// whether it was capitalized, whether it opened a sentence (so a capital there
// is not evidence of a name), and its offsets in the input (`start` inclusive,
// `end` exclusive, so `text.slice(start, end) === raw`), which lets a page mark
// each word in place without re-searching the text.
export function tokenize(text) {
  const src = String(text || "");
  const out = [];
  let sentenceStart = true;
  let last = 0;
  WORD_RE.lastIndex = 0;
  let m;
  while ((m = WORD_RE.exec(src))) {
    const between = src.slice(last, m.index);
    // a new sentence opens after end punctuation, a blank line, or a dialogue dash
    if (out.length === 0 || /[.!?…:]/.test(between) || /\n\s*\n/.test(between) || /\n\s*[-\u2013\u2014]\s*$/.test(between)) {
      sentenceStart = true;
    }
    const raw = m[0];
    const norm = normalizeToken(raw);
    last = m.index + raw.length;
    if (!norm || !CYR_LETTER_RE.test(norm)) continue;
    out.push({ raw, norm, capitalized: isCapitalized(raw), sentenceInitial: sentenceStart, start: m.index, end: last });
    sentenceStart = false;
  }
  return out;
}

// Counts the tokenizer reports beside the profile.
export function tokenStats(tokens) {
  const types = new Set(tokens.map((t) => t.norm));
  return { tokens: tokens.length, types: types.size };
}
