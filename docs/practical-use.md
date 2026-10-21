# Practical use

## Where this fits

This is a small retrospective benchmark (a comparison using existing observations) for checking how data acquisition—choosing which labels to reveal—affects prediction on already measured green fluorescent protein (GFP) records. The saved-run audit is useful when reviewing a local run, receiving result files from someone else or checking that a figure was built from a coherent experiment record. It checks the published contract without fitting another model.

## Input and output contract

```bash
python -m gfp_active_learning.audit --data-dir data --results-dir results --out run-audit.json
```

The input directory must contain the checksum-verified dataset and manifest. The result directory must contain `run_metadata.json` and the six CSV files from the standard benchmark. The audit expects the current four seeds, two policies, five budgets and forest configuration. A changed protocol needs deliberate changes to the contract; it should not pass as the original experiment.

The command checks all query identities and labels against pool records, duplicate acquisitions, batch sizes, seeded initial sets, evaluation counts, complete metric keys, recomputed means and sample standard deviations (SDs), paired differences, reference counts and sequence distances. It returns a JSON report with counts, checks and SHA-256 hashes of the reviewed result files. Exit status 2 means a check failed. An output path that would replace an input is refused. With no `--out`, the JSON is printed only.

The final-prediction commands provide a stronger numerical check: `python -m gfp_active_learning.predictions export --directory PATH` writes a compressed CSV and manifest, refitting only the eight already-defined final models; `verify --directory PATH` independently reconstructs the 16 final metric rows from source outcomes. Both return 0 on agreement, 1 on numerical disagreement, and 2 on input/format failures. Verification replaces its two report files in that directory.

## Worked use case

Reproduce the fixed experiment into a new directory, compare it to the baseline, then audit its internal consistency:

```bash
python -m gfp_active_learning --output-dir reproduced-results
python scripts/check_reproduction.py results reproduced-results
python -m gfp_active_learning.audit --results-dir reproduced-results --out reproduced-results/audit.json
python -m gfp_active_learning.predictions export --results-dir reproduced-results --directory final-predictions
python -m gfp_active_learning.predictions verify --results-dir reproduced-results --directory final-predictions
```

The included [example audit](../examples/run-audit.json) passes with 3,072 queried rows, 80 metric rows, 20 aggregate rows and eight paired comparisons. Each policy acquires 384 unique pool observations for each seed. The policies share the exact seeded initial set. This supports traceability of the run, not a conclusion that either policy will work better in a laboratory.

The comparison script and audit answer different questions. Comparison checks agreement with recorded numerical outputs, allowing small floating-point differences. The audit recalculates structural and arithmetic invariants from the supplied records and verified source. The new final-prediction export now supplies per-observation evidence for independently reconstructing final-budget metrics. Full benchmark reproduction remains necessary for checking earlier budgets and acquisition.

## Checks before relying on a result

- Verify the input and run configuration match the intended protocol before interpreting the curve.
- Inspect both evaluation sets and paired differences, including unfavorable seeds.
- Read the source phenotype as cellular log-brightness, not intrinsic molecular brightness or a universally transferable protein property.
- Retain the audit report with the reviewed files; changing files afterward requires another audit.

These are operator responsibilities. The software cannot establish that a person avoided viewing public outcomes, that an unknown implementation hid labels, or that a biological measurement is valid. Existing counterfactual tests check that changing hidden labels does not change acquisition in this implementation.

The [glossary](glossary.md) defines file and statistical terms; the [assumption register](assumptions.md) explains the fixed protocol and what its checks cannot establish.

## Known limits

A consistent artifact set can still come from a poor model. Aggregate metrics can be internally consistent while predictions are wrong. The saved-run audit itself does not reconstruct predictions; use the separate final-prediction verifier for the final budget. Earlier-budget predictions are not exported. It checks the current fixed experiment, not arbitrary externally configured runs. The related-sequence split, four shared-data seeds, coarse descriptors and uncalibrated tree disagreement remain unchanged.

## Next improvements

1. **Extended verification coverage:** final-budget predictions and independent metrics are now implemented. Add selected earlier checkpoints only if justified; accept when all requested checkpoints have complete identity checks without silently changing the benchmark.
2. **Protocol versioning:** define a machine-readable configuration rather than hard-coded defaults; accept when incompatible configurations fail clearly and each report records a schema/version.
3. **Additional fixed subsets:** predeclare several label-blind subset seeds; accept when results include all subsets and the original baseline remains separately reproducible.
4. **Calibration evaluation:** assess a clearly defined uncertainty estimator only after separating development from evaluation; accept when calibration metrics and acquisition outcomes are reported together, including failures.
