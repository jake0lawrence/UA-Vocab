# B1 extension, stage 4: the gap-fill model (sources)

- `predicted-cefr.snapshot.json`: the two label-independent inputs the model
  needs beyond thread 01's seed and the validated overlay. `partners`: the
  Wiktionary-listed aspect partners of every VERB lemma on the list (kaikki.org
  wiktextract, CC-BY-SA 3.0). `lexicon`: for every list lemma, whether the
  VESUM lexicon (via pymorphy3-dicts-uk) knows it, whether its normal form is
  the lemma, and whether the part of speech agrees. The lexicon map is
  VESUM-derived, regenerable with `--snapshot`, and not part of the public
  release; the public files carry only the out-of-scope class it feeds.
  `resources`: per list lemma, the open feature sources the feature-resource
  inventory found buildable now: Wiktionary sense count and a "borrowed"
  category flag (kaikki.org wiktextract, CC-BY-SA), wordfreq's Zipf frequency
  (subtitles, web and books; MIT code over CC-BY-SA data), the UniMorph 4.0
  derivational family from `ukr.derivations` (6,650 edges, union-find; the
  UniMorph release is CC BY-NC 4.0 with the Wiktionary-derived part CC-BY-SA
  3.0, so the family ids are a modeling input, regenerable, not redistributed
  as data), membership in the Borodin A1 and A2 lexical minima
  (CC-BY-4.0, already committed on this surface; computed and reported as
  `excludedFeatures`, never in the shipped model since 2026-09-13, because
  the flags were a graded word list read back as a feature, firing on most
  validated A1 labels and on almost none of the lemmas being predicted, and
  their independence from the profile's textbook base is not established),
  and the Wiktionary
  derived-term family from `wiktionary-families.json` (see
  `wiktionary-families.SOURCE.md`: derived terms, single-base affix
  etymologies and aspect partners over non-compound nodes; joined by rank, so
  homographs stay apart; CC-BY-SA).
- `predicted-cefr.json` and `src/lib/ukrainian-frequency/predicted-cefr.data.mjs`:
  the predictions, the grouped held-out evaluation, the ablation ladder, the
  calibration table and the per-band support; `public/downloads/ukrainian-frequency/predicted-cefr/`
  the public CSVs (`predictions.csv`, `held-out.csv`). The derived JSON does
  not repeat the held-out rows; `held-out.csv` is the record.

Training labels: the validated overlay (`puls-cefr.json`, PULS by
permission). Frequency features: the seed's counts and document counts
(UberText 2.0, CC-BY). The model is pure numpy; the seed is fixed.

Rules the artifacts hold: predictions are never merged into the validated
overlay (the test asserts the validated artifacts carry no prediction and
that no predicted rank is a validated one); every headline metric recomputes
from `held-out.csv`; Stage A (out of scope) is a rule, not a learned
classifier, because no out-of-scope labels exist.

Reproduce: `scripts/ukrainian-frequency/gapfill-model.py --snapshot --kaikki
<verb jsonl> --kaikki-lemmas <all-POS jsonl for the list lemmas> --unimorph
<ukr.derivations> --wiktionary-families src/data/ukrainian-frequency/wiktionary-families.json`;
without `--snapshot` it trains, evaluates and predicts from the committed
snapshot (about six minutes on one CPU; rerun it after any change to
`puls-cefr.json`, since the labels are read from there at run time).

## License

CC-BY-NC-SA-4.0. The model is trained on the validated PULS overlay, which the
profile's authors license CC BY-NC-SA 4.0 (decided 2026-09-24), and the owner's
decision of the same day is that predictions over those labels carry the
profile's terms rather than argue whether a model's output is adapted material.
The predictions are ours, never the profile's, and never enter the validated
overlay.
