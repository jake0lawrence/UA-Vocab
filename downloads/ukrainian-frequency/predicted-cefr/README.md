# Ukrainian Frequency: predicted CEFR levels (the gap-fill model)

**These are predictions, not validated levels.** They ship in this directory,
separate from the validated overlay (`../validated-cefr/`), and are never
merged into it. Treat every row as a candidate for the profile's authors.

`predictions.csv` covers the 5,597 lemmas of the top-12,000 list that the
validated PULS map does not label. Columns
`rank,lemma,pos,scope,predicted_level,probability,models_agree,abstain,thin_support,uncertain,note`.

- `scope`: `predicted`, or one of the out-of-scope classes the model does not
  touch: proper nouns, function words, and lemmas the lexicon does not know.
  PULS labels no proper nouns and stops at C1, so these are ruled out first.
- `predicted_level` (A1 to C1) and `probability` are the shipped model's, a
  proportional-odds ordinal logistic regression. A predicted C1 is noted as
  "C1 or beyond".
- `abstain`: the probability is below the abstention threshold, chosen as the
  lowest tested confidence at which held-out exact accuracy reaches 50 percent.
  `models_agree`: the multinomial challenger predicts the same level.
  `uncertain` is either flag. `thin_support`: the lemma sits in a rank band
  where fewer than 35 percent of lemmas carry a validated label.

`held-out.csv` is the evaluation itself: every validated lemma with its level,
its fold and group, and the out-of-fold prediction of every model, so the
metrics on the page recompute from this file.

## How it was evaluated

Five-fold cross-validation on the 6,403 validated labels, GROUPED: lemmas that
share a derivational stem, an aspect-pair link, a spelling, a UniMorph
derivational family or a Wiktionary derived-term family never straddle train
and test (3,394 groups). Metrics, grouped folds, shipped model: exact match
40.0 percent, within one level 82.3 percent, macro-F1 0.313, MAE 0.806,
quadratic weighted kappa 0.479. Baselines on the same folds: majority class
34.0 / 71.0, rank band only 34.6 / 70.9, frequency only 37.7 / 76.6. Under
plain random folds the shipped model scores 41.5 / 83.4; the gap is reported
as the size of the leakage a naive split would hide. Expected calibration
error 0.019. The eight-step ablation ladder in the JSON and on the page reports
each feature block separately; of the open resources, Wiktionary polysemy
adds nothing, wordfreq frequency 0.9 points, UniMorph families 0.2, and the
Wiktionary derived-term family (size, membership, fold-safe lowest validated
level) nothing at all: 40.2 to 40.0 exact, inside fold noise. The family
graph itself is the deliverable (`../wiktionary-families/`); the reason it
cannot lift the model is measured beside it: among families with two or more
validated members the profile places every member at one level in only a
third.

The list this model is trained against is v0.2.0. Its seed carries no document
count, so the two document-frequency features the earlier model had
(log document frequency, documents per occurrence) are gone and the ladder is
eight steps rather than nine; the retrained model is republished with its own
figures rather than carried from the v0.1.0 run (which read 40.2 / 82.9 on
6,391 labels).

**One feature is computed, reported and deliberately not shipped.** Until
2026-09-13 the model also carried membership in the open A1 and A2 lexical
minima (Borodin et al.), its two strongest weights, and read 49.4 percent
exact. On the current labels and folds those two flags would give 49.2 / 92.2,
a 9.2-point lift; the JSON keeps that number under `excludedFeatures`. It is
out because the lift was a graded word list read back as a feature: the flags
fire on 1,501 of the 6,403 labels (most of validated A1) but on only 84 of the
lemmas the model exists to predict, and whether those volumes sit among the
textbooks the profile was validated on could not be established. The honest
model is the one shipped here; it beats the rank-band baseline by 5.5 points
of exact match and 11.4 within one, which is the size of what frequency and
form can say about a level for Ukrainian with the open resources that exist.

The ablation ladder, per-band label presence and accuracy, the confusion
matrix and the calibration table are in
`src/data/ukrainian-frequency/predicted-cefr.json` and on the page.

## Features

Log frequency (UberText 2.0), rank band, part of speech, length, syllables, suffix and prefix
indicators, reflexive and apostrophe flags, lexicon membership (VESUM via
pymorphy3), the derivational family's lowest validated level and the aspect
partner's validated level (both computed from the training fold only), and
the open resources: Wiktionary sense count and borrowed-term flag, wordfreq
Zipf frequency, UniMorph 4.0 derivational family size, and the Wiktionary
derived-term family: its size, membership, and its lowest validated level
(training fold only). Membership in the open A1 and A2 lexical minima is
computed and reported, never shipped (above). The ablation ladder on the
page reports what each block buys.

## What this cannot do

The labels are missing not at random (they come from textbooks), the list is
censored at rank 12,000, and the strongest feature of the French template
(per-level frequencies from a graded learner corpus) does not exist for
Ukrainian. The v0.2.0 seed carries no document count, so no dispersion feature exists. No LLM
judgment is used.

## License

CC-BY-NC-SA 4.0. The model is trained on the validated overlay (PULS,
Synchak, O., Starko, V., Burak, M., Svystun, M., by permission, CC BY-NC-SA 4.0 at
the authors' decision), so the predictions carry its terms; ranks from UberText
2.0 (lang-uk, CC-BY). The predictions are ours, never the profile's.

## Where it fits

There is no `lemmas.csv` in this folder: the per-lemma table is
`predictions.csv`. With `../validated-cefr/lemmas.csv` it accounts for every
one of the 12,000 list lemmas: a validated level there, or a prediction or a
stated out-of-scope reason here. Join both to `../v0.1.0/lemmas.csv` on `rank`.

For levels you can act on, keep the rows with `scope = predicted` and
`uncertain = no` (1,750 in this snapshot, nearly all B2 and C1). Everything
else is a candidate for the profile's authors, not a label.

Shown in the B1 extension section of the research page. Deliberately not used
by the text profiler, which counts validated levels only, and not shipped in the
`ukvocab` package. The excluded minima feature is the subject of the site's
erratum post on the leak.
