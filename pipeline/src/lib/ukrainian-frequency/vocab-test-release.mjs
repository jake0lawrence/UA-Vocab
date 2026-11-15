// ---------------------------------------------------------------------------
// Ukrainian Frequency - thread 05, the vocabulary-size self-test (pure builder).
//
// Builds a Yes/No checklist vocabulary-size test item bank, the standard
// psycholinguistic instrument for this job (Meara & Buffery's X_Lex / Y_Lex):
// a respondent checks off the real words they know from a mixed list of real
// words and invented pseudowords, and a false-alarm correction (checking
// pseudowords "known") guards the estimate against yea-saying.
//
// Item bank construction, fully deterministic and network-free:
//  - The 12000-lemma list (the committed thread-01 seed) is split into its 12
//    thousand-rank frequency bands, the same bands thread 01 already reports.
//  - Each band contributes 5 real lemmas (proper nouns, capitalized/mistagged
//    entries, and lemmas under 3 letters excluded) sampled at fixed offsets.
//  - Each band also contributes 5 pseudowords: a real lemma elsewhere in the
//    same band (a different lemma than any real item, so no answer leaks
//    another) run through ONE deterministic phonological letter substitution.
//    Every substitution position is tried, closest to the middle of the word
//    first; the first candidate that collides with neither the 12000-lemma
//    list, an already-generated pseudoword, nor a 333k-headword reference
//    Ukrainian dictionary (see uk-lexicon-dict_uk.SOURCE.md) is kept. If no
//    position on a source lemma clears all three checks, the next lemma in
//    the band is tried.
//  - The full 120-item bank is shuffled with a fixed-seed PRNG so band and
//    real/pseudo status are not adjacent or guessable in presentation order.
//
// Honesty discipline: this is a CONSTRUCTED instrument, not one independently
// validated against a psycholinguistic norming study. The page says so. The
// two-tier collision check (source corpus plus the larger reference
// dictionary) is real filtering, not a substitute for that validation.
//
// This module is pure data-processing (Node fs via readSeed and the committed
// lexicon). It is imported by the generator
// (scripts/ukrainian-frequency/build-vocab-test.mjs) and the drift-guard test,
// never by the client page.
// ---------------------------------------------------------------------------

import { readSeed } from "./release.mjs";
import { gunzipSync } from "node:zlib";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DATA_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../data/ukrainian-frequency");
const LEXICON_PATH = path.join(DATA_DIR, "uk-lexicon-dict_uk.txt.gz");

// A much larger (333k-headword) Ukrainian wordlist, used only to reject
// generated pseudowords that turn out to collide with a real word the
// 12000-lemma list does not contain. See uk-lexicon-dict_uk.SOURCE.md.
let cachedLexicon = null;
function loadLexicon() {
  if (!cachedLexicon) {
    const raw = gunzipSync(readFileSync(LEXICON_PATH));
    cachedLexicon = new Set(raw.toString("utf8").split("\n").filter(Boolean));
  }
  return cachedLexicon;
}

export const BAND_SIZE = 1000;
export const BAND_COUNT = 12;
export const REAL_PER_BAND = 5;
export const PSEUDO_PER_BAND = 5;
export const MIN_LEN = 3;
export const SHUFFLE_SEED = 1348;

// Offsets within a 1000-wide band (0-indexed), spread across the band and kept
// away from the real-item offsets so a pseudoword is never built from a lemma
// that is also asked as a real item.
const REAL_OFFSETS = [40, 210, 480, 650, 900];
const PSEUDO_START_OFFSETS = [120, 330, 560, 770, 950];

// One deterministic swap per letter: phonologically or visually adjacent
// Ukrainian letters, so the result still looks like a plausible word. Applied
// once, at the position closest to the middle of the source lemma.
const VOWEL_SWAP = {
  а: "о", о: "а",
  е: "и", и: "е",
  і: "о", ї: "і",
  у: "і", ю: "о",
  я: "е", є: "і",
};
const CONSONANT_SWAP = {
  б: "п", п: "б",
  в: "ф", ф: "в",
  г: "х", х: "г",
  ґ: "к", к: "ґ",
  д: "т", т: "д",
  ж: "ш", ш: "ж",
  з: "с", с: "з",
  й: "в",
  л: "р", р: "л",
  м: "н", н: "м",
  ц: "ч", ч: "ц",
  щ: "ч",
};

// Every letter position carrying a mapped swap, ordered closest-to-middle
// first (the position a construction like this should prefer, since changing
// an edge letter more often produces a real word with a common Ukrainian
// prefix or suffix left intact).
function targetPositions(letters) {
  const mid = (letters.length - 1) / 2;
  return letters
    .map((c, i) => ({ i, repl: VOWEL_SWAP[c] || CONSONANT_SWAP[c] }))
    .filter((t) => t.repl)
    .sort((a, b) => Math.abs(a.i - mid) - Math.abs(b.i - mid));
}

