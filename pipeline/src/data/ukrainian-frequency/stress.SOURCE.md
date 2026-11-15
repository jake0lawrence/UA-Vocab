# Word stress source (thread 07)

The thread-07 artifacts (`stress.json`, `stress-overrides.json`,
`stress-adjudication.json` here; the generated
`src/lib/ukrainian-frequency/stress.data.mjs`; and the public release at
`public/downloads/ukrainian-frequency/stress/<version>/`) are DERIVED. The
snapshot is the artifact of record: a reviewed per-lemma stress column over
list v0.2.0, imported on 2026-10-01 from the handover of the session that
built it, and rebuilt from the open sources by
`scripts/ukrainian-frequency/extract-stress.py`.

## What it is

For each of the 12,000 (lemma, UD part of speech) rows of the list: the
primary stressed form (combining acute U+0301), the accepted variants with the
primary first, a status that says how the row was resolved, a note, and the
provenance of the chosen stress. 10,785 of the 11,090 polysyllabic lemmas carry
one confident stress (97.2 percent); 248 are labeled (free variant, homograph,
dictionary-only doublet, variable name); 57 are missing, 36 of them proper
nouns; 910 are monosyllables.

## Why it exists

Ukrainian stress is free and mobile and nothing in the spelling says where it
falls. A learner working from the list meets 12,000 headwords with no way to say
them, and stress is the gap users of the list asked about most. The prompt was
an email from Andrij Rudnitsky, who pointed at the lang-uk stress dictionary as
the source.

## Sources and licenses

- **ukrainian-word-stress 2.1.0** (lang-uk: Oleksiy Syvokon, maintained by Dmytro Chaplynskyi), MIT.
  https://github.com/lang-uk/ukrainian-word-stress. The baseline. Read directly
  from its trie (`_load_dictionary`, `_trie_value`, `_parse_dictionary_value`),
  never through its stanza tagger; readings are filtered by the list's own UD
  part of speech and lemma features (Case=Nom, VerbForm=Inf). Installed with
  `pip install --no-deps ukrainian-word-stress marisa-trie`, which skips the
  several-GB torch/stanza dependency the library declares.
- **en.wiktionary** via kaikki.org (wiktextract JSONL, about 300 MB) and
  **uk.wiktionary** (the pages-articles dump, about 16 MB; the API returns 429
  to shared addresses). Wiktionary content CC-BY-SA 3.0.
- **uk.wikipedia** lead sentences, CC-BY-SA 4.0, for proper nouns nothing else
  covers; the article title is recorded per row.
- **goroh.pp.ua**, consulted for 19 tiebreaks, one reference lookup per word.
  Only the attested stress position is recorded; no content is copied. Not an
  open license, which is why its reach is kept small, counted, and every such
  row is a manual decision in `stress-overrides.json`.

**The column is CC-BY-SA 4.0** because of the Wiktionary-derived rows. It is
published as its own file joined on rank, not as a column on `lemmas.csv`, so
the CC-BY list (and its Zenodo deposit) is not relicensed.

## The nine stages

1. Monosyllables: no mark.
2. The dictionary, POS-filtered. Covered 97.4 percent of polysyllabic lemmas.
   Reading the trie by part of speech caught 18 cases where the library's
   stanza guess on a bare lemma picked the wrong homograph (брати́ for the verb
   бра́ти); the list is in `stress-adjudication.json` (`stanzaVsPosDictionary`).
3. en.wiktionary: separates a true free variant (one entry, "X or Y") from a
   homograph (separate entries) from a minor variant (every sense archaic, dated
   or dialectal); fills lemmas the dictionary lacks; cross-checks the singles
   (8,001 agree, 35 disagree: `libraryVsEnWiktionary`).
4. uk.wiktionary: the stress in each entry's headword line, independent of
   en.wiktionary.
5. The vote: the dictionary (one voice however it was read), en.wikt, uk.wikt;
   two of three decide. Every flagged lemma and every vote is in
   `stress-adjudication.json` (`log`, 199 rows).
6. Rules for conflicts that only look like conflicts: en.wikt marks every part
   of a compound where the dictionary marks the main stress; doubled acutes in
   Wiktionary data; a stanza guess against the POS-filtered lookup loses.
7. goroh.pp.ua tiebreaks for the conflicts left over (19 rows cite it).
8. Rules for lemmas no source covers: standard spelling (проект as проє́кт),
   compounds (stress on the last component), acronyms (final syllable), -енко
   surnames.
9. uk.wikipedia leads for the proper nouns still missing (resumable; the
   session stopped at 27 of 173 because the shared address was throttled, and
   the pass was finished on 2026-10-01: 116 names stressed, 111 one way and 5
   with variants; two results with the mark on a consonant, Н́іколас and
   Коб́олєв, refused and left missing).

Every manual decision (27 rows) is in `stress-overrides.json` and is applied
LAST by the pure builder, so a rebuilt pipeline reproduces it, and the test
refuses any goroh-backed row that changes without an entry there.

## The import of 2026-10-01

The handover's reviewed CSV was converted to `stress.json` with four
normalizations, each verifiable:

