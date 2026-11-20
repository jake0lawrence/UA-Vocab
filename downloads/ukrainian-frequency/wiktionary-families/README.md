# Ukrainian Frequency: the Wiktionary derived-term family graph

The open fallback for the Ukrainian Vocabulary Profile's word families, which
the profile uses to verify levels but has not published. A derivational
family graph over the [Ukrainian Frequency](https://uavocab.org/research)
top-12,000 list, built from the English Wiktionary's Ukrainian entries
(kaikki.org extraction dated 2026-10-30). Snapshot 2026-11-20.

## This snapshot (2026-11-20)

Rebuilt from the 2026-10-30 extraction, replacing the snapshot of 2026-09-12
(extraction 2026-09-20). Two things changed, one upstream and one here:

- **Wiktionary moved its etymologies to a new template.** Most Ukrainian
  entries now write their etymology with the unified `{{ety}}` template
  (`{{ety|uk|:af|банк|-івський}}`) instead of `{{af}}`. The extractor read
  only the old templates, so on the new extraction it would have lost about
  550 of the 2,452 affix edges it had. It now reads an `:af` segment of
  `{{ety}}` exactly as it reads `{{af}}`.
- **A base carrying an inline modifier is now read.** Wiktionary writes a
  gloss or gender on a part (`банк<t:bank><g:m>`); the extractor used to drop
  such a part as not a word, and with it the edge. It now drops the modifier
  and keeps the word. A part in another language (`fr:...`) is still not a
  Ukrainian base.

Together: affix edges 2,452 to 14,110, words in the graph 18,522 to 28,704,
list lemmas in a family 4,171 to 7,259 of 12,000, families touching the list
1,919 to 2,848, largest family 108 to 143 members.

**Known limitation, older than this snapshot.** A compound that Wiktionary
lists as derived under both of its roots but whose second root does not share
the first four letters with it (лиходій under лихо and діяти) is not caught
as a compound, and joins two nests. The largest such chain (лише, лихо, дія,
чин, зло) had 38 members in the September snapshot and has 112 in this one.

## families.csv

One row per family member. Columns
`family_id,root,family_size,lemma,on_list,rank,pos,validated_level`.

- `family_id` is stable within a snapshot and assigned in order of the
  family's lowest-ranked list member, which is also its `root` label (a
  handle, not an etymological claim). `family_size` counts every Wiktionary
  member, on the list or not.
- `on_list` says whether the member is one of the 12,000 list lemmas; only
  those rows carry `rank`, `pos` and `validated_level` (the PULS overlay's
  A1 to C1 level, by permission, blank where the profile has none). A list
  lemma with two parts of speech gets two rows.

## edges.csv

Every edge that touches a family member, with its type:
`source,target,edge_type,used_for_families`.

- `derived`: `source` lists `target` under Derived terms.
- `affix`: `source`'s etymology is one affix template over the single
  full-word base `target`.
- `aspect`: `target` is `source`'s listed perfective or imperfective partner.
- `related`: `source` lists `target` under Related terms. Recorded for
  completeness and marked `used_for_families = no`, because on this dump it
  chains unrelated roots into families of hundreds.

A family is a connected component of the `yes` edges over non-compound
nodes. Compounds are excluded because Wiktionary lists them under both roots
(високий and оплачувати both list високооплачуваний), so one compound would
merge two families. Nodes are single Cyrillic tokens of three or more
letters, stress stripped; affix bases known only as function words are
dropped.

## The finding

Among the families with two or more validated members (920 in this
snapshot), the profile places every member at the same level in about a fifth
(192), one level apart in 324, and two or more apart in 404; the mean spread
is 1.53 levels. The September snapshot, which saw fewer affix edges, read
about a third (219 of 640, mean spread 1.14): the larger families that the
fuller reading finds are also more spread out. A family is not a level,
which is the eLex 2025 paper's own point (писати at A1, its family spread
across the levels). The gap-fill model therefore uses a family's lowest
validated level as one feature, computed fold-safe, rather than copying it.

## License

CC-BY-NC-SA 4.0 as a whole. Edges and members from the English Wiktionary via
kaikki.org (CC-BY-SA 3.0, attributed), CC-BY-SA on their own without the level
column. Validated levels from PULS (Synchak, O., Starko, V., Burak, M., Svystun, M.), by
permission, CC BY-NC-SA 4.0 at the authors' decision (2026-09-24). Cite the
profile as: Профіль української лексики (ПУЛЬС) / О. Синчак, В. Старко, М. Бурак, М. Свистун та ін. Львів: Школа української мови та культури УКУ, 2026. Rebuild with
`scripts/ukrainian-frequency/extract-wiktionary-families.py`.

## Where it fits

Join the `on_list = yes` rows to `../v0.1.0/lemmas.csv` on `rank`. The
`validated_level` column echoes `../validated-cefr/lemmas.csv`.

The gap-fill model in `../predicted-cefr/` reads the family size, membership
and lowest validated level as one ablation step (it adds nothing measurable)
and uses the families to group its cross-validation folds, so related words
never straddle train and test. It reads the graph only when it is retrained;
the published predicted levels were trained on the September snapshot and are
unchanged by this one. The graph is also the evidence behind the open
request to the profile's authors for their own word families.
