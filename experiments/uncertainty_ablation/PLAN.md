# GFP acquisition-component ablation: fixed plan

Written on **21 October 2026 before running the ablation**. This is a plan for an exploratory extension of an already observed public benchmark, not a new blind holdout or a formal preregistration.

## Learning checkpoint

The user's prediction is: **the combined policy will help most on more-distant variants**. No reason was supplied; none is inferred here. We will inspect the direction of the results and explain which acquisition components appear useful under this fixed model.

## Fixed comparison

Keep the historical subset and descriptors unchanged: 2,400 pool records, 400 local-test records and 800 distant-test records; 20 residue fractions plus source mutation count; the existing 64-tree random forest, depth 10, leaf size 2. Use seeds **11, 29, 47, 83**, budgets **64, 128, 192, 256, 384**, and the original `seed + budget` forest seed. All four policies share the exact same randomly selected initial 64 records within each seed.

1. **random:** unchanged uniform sampling without replacement.
2. **uncertainty_only:** rank all remaining pool records by the standard deviation of tree predictions; take the next batch directly, with seeded random ties. No diversity step.
3. **diversity_only:** greedily maximize minimum aligned Hamming distance to labeled records and the current batch across the entire remaining pool. Seeded random ties; no uncertainty screening or score.
4. **combined:** call the original uncertainty/diversity policy unchanged: screen to four times the batch size by tree disagreement, then select for Hamming diversity within that shortlist.

Random and combined must reproduce their historical acquisition paths and metrics within existing numeric tolerances. No model, representation, distance, shortlist multiplier, seed or budget will be chosen from the new outcomes.

## Outcomes and sign conventions

Primary descriptive outcome: **distant-test RMSE at 384 labels**, with all four policy means, sample SDs and per-seed results shown. Assess whether combined has the smallest mean on this set; also show each seed rather than declaring a general winner.

To examine whether combined helps more at distance, calculate within each seed:

`[(RMSE_random − RMSE_combined)_distant − (RMSE_random − RMSE_combined)_local]`.

Positive values indicate a larger absolute RMSE reduction on the distant set; negative values indicate a smaller reduction or larger harm there. This compares absolute changes on the source log-brightness scale, not standardized task difficulty. Report the mean and each seed. Report all pairwise policy-minus-random final RMSE differences as context.

Secondary outcomes, fixed in advance: complete matched-budget RMSE/MAE/Spearman learning curves; final-policy acquisition overlap; and the Spearman association between tree disagreement and absolute prediction error **separately for every policy × seed × budget × evaluation role**. Constant spread or error gives an undefined association. Final-budget per-record predictions and spread support inspection; these associations are not uncertainty calibration or confidence-interval coverage.

## Leakage and reproducibility boundaries

Only acquired pool labels can fit a model. Evaluation labels are used only after fitting for outcome calculation; neither acquisition function accepts evaluation outcomes. Persist the complete query history with source record IDs, source roles/split fingerprints, the plan hash, model settings and input/code hashes. Initial-set equality, budget adherence, no repeated acquisitions, and invariance to evaluation-label changes will be checked.

The pool and both evaluation sets are historical and related. The original random/combined outcomes were already visible before this plan; adding policies does not restore blinding. Four repeated acquisition seeds on the same fixed outcomes are descriptive repetitions, not independent biological studies. No significance test, confidence interval, prospective experiment, new sequence generation, or general claim that combined is best will be made.

## Deliverables

Keep original code and `results/` unchanged. Add an isolated module under `experiments/uncertainty_ablation/`, runnable with `python -m experiments.uncertainty_ablation`. Save its outputs only in that experiment's `results/`: all learning curves and histories, paired contrasts, overlap/uncertainty diagnostics, final predictions, plot, manifest, and a plain-language interpretation. Preserve the original files' starting fingerprints in `baseline_files.json`.