1. **Replay of stage 2.** The POS-filtered dictionary stage was re-run here over
   all 12,000 lemmas (the library installed without stanza) and reproduced every
   `dictionary` / `dictionary_pos` row except 39. 22 are rows where the trie is
   ambiguous for the lemma's part of speech, or has no reading for it, and the
   library's context model chose: retagged **`library_context`** (not
   reproducible from the trie alone). 17 are hyphenated compounds the trie has
   no single entry for, which the library's own compound handling stressed:
   retagged **`compound`**, joining the 8 rows the handover already tagged so.
   The handover's 10,349 + 23 + 8 = 10,380 rows are relabeled, not recounted.
2. **Primary first.** `stress_variants` is reordered so the primary stress is
   the first variant (the handover column kept the source's order).
3. **Either-stress forms split.** Two hyphenless rows carried two acutes in one
   form, en.wiktionary's either-stress notation (за́три́мка, по́місни́й); they are
   split into single-accent variants and labeled.
4. **Marks.** NFC; combining acute only; a doubled acute collapses; a grave
   (secondary stress) never appears in the primary form. A mark that does not
   sit on a vowel (Н́іколас, a typo a Wikipedia lead can carry) is refused.

## Honesty limits (all surfaced on the page)

- **Homograph primaries are corpus-verified only where the spelling can tell
  the readings apart.** Where the two readings' paradigms differ somewhere
  (прохо́дити's проходитиме against проходи́ти's проходіть) the primary is the
  reading whose distinguishing forms occur more in UberText 2.0, with the count
  on the row (`homograph_corpus`); where they are spelled alike in every cell
  (о́рган / орга́н) the primary is still the first en.wiktionary entry and the
  note says it is unverified. See `stress-homographs.SOURCE.md`.
- **No source wins by default.** en.wiktionary was wrong against goroh on
  по́каз, нульови́й, побажа́ння and казко́вий; the dictionary was wrong twice
  (йо́го for його́ at rank 40, підозрюва́тися for підо́зрюватися). Both upstream
  errors are corrected by override and queued in
  `contrib/ukrainian-word-stress/issues.md`.
- **The paradigms file disagrees in 18 headwords.** Read against thread 04's
  verbatim Wiktionary forms, 13 headwords inherit a wrong stress from
  en.wiktionary (`paradigmCorrections`, goroh- or dictionary-backed) and 5 are
  open. The paradigms file is NOT patched (it is a verbatim mirror the next dump
  would overwrite); the disagreements ship beside the column with a verdict per
  row, and the test holds the set as a ratchet.
- **A Wikipedia search can return a different bearer of a name** (Філіп came
  from "Філіп II"); the article title is kept per row so it can be audited.

## Owner decisions (2026-10-01)

- **Proper nouns are out of scope.** The builder's `scopeProperNouns` step runs
  after the overrides and the row validation: every PROPN row keeps the
  pipeline's stress, its pipeline status moves to the note, its status becomes
  `proper_noun`, and the headline shares are read over the 9,920 polysyllabic
  common words. The snapshot itself is unchanged, so the pipeline's statuses
  for names are still there to audit.
- **Dictionary-only doublets are settled from a printed source**, Погрібний's
  orthoepic dictionary, not goroh. `doublets.csv` in the release is the
  worklist; each lookup becomes an `adjudicated` override citing the page, and
  `LEDGERED_SOURCES` in the builder refuses a row that cites goroh or Pohribnyi
  without a ledger entry.
- **Homographs are counted in UberText 2.0** where their readings differ in
  spelling (`count-homographs.py`, `stress-homographs.json`,
  `stress-homographs.SOURCE.md`), after the site's own lemmatizer strikes every
  distinguishing form that is also another word's; readings spelled alike in
  every form stay labeled with the first en.wiktionary entry as primary.

## Reproduction run (2026-10-02)

`extract-stress.py --check --names --library-context` was run from the dumps
(kaikki.org Ukrainian JSONL, 300 MB; the uk.wiktionary pages-articles dump,
16 MB; ukrainian-word-stress 2.1.0 with stanza and its `uk` model for the
context pass; uk.wikipedia live for the names, 139 lookups cached) against
this snapshot. Result: every in-scope primary stress re-derives except
півде́нно-за́хідний, a compound whose side (en.wiktionary's full form or the
dictionary's main stress) depends on the library's stanza tagger; 14 rows
differ only where the manual ledger settles them; 6 proper-noun rows differ
(out of scope, reported); 201 in-scope rows keep their stress under a truer
provenance label, 140 of them `dictionary` rows the rebuild calls
`dictionary_pos`. The
fixes the run needed in the ported stages are in the extractor's history;
`docs/ukrainian-frequency/stress-column.md` has the reading.

## Open tasks

- Settle the compound convention for v1.0.1 (en.wiktionary's full form
  wherever it exists; four rows change notation, none changes main stress)
  and carry the rebuild's provenance labels into the snapshot.

## Reproduce

```bash
pip install --no-deps ukrainian-word-stress marisa-trie
pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install stanza   # --library-context only
python3 -c "import stanza; stanza.download('uk')"
python3 scripts/ukrainian-frequency/extract-stress.py \
  --kaikki kaikki.org-dictionary-Ukrainian.jsonl \
  --ukwikt ukwiktionary-latest-pages-articles.xml.bz2 \
  --names --library-context --check      # diff against the committed snapshot; names are throttled, cache in build/ukwiki-names.json
npm run uk-freq:build-stress              # freeze the release + browser tier (no network)
npm run uk-freq:check-stress              # it re-derives byte for byte (CI runs the vitest twin)
```
