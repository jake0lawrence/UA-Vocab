# Ukrainian Frequency: the Wiktionary derived-term family graph

The open fallback for the Ukrainian Vocabulary Profile's word families, which
the profile uses to verify levels but has not published. A derivational
family graph over the [Ukrainian Frequency](https://uavocab.org/research)
top-12,000 list, built from the English Wiktionary's Ukrainian entries
(kaikki.org extraction dated 2026-09-09). Snapshot 2026-09-12.

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

Among the families with two or more validated members, the profile places
every member at the same level in about a third. A family is not a level,
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
never straddle train and test. The graph is also the evidence behind the open
request to the profile's authors for their own word families.
