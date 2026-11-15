// ============================================================
// UKRAINIAN FREQUENCY : the lexical-minimum crosswalk. Pure builder.
//
// Ukrainian now has two independent answers to "which words come first", built
// by different methods, and nobody had put them side by side:
//
//   the MINIMUMS  "1000 i 1 slovo" A1 (Borodin and Turkevych) and A2 (Borodin
//                 and Lazarenko). Expert selection over GRAK and Ukrainian Web
//                 2022 frequency, weighted by usefulness at the learning stage.
//                 A teaching syllabus: about 2,000 words, in two volumes.
//   the PROFILE   the Ukrainian Vocabulary Profile on PULS (Synchak, Starko,
//                 Burak, Svystun), the one corpus-VALIDATED CEFR profile for
//                 Ukrainian. A descriptive map: 10,194 lemma strings, A1 to C1,
//                 the level being the ONSET of the lexeme's earliest sense.
//
// This crosswalks them on the thread-01 frequency spine and classifies every
// disagreement. It is not a scoring of either. They answer different questions,
// and the interesting rows are exactly the ones where a syllabus and a
// descriptive profile part company.
//
// WHAT MAKES A ROW COMPARABLE. Both sides are joined by lemma string, folded
// for the pedagogical stress accent and for the four apostrophe glyphs the
// sources disagree about. Two consequences the caller must carry into any
// claim:
//   - NO PART OF SPEECH ON THE MINIMUM SIDE. The published lists carry none, so
//     homographs collapse (то as particle and as conjunction are one row).
//   - ONSET, NOT SENSE. A profile level is the earliest sense of the lexeme. A
//     word can be validated A1 for a basic sense while a minimum teaches a
//     different one. A string crosswalk cannot see that, and never claims to.
//
// EVERY WORD OF AN ENTRY COUNTS. The minimums' unit is the published entry
// line, which can name several words: an aspect pair, a gender pair, a spelling
// variant set. Membership is per headword, so "в, у" puts both in A1.
//
// House rule: no em-dashes.
// ============================================================

export const LEVELS = ["A1", "A2", "B1", "B2", "C1"];
export const LEVEL_ORDER = { A1: 1, A2: 2, B1: 3, B2: 4, C1: 5, C2: 6 };
export const VOLUMES = ["A1", "A2"];

// Every class a crosswalk row can fall into. `beyond` is the expected mass (a
// 2,000-word syllabus cannot carry a 10,000-word profile) and is reported so
// the table's marginals close, never as a finding.
export const CLASSES = {
  agree: "the volume and the validated level are the same",
  earlier: "the minimum teaches it earlier than the profile validates it",
  later: "the minimum teaches it later than the profile validates it",
  absent: "validated A1 or A2, and neither volume carries it",
  beyond: "validated B1 or higher and outside the minimums, as expected",
  unprofiled: "in a volume, and the profile does not cover it",
};

