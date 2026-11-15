# 1000 i 1 slovo (A2) joined onto the Ukrainian frequency list

The "1000 i 1 slovo" A2 lexical minimum for Ukrainian as a foreign
language (Kseniia Borodin and Olesia Lazarenko; Europa-Universitat Viadrina
Frankfurt (Oder), 2026; https://doi.org/10.11584/opus4-1448), joined onto the
uavocab.org/research top-12,000 lemma frequency list
(UberText 2.0, lang-uk).

lemmas.csv: one row per published entry, verbatim. The entry text, whether it
is a word or phrase entry, whether the same authors' A1 minimum already claims
it, and, where a headword matches a lemma on the frequency list, the frequency
rank, lemma, POS, and the validated PULS CEFR level where one exists (Synchak
et al. 2025, by permission).

The minimum carries no part of speech, so the join is by spelling: `rank`,
`lemma` and `pos` are the spelling's most frequent reading on the list, and
`puls_level` is the EASIEST level the profile gives any reading of that
spelling. The two could belong to different readings (the A1 volume has
such rows); in this volume every puls_level matches the validated level of
its own rank. For a per-reading level, join `rank` to
validated-cefr/lemmas.csv.

themes.csv: the book's own thematic dictionary, one row per topic heading, with
how much of that semantic field the frequency list reaches. `words` counts
every unit under the heading; `matched` the units that reach the list;
`off_list` the single-word units that do not. A phrase unit that does not
match is in neither, so matched + off_list can be less than words, and
`off_list_pct` is off_list over all words (phrases included).

Where it fits: this is the syllabus side of the A2 comparison. `in_a1`
measures the step from the A1 volume (../borodin-a1/): how many entries are
carried over and how much deeper in the corpus the new ones sit. themes.csv
shows which semantic fields a news-heavy frequency list misses, and
../genre-split/ tests that directly by looking up every word entry here in
same-size fiction and news lists. ../minimums-crosswalk/ classifies every
disagreement between the two volumes and the whole validated profile; the
text profiler offers it as a known-word set; the ukvocab Python package
ships it; and its multiword entries are the phrase rows of
../b1-extension/multiword.csv.

License: CC-BY-4.0 (the publication's own license). Attribute:
Borodin, K. and Lazarenko, O., "1000 i 1 slovo. Leksychnyi minimum z
ukrainskoi movy (A2). Navchalnyi posibnyk". Europa-Universitat Viadrina
Frankfurt (Oder), 2026. DOI 10.11584/opus4-1448. Frequency ranks CC-BY-4.0
(UberText 2.0, lang-uk); PULS levels CC-BY-NC-SA-4.0 by the authors' permission.

Snapshot: 2026-07-28