// Exported for the unit test: every one-letter-substitution candidate for a
// lemma, ordered closest-to-middle first, or [] if the lemma has no letter
// carrying a mapped swap (should not happen for real Ukrainian lemmas of
// MIN_LEN or more).
export function pseudowordCandidates(lemma) {
  const letters = [...lemma];
  return targetPositions(letters).map((t) => {
    const out = [...letters];
    out[t.i] = t.repl;
    return out.join("");
  });
}

// Excludes PROPN-tagged rows and, as a second, tag-independent guard, any
// lemma that starts with an uppercase letter. The source dictionary carries a
// handful of mistagged duplicates (a real surname tagged ADV, for instance)
// that a POS-only filter misses; a capitalization check is robust to that.
function eligible(row) {
  if (!row || row.pos === "PROPN" || row.lemma.length < MIN_LEN) return false;
  const first = row.lemma[0];
  return first === first.toLowerCase();
}

// Walk forward from `offset` within the band (wrapping) for the first
// not-yet-used, eligible row. `spoken` holds every lemma STRING already
// asked as a real item or already used as a pseudoword source, in any band:
// the seed carries a few spellings at two ranks (тож as a conjunction at
// 1,331 and as a particle at 6,651), and a rank-only guard let v1.1.0 build
// the pseudoword таж from the first while asking тож itself as a real item
// from the second, so one answer leaked another.
function walkBand(rows, bandStart, offset, usedRanks, spoken) {
  for (let step = 0; step < BAND_SIZE; step++) {
    const absRank = bandStart + ((offset + step) % BAND_SIZE);
    if (usedRanks.has(absRank)) continue;
    const row = rows[absRank - 1];
    if (!eligible(row) || spoken.has(row.lemma.toLowerCase())) continue;
    return { rank: absRank, lemma: row.lemma, pos: row.pos };
  }
  return null;
}

// Deterministic seeded shuffle (mulberry32). Fixed seed so the committed
// presentation order re-derives byte for byte from a fresh build.
function mulberry32(seed) {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle(arr, seed) {
  const rand = mulberry32(seed);
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Build the full 120-item bank (60 real, 60 pseudoword) from the committed
// thread-01 seed. Network-free and deterministic.
export function buildVocabTest() {
  const seed = readSeed();
  const rows = seed.rows;
  const allLemmas = new Set(rows.map((r) => r.lemma.toLowerCase()));
  const lexicon = loadLexicon();
  const usedRanks = new Set();
  const usedForms = new Set();
  const spoken = new Set(); // lemma strings that are a real item or a pseudoword source
  const unordered = [];

  for (let band = 1; band <= BAND_COUNT; band++) {
    const bandStart = (band - 1) * BAND_SIZE + 1;

    for (let i = 0; i < REAL_PER_BAND; i++) {
      const picked = walkBand(rows, bandStart, REAL_OFFSETS[i], usedRanks, spoken);
      if (!picked) throw new Error(`band ${band}: no eligible real lemma near offset ${REAL_OFFSETS[i]}`);
      usedRanks.add(picked.rank);
      usedForms.add(picked.lemma.toLowerCase());
      spoken.add(picked.lemma.toLowerCase());
      unordered.push({ id: `b${band}r${i + 1}`, form: picked.lemma, isReal: true, band, rank: picked.rank });
    }

    for (let i = 0; i < PSEUDO_PER_BAND; i++) {
      let offset = PSEUDO_START_OFFSETS[i];
      let built = null;
      for (let attempt = 0; attempt < BAND_SIZE && !built; attempt++) {
        const picked = walkBand(rows, bandStart, offset, usedRanks, spoken);
        if (!picked) throw new Error(`band ${band}: pseudoword source exhausted near offset ${PSEUDO_START_OFFSETS[i]}`);
        usedRanks.add(picked.rank);
        spoken.add(picked.lemma.toLowerCase());
        // Try every substitution position on this source lemma, closest to
        // the middle first, before giving up on it and moving to the next
        // candidate lemma in the band.
        for (const pseudo of pseudowordCandidates(picked.lemma)) {
          const key = pseudo.toLowerCase();
          if (allLemmas.has(key) || usedForms.has(key) || lexicon.has(key)) continue;
          usedForms.add(key);
          built = { id: `b${band}p${i + 1}`, form: pseudo, isReal: false, band, sourceRank: picked.rank, sourceLemma: picked.lemma };
          break;
        }
        offset = picked.rank - bandStart + 1; // resume just past the rejected candidate
      }
      if (!built) throw new Error(`band ${band}: could not construct a non-colliding pseudoword near offset ${PSEUDO_START_OFFSETS[i]}`);
      unordered.push(built);
    }
  }

  return shuffle(unordered, SHUFFLE_SEED);
}