const APOS = /['ʼʹ`´‘′’]/g;

// A correct reader for the committed PULS snapshot. 67 of its rows quote a
// lemma field that contains a comma ("u, v" at A1 among them), so a naive split
// shifts every column after it and silently relabels the level. Handles quoted
// fields and doubled quotes; that is all this dialect uses.
export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  const src = String(text).replace(/\r\n?/g, "\n");
  for (let i = 0; i < src.length; i += 1) {
    const c = src[i];
    if (quoted) {
      if (c === '"') {
        if (src[i + 1] === '"') { field += '"'; i += 1; } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  if (!rows.length) return [];
  const header = rows[0];
  return rows.slice(1).filter((r) => r.length === header.length).map((r) => Object.fromEntries(header.map((h, i) => [h, r[i]])));
}

// Fold what the sources spell differently and nothing else: the combining
// stress accent U+0301 (pedagogical, never lexical) and the apostrophe, in
// every glyph and in the one encoding. The PULS harvest kept the platform's
// HTML entity verbatim, so 135 of its rows spell the apostrophe "&#39;"
// (sim&#39;ia, im&#39;ia); decoding it here is what lets those lemmas join at
// all. No Ukrainian lemma legitimately contains that sequence.
export function fold(s) {
  return String(s || "")
    .replace(/&#0*39;|&apos;|&quot;/g, "’")
    .normalize("NFD")
    .replace(/́/g, "")
    .normalize("NFC")
    .replace(APOS, "’")
    .toLowerCase()
    .trim();
}

// The authors' own separators inside one entry line. An en dash separates an
// aspect pair only when spaced; a bare hyphen stays inside a word
// (po-ukrainsky). "=" marks a synonym pair, the negated equals an antonym pair.
const SEP = /\s*(?:\/|,|;|=|≠|\s–\s)\s*/;
const GRAMMAR_NOTES = new Set(["док.", "недок.", "…", "..."]);

const clean = (p) => String(p || "").trim().replace(/^[!?.…\s]+|[!?.…\s]+$/g, "").trim();

// Every single-word headword an entry names, main text and parentheses alike.
//
// The authors distinguish two uses of a parenthesis by the space in front of
// it, and the distinction is exact across both volumes (A1: 47 spaced, 0
// unspaced; A2: 3 spaced, 19 unspaced).
//   SPACED    a separate word: a variant ("vpered (upered)"), or the lemma
//             behind a phrase ("Shcho stalosia? (Statysia)"). It is a headword.
//   UNSPACED  a continuation of the word it touches: the reflexive particle in
//             "vmyvaty(sia)", the plural imperative in "Buvai(te)!". It is NOT
//             a headword on its own, it is half of one. Reading it as a word
//             put "te" (rank 27) into the A2 volume off "Buvai(te)!". So the
//             base and the joined form are both emitted and the fragment never
//             is: "vmyvaty(sia)" gives vmyvaty and vmyvatysia.
export function headwords(entry) {
  const src = String(entry);
  const spaced = [...src.matchAll(/(^|\s)\(([^)]*)\)/g)].map((m) => m[2]);
  const joined = [];
  for (const m of src.matchAll(/(\S+?)\(([^)]*)\)/g)) {
    const stem = clean(m[1]);
    if (stem && !stem.includes(" ")) joined.push(stem + m[2]);
  }
  // Inside a spaced parenthesis the authors separate ALTERNATIVES with a
  // semicolon and PARADIGM FORMS with a comma: "ity (yty; idy! idit!)" offers
  // yty as a second infinitive, "mii (moia, moie, moi)" merely declines the
  // headword. So a semicolon group holding one bare word is a headword and a
  // comma list never is. All 18 multi-piece parentheticals in the two volumes
  // are paradigms or collocations; only yty is a real alternative.
  const fromParens = [];
  for (const group of spaced) {
    for (const part of group.split(";")) {
      const w = clean(part);
      if (w && !w.includes(",") && !w.includes(" ") && !GRAMMAR_NOTES.has(w)) fromParens.push(w);
    }
  }
  const main = src.replace(/\([^)]*\)/g, " ");
  const pieces = [...main.split(SEP).map(clean).filter(Boolean), ...joined, ...fromParens];
  const out = [];
  for (const p of pieces) {
    if (p.includes(" ")) continue;
    const w = fold(p);
    if (w && !out.includes(w)) out.push(w);
  }
  return out;
}

// A covered headword plausibly built on the same root. Three cheap tests, from
// strongest to weakest. This is a FALSE-POSITIVE FILTER on the absent list, not
// a morphological claim: it over-matches on purpose (zakryty is flagged against
// zakrychaty) so that what survives unflagged is conservative.
export function relativeOf(lemma, covered, familiesByLemma) {
  for (const fam of familiesByLemma.get(lemma) || []) {
    for (const m of fam) {
      const w = fold(m);
      if (w !== lemma && covered.has(w)) return { relative: w, via: "family" };
    }
  }
  if (lemma.length >= 5) {
    for (const c of covered) {
      if (c.length >= 5 && c !== lemma && (c.includes(lemma) || lemma.includes(c))) {
        return { relative: c, via: "contains" };
      }
    }
  }
  let best = null;
  for (const c of covered) {
    let n = 0;
    while (n < lemma.length && n < c.length && lemma[n] === c[n]) n += 1;
    if (n >= 5 && n >= Math.min(lemma.length, c.length) - 4 && (!best || n > best.n)) best = { c, n };
  }
  return best ? { relative: best.c, via: "stem" } : null;
}

function classify(volume, level) {
  if (!level) return volume ? "unprofiled" : null;
  if (!volume) return level === "A1" || level === "A2" ? "absent" : "beyond";
  if (volume === level) return "agree";
  return LEVEL_ORDER[volume] < LEVEL_ORDER[level] ? "earlier" : "later";
}

// ------------------------------------------------------------
// Build. Inputs are parsed committed files; nothing here touches disk.
//   seed:      ubertext-lemmas-top12k.json ({ rows: [{lemma,pos,count}] })
//   a1raw/a2raw: borodin-*.raw.json ({ entries: [string] })
//   pulsRaw:   rows of puls-cefr.raw.csv ([{lemma, level, pos_uk}]), the WHOLE
//              validated profile, not the top-12000 slice, so a minimum word
//              off the frequency list can still be compared
//   families:  wiktionary-families.json ({ families: [{members: [string]}] })
// ------------------------------------------------------------
export function buildCrosswalk({ seed, a1raw, a2raw, pulsRaw, families }) {
  const rank = new Map();
  const pos = new Map();
  seed.rows.forEach((r, i) => {
    const k = fold(r.lemma);
    if (!rank.has(k)) {
      rank.set(k, i + 1);
      pos.set(k, r.pos);
    }
  });

  // The profile's onset level per lemma string. A PULS entry can list variants
  // in one field ("kozhnyi, kozhen"); each is its own string.
  const puls = new Map();
  for (const r of pulsRaw) {
    for (const piece of String(r.lemma).split(/\s*,\s*/)) {
      const k = fold(piece);
      if (!k || !LEVEL_ORDER[r.level]) continue;
      const cur = puls.get(k);
      if (!cur || LEVEL_ORDER[r.level] < LEVEL_ORDER[cur]) puls.set(k, r.level);
    }
  }

  // Volume membership per headword, keeping the entry line it came from. A word
  // in both volumes belongs to the earlier one.
  const member = new Map();
  // Words that appear only inside a multi-word entry ("tomu" in "bo = tomu
  // shcho"). The volume does not list them as words, so they are not members,
  // but a reader has met them, so an absent row says so rather than implying
  // the word is unseen.
  const inPhrase = new Map();
  const readVolume = (raw, volume) => {
    const entries = [...new Set(raw.entries)];
    for (const e of entries) {
      for (const w of headwords(e)) {
        if (!member.has(w)) member.set(w, { volume, entry: e });
      }
      for (const piece of e.replace(/\([^)]*\)/g, " ").split(SEP)) {
        const p = clean(piece);
        if (!p.includes(" ")) continue;
        for (const part of p.split(/\s+/)) {
          const w = fold(clean(part));
          if (w && !inPhrase.has(w)) inPhrase.set(w, e);
        }
      }
    }
    return entries.length;
  };
  const a1Entries = readVolume(a1raw, "A1");
  const a2Entries = readVolume(a2raw, "A2");

  const familiesByLemma = new Map();
  for (const f of families.families) {
    for (const m of f.members) {
      const k = fold(m);
      if (!familiesByLemma.has(k)) familiesByLemma.set(k, []);
      familiesByLemma.get(k).push(f.members);
    }
  }
  const covered = new Set(member.keys());

  const universe = [...new Set([...member.keys(), ...puls.keys()])];
  const rows = [];
  for (const lemma of universe) {
    const m = member.get(lemma) || null;
    const level = puls.get(lemma) || null;
    const cls = classify(m ? m.volume : null, level);
    if (!cls) continue;
    const row = {
      lemma,
      rank: rank.get(lemma) ?? null,
      pos: pos.get(lemma) ?? null,
      volume: m ? m.volume : null,
      entry: m ? m.entry : null,
      level,
      class: cls,
      relative: null,
      relativeVia: null,
    };
    if (cls === "absent") {
      if (inPhrase.has(lemma)) {
        row.relative = inPhrase.get(lemma);
        row.relativeVia = "phrase";
      } else {
        const rel = relativeOf(lemma, covered, familiesByLemma);
        if (rel) {
          row.relative = rel.relative;
          row.relativeVia = rel.via;
        }
      }
    }
    rows.push(row);
  }
  // On the frequency spine first, then the words the corpus never reached.
  rows.sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity) || a.lemma.localeCompare(b.lemma, "uk"));

  const table = {};
  for (const v of [...VOLUMES, "none"]) {
    table[v] = {};
    for (const l of [...LEVELS, "none"]) table[v][l] = 0;
  }
  const byClass = {};
  for (const k of Object.keys(CLASSES)) byClass[k] = 0;
  for (const r of rows) {
    table[r.volume || "none"][r.level || "none"] += 1;
    byClass[r.class] += 1;
  }

  const pick = (fn) => rows.filter(fn).map(({ lemma, rank: rk, pos: p, volume, entry, level, relative, relativeVia }) =>
    ({ lemma, rank: rk, pos: p, volume, entry, level, relative, relativeVia }));

  return {
    rows,
    counts: {
      universe: rows.length,
      a1Entries,
      a2Entries,
      a1Headwords: rows.filter((r) => r.volume === "A1").length,
      a2Headwords: rows.filter((r) => r.volume === "A2").length,
      inBothVolumes: [...member.keys()].length,
      profileLemmas: puls.size,
      onFrequencyList: rows.filter((r) => r.rank != null).length,
      table,
      byClass,
      // The three sets a next edition would actually read.
      laterAtA1: pick((r) => r.class === "later" && r.level === "A1").length,
      absentA1: pick((r) => r.class === "absent" && r.level === "A1").length,
      absentA2: pick((r) => r.class === "absent" && r.level === "A2").length,
      absentA1NoRelative: pick((r) => r.class === "absent" && r.level === "A1" && !r.relative).length,
      absentA2NoRelative: pick((r) => r.class === "absent" && r.level === "A2" && !r.relative).length,
      // absent rows a volume does reach, but only inside a multi-word entry
      absentInPhrase: rows.filter((r) => r.relativeVia === "phrase").length,
    },
    sets: {
      later: pick((r) => r.class === "later"),
      absentA1: pick((r) => r.class === "absent" && r.level === "A1"),
      absentA2: pick((r) => r.class === "absent" && r.level === "A2"),
      earlier: pick((r) => r.class === "earlier"),
      unprofiled: pick((r) => r.class === "unprofiled"),
    },
  };
}

export const CSV_COLUMNS = ["lemma", "rank", "pos", "volume", "entry", "validatedLevel", "class", "relative", "relativeVia"];

// Neutralize the four characters a spreadsheet reads as a formula. Same rule
// the rest of this surface's CSV exports use.
const cell = (v) => {
  const s = v == null ? "" : String(v);
  const safe = /^[=+\-@]/.test(s) ? `'${s}` : s;
  return /[",\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
};

export function crosswalkCsv(rows) {
  const out = [CSV_COLUMNS.join(",")];
  for (const r of rows) {
    out.push([r.lemma, r.rank ?? "", r.pos ?? "", r.volume ?? "", r.entry ?? "", r.level ?? "", r.class, r.relative ?? "", r.relativeVia ?? ""].map(cell).join(","));
  }
  return `${out.join("\n")}\n`;
}
