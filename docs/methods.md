# Methods and interpretation

## Fixed data roles

The [preparation script](../scripts/prepare_data.py) uses original Sarkisyan labels and Tasks Assessing Protein Embeddings (TAPE) sequences/split membership. It checks full-source and archive-member SHA-256 hashes, reconstructs **recorded** source genotypes for matching, and verifies TAPE's rounded label within `1e-6` of the original value. Records with shorter sequence strings are excluded; no padding or speculative alignment is introduced. Details and exclusion counts are in [provenance](data-provenance.md).

Full-length train and validation records are pooled, sorted by `SHA256("gfp-active-learning-v1|" + sequence)`, and assigned in order: 2,400 to the acquisition pool and 400 to local evaluation. Original TAPE test records are sorted separately and the first 800 form the distant evaluation set. This subset selection does not inspect phenotype values. It creates a new small benchmark; it is not the original TAPE benchmark score.

Pool/local records have at most three source-reported substitutions and distant records have ≥4. A full-sequence hash is unique across roles. `distance_audit.csv` reports minimum aligned Hamming mismatch counts from each evaluation sequence to the entire pool. Local minimum/median/maximum are 1/2/3 residues; distant values are 2/4/10. The mutation-count boundary does not impose a minimum between-set sequence distance.

## Features and fixed regression model

Features are 20 residue fractions followed by source reference-relative mutation count. No feature is estimated from brightness labels; no scaling is required for the chosen trees. Residue composition is deliberately lossy and positional Hamming distance is used only for acquisition/diversity auditing.

The model is scikit-learn `RandomForestRegressor` with 64 trees, maximum depth 10, minimum leaf size 2, all features eligible at each split, bootstrap sampling, and `n_jobs=1`. Other settings are stored in `run_metadata.json`. A simulation fit uses `random_state = seed + label_budget`; the all-pool reference uses 2026. These settings are fixed implementation choices, not the result of a hyperparameter search using the evaluation sets. No claim is made that they are optimal.

## Acquisition policy

Four seeds (11, 29, 47, 83) each define a 64-record uniformly sampled initial labeled set shared by both policies. Budgets are 64, 128, 192, 256, and 384. A separate seeded acquisition random-number generator (RNG) uses `seed + 10000`.

1. Fit only on currently acquired pool labels.
2. Evaluate the fitted model on the two fixed evaluation sets for reporting. These metrics are not arguments to acquisition.
3. For random acquisition, sample the next batch uniformly without replacement.
4. For the uncertainty/diversity policy, calculate the standard deviation of individual-tree predictions for remaining pool records. Rank by this heuristic, with seeded random tie-breaking, and retain up to four times the requested batch size.
5. Within that shortlist, greedily choose the sequence with greatest minimum Hamming distance to the labeled set and the already chosen batch. Break ties by higher tree disagreement, then the shortlist's order.
6. Reveal only the chosen stored labels through the `PoolOracle`, the interface that permits access only to acquired labels. This is a programming boundary, not protection against deliberately inspecting the public source file. Refit from scratch at the next budget.

This hybrid is not ordinary pure uncertainty sampling, a formal optimal-design method, or calibrated Bayesian optimization. It favors diversity only within an uncertainty-screened shortlist. It does not assume a Gaussian predictive distribution, and its tree spread is never converted into a confidence level.

## Evaluation and uncertainty

For each seed/budget/policy/evaluation set, report root mean squared error (RMSE), mean absolute error (MAE), and Spearman rank correlation, which compares prediction and outcome ranks. Constant outcomes or predictions give an undefined rank correlation (`None`/empty CSV field), not an invented zero. Learning curves display means and one sample standard deviation (SD) across four acquisition seeds (`ddof=1`). Paired final-budget RMSE differences subtract the random score from the heuristic score within each seed. These are descriptive comparisons on shared outcomes, not four independent scientific studies or a significance test.

One all-pool-label fit supplies context for the same model family. It is neither a mathematical upper bound nor a fair label-budget competitor. Lower uncertainty or additional labels need not improve every observed score monotonically.

The evaluation sets are excluded from training and acquisition, but their metrics are now visible in this public repository. Treat future changes prompted by these results as development against an observed benchmark; they would need a fresh evaluation design for a confirmatory claim. This run does not establish performance for new protein families, different assays, or prospective experiments.

## Reproducibility checks

Tests reject malformed sequences, duplicated records, nonfinite labels, broken hashes, invalid data roles, and illegal oracle queries. Synthetic counterfactual tests alter evaluation outcomes or only never-acquired pool labels and require acquisition histories to stay identical. Hand-calculated feature/distance/metric tests check numerical semantics. The same seed must reproduce the same small simulation.

CI reruns the full benchmark and compares six CSVs with exact categorical values and numeric tolerance `rtol=1e-6, atol=1e-7`. The tolerance allows harmless floating-point variation, not arbitrary result drift. Input bytes and source hashes must match exactly. PNG bytes and library patch-version strings are not numerical scientific results and are not forced to match byte-for-byte.

The [assumption register](assumptions.md) explains why the subset sizes, budgets, model settings and four-times shortlist were chosen, what has been checked, and what remains an untested design choice. The [glossary](glossary.md) defines the terms used here.

## Scientific basis

- [Sarkisyan et al., Nature (2016)](https://doi.org/10.1038/nature17995): original GFP landscape and measurement context.
- [Rao et al., NeurIPS (2019)](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html): TAPE data/task provenance and evaluation context.
- [Greenman, Amini, and Yang, PLOS Computational Biology (2025)](https://doi.org/10.1371/journal.pcbi.1012639): direct benchmark evidence that uncertainty and acquisition methods vary across tasks. This implementation is not their model or a reproduction of their results.
- [Official scikit-learn random forest documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html): estimator semantics and parameter definitions.


## Final-budget prediction cross-check (round 2)

`python -m gfp_active_learning.predictions export` refits only the eight final-budget models from the verified saved acquisition history, preserving its row order and `seed + 384` model seeds. It uses the same declared forest and descriptors; it does not rerun acquisition or select additional records. The gzip CSV has 9,600 rows: 1,200 evaluation observations × four seeds × two policies. Each row records seed, policy, budget, evaluation role, source record ID and prediction. It deliberately omits copied true labels; the verifier joins them from the fingerprinted source table.

`python -m gfp_active_learning.predictions verify` checks source/result hashes and complete, unique role-correct prediction keys. It computes RMSE and MAE directly from errors and computes Spearman correlation as the correlation of independently constructed average-tie ranks; it does not call the benchmark's scoring function or SciPy's `spearmanr`. Constant ranks remain undefined. Sixteen reconstructed metric rows must agree with the saved final-budget rows under relative tolerance `1e-8` or absolute tolerance `1e-10`.

The gzip is limited to 4,000,000 bytes before and after decompression. A valid but numerically discrepant export returns status 1; malformed input, changed fingerprints or unsupported keys return status 2. Verification writes `recomputed_metrics.csv` and `verification.json` beside the export, replacing prior verification files; a failed input check may leave an older report, so the command's exit status matters. The manifest fingerprints the prediction bytes and the exact acquisition/metric/configuration files. These unsigned fingerprints establish consistency, not trusted authorship. This check verifies numerical reporting for the saved experiment, not calibration, biological validity or new-family generalization.
