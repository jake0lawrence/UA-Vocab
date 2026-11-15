# The genre split: fiction against news, same size, same pipeline

Every word entry of the "1000 i 1 slovo" A2 lexical minimum (Borodin and
Lazarenko, CC-BY-4.0, https://doi.org/10.11584/opus4-1448) looked up in two
frequency lists built from the fiction and news subcorpora of UberText 2.0
(lang-uk, https://lang.org.ua/en/ubertext/), each capped to the same token
count and lemmatized by the same tool.

entries.csv: one row per word entry of the A2 minimum (phrase entries are
left out). Columns `entry,fiction_rank,news_rank,only`. `entry` is the
published entry, verbatim; `only` is `news` or `fiction` when exactly one
genre's top 12,000 reaches the entry, blank when both or neither do.

`themes.csv`: one row per topic heading of the A2 book that has word entries.
Columns `theme,units,news,fiction,news_pct,fiction_pct,delta_pct`: the units
under the heading, how many each genre reaches, those as percentages, and
`delta_pct`, fiction minus news (positive where fiction reaches more).

A blank rank means the entry is outside that genre's top 12,000.

These ranks are NOT comparable to the main Ukrainian Frequency
list, which lang-uk's own lemmatizer produced over the combined
corpus. They are comparable only to each other.

Where it fits: ../borodin-a2/ found that a large share of the A2 minimum does
not rank on the main list, which is built mostly from news. This split holds
genre as the only variable and finds that fiction and news reach about the
same amount of the minimum but different parts of it (news: institutional and
geographic words; fiction: domestic and bodily ones), so the gap is mostly a
genre effect. Shown as thread 6 of the research page. Nothing joins on these
ranks, by design; a test keeps them apart from the thread-01 ranks.

License: the entries are the Borodin and Lazarenko A2 minimum (CC-BY-4.0);
the ranks derive from UberText 2.0 (lang-uk, CC-BY-4.0). Attribute both.

Tokens per genre: 85,552,190
Snapshot: 2026-07-28
