# B1 extension: the Wiktionary derived-term family graph (source)

The open fallback for the one PULS ask with no public route yet. The profile
groups its vocabulary into about 1,100 word families and verifies levels
within them (eLex 2025, section 3.5.2), but the families are "to be added in
future updates" on the platform (section 4.4) and are not exported. This
graph builds the same kind of grouping from what IS open: the English
Wiktionary's Ukrainian entries, as extracted by kaikki.org (wiktextract).

- Input: the full kaikki.org Ukrainian dump (`kaikki.org-dictionary-Ukrainian.jsonl`,
  Last-Modified 2026-10-30, 53,277 Ukrainian headwords, not committed: 323 MB;
  the first snapshot read the 2026-09-09 and 2026-09-20 extractions). Every
  edge is taken verbatim from an entry; no family is inferred from spelling.
- Edges used for families: `derived` (headword A lists B under Derived
  terms), `affix` (B's etymology is one affix claim over exactly one
  full-word base A: an `{{af}}`-family template, or since 2026-11-20 an
  `:af` segment of the unified `{{ety}}` template Wiktionary migrated most
  Ukrainian etymologies to; a part's inline modifiers such as `<t:bank>` are
  dropped before it is read, where they used to drop the part), `aspect` (B is A's listed perfective or imperfective
  partner). `related` (Related terms) is recorded in `edges.csv` and NOT
  used: on this dump it chains unrelated roots through shared suffixes and
  cognate lists into families of hundreds.
- Node filter: one Cyrillic token of three or more letters, stress stripped,
  apostrophes normalized; reconstructions, bare affixes, Latin and multiword
  entries are out. An affix base Wiktionary knows only as a function word is
  out, so вгору does not chain every в- word into one family.
- Compound nodes are excluded from the used edges, on purpose: Wiktionary
  lists a compound under both of its roots (високий and оплачувати both list
  високооплачуваний), and one such node would merge two nests. A node is a
  compound when its etymology names two or more full-word bases, or when two
  headwords with different stems both list it as derived while it carries
  both stems.
- A family is a connected component of the used edges. Only families that
  touch the top-12,000 list are kept; ids are assigned in order of the
  family's lowest-ranked list member, and that member is the family's
  `root` label (a handle, not an etymological claim).
- Beside each list member the artifacts carry its validated level from the
  PULS overlay (by permission). The level is reported, never used to shape
  the graph; the "same level" statistic is a finding about the profile, not a
  property the graph was built to have.

Outputs: `wiktionary-families.json` (every family that touches the list, all
its Wiktionary members, the list members with rank / POS / level, the
aggregates), the public `wiktionary-families/families.csv` and `edges.csv`,
and the browser tier `src/lib/ukrainian-frequency/wiktionary-families.data.mjs`.
The gap-fill model reads the JSON at `--snapshot` time (family size,
membership, and the family's lowest validated level computed fold-safe) and
folds the family into its group-aware split.

Reproduce: `npm run uk-freq:wikt-families -- --dump <kaikki jsonl> --dump-date <yyyy-mm-dd>`
(under four seconds). Licenses: Wiktionary CC-BY-SA 3.0, redistributed
with attribution; levels PULS by permission, CC BY-NC-SA 4.0 (the authors'
decision of 2026-09-24), so the table is CC-BY-NC-SA-4.0 as a whole and
CC-BY-SA without the level column. No em-dashes.
