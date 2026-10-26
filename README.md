# GFP active learning

GFP means green fluorescent protein, a protein used as a light-emitting biological reporter.

**Can a model choose which existing brightness measurements to reveal next and learn more efficiently than random sampling?** This small, reproducible benchmark tests that question on two evaluation sets. In the included run, the selection heuristic slightly reduced average error on nearby sequences but increased it on more mutated sequences.

## Why this project

The data come from the measured green fluorescent protein landscape of [Sarkisyan et al. (2016)](https://doi.org/10.1038/nature17995). Every sequence and label already existed before this project. The program hides and reveals stored measurements; it does not design proteins, run experiments, or recommend sequences for testing.

## What it does

- Traces data preparation through checksums and separate code/data licenses.
- Separates the acquisition pool from evaluation sets and reveals labels only when a policy selects them.
- Fits random-forest regressors to simple sequence descriptors and compares random sampling with a diversity-aware acquisition heuristic.
- Reports learning curves and paired comparisons across seeds, with tests against hidden-label leakage.
- Reports both favorable and unfavorable results across evaluation sets.

The pool has 2,400 observations. Two fixed evaluation sets contain 400 nearby and 800 more mutated sequences. Their labels never enter training or acquisition. Each policy starts from the same 64 observations within a seed and reaches 384 revealed labels. Four seeds compare uniform random selection with tree-disagreement screening followed by sequence-diversity selection.

An independent saved-run audit checks query identities, source labels, budgets, paired initial sets, aggregate statistics and sequence-distance summaries without training another model.

## Quick start

CI uses Python 3.12. The included 1.3 MB CSV lets the analysis run offline after dependency installation. It requires no account, application programming interface (API) key, graphics processing unit (GPU), or model download.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m gfp_active_learning --output-dir reproduced-results
python scripts/check_reproduction.py results reproduced-results
```

The recorded development run took under two minutes on a central processing unit (CPU); runtime depends on the machine and environment. It writes six CSV tables, a run manifest, a plot, and a short [results report](results/report.md). The reproduction check uses strict input hashes and tolerant numeric comparisons; it does not require identical PNG bytes across platforms.

To rebuild the subset from the two pinned public source downloads:

```bash
python scripts/prepare_data.py --download --output rebuilt-data
```

This optional step verifies source and archive-member checksums before matching records. Normal analysis does not download anything. Remove `rebuilt-data` after checking it if you do not want a second data copy.

Audit the saved run (failure returns a nonzero exit status):

```bash
python -m gfp_active_learning.audit --results-dir results --out run-audit.json
```

Export final-budget predictions and check their metrics independently:

```bash
python -m gfp_active_learning.predictions export --results-dir reproduced-results --directory reproduced-results/final-predictions
python -m gfp_active_learning.predictions verify --results-dir reproduced-results --directory reproduced-results/final-predictions
```

These commands use the reproduced run and write its prediction bundle under `reproduced-results/`. Export replaces prediction files at the specified destination; verification replaces its two report files. Choose a separate directory for each run to retain earlier bundles and the checked-in example.

## Example results

At 384 revealed labels, lower root mean squared error (RMSE) is better:

| Evaluation set | Random RMSE, mean ± SD | Uncertainty + diversity RMSE, mean ± SD |
| --- | ---: | ---: |
| Local, ≤3 source substitutions | 0.7715 ± 0.0096 | 0.7570 ± 0.0162 |
| More mutated, ≥4 source substitutions | 1.1651 ± 0.0632 | 1.1799 ± 0.0406 |

Errors use the source's log-brightness scale. Standard deviation (SD) describes variation across four seeds on the same data; it is not a confidence interval or biological replication. The heuristic's small average local advantage did not carry over to the more mutated set. This result describes one frozen subset and one simple model; it does not show that either policy is generally better.

![Learning curves](results/learning_curves.png)

The dashed reference uses every pool label with the same model family. It is contextual, not a guaranteed upper bound. The evaluation sequences remain related to the pool: the median nearest-pool distance is two residues locally and four in the more mutated set. These are not tests on unseen protein families.

The [example audit](examples/run-audit.json) verifies 3,072 acquisitions, 80 metric rows, 20 aggregate rows and eight paired differences. It checks that the saved records meet the fixed contract; it does not establish biological validity or prove that humans were blinded.

The [final-prediction check](examples/final-predictions/verification.json) joins 9,600 exported predictions to source labels and independently reproduces all 16 final-budget metric rows. Only the final budget is exported; earlier trajectories are unchanged.

A separate [four-policy ablation](experiments/uncertainty_ablation/README.md) isolates uncertainty-only, diversity-only, and combined selection against random with the same starts, budgets and model. Diversity-only had the lowest distant-set mean RMSE; uncertainty-only had the lowest local-set mean. The recorded prediction that combined would help most at distance was not supported in this exploratory reuse of the historical subset. The original results above remain unchanged.

## Practical use and limitations

Cell-based GFP fluorescence depends on expression (protein production), folding into a three-dimensional structure, and maturation of its light-emitting group, as well as the protein's photophysical properties ([Sarkisyan et al., 2016](https://doi.org/10.1038/nature17995); [Balleza et al., 2018](https://doi.org/10.1038/nmeth.4509)). It does not directly measure intrinsic molecular brightness or general enzyme activity.

The model uses residue composition and mutation count, discarding position-specific information. Its tree disagreement ranks candidates but does not quantify calibrated uncertainty. The fixed measured pool omits prospective assay failures, changing experimental conditions, and unobserved sequence space.

The scientific starting points are [Sarkisyan et al.](https://doi.org/10.1038/nature17995), [TAPE](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html), and [Greenman et al.'s uncertainty benchmark](https://doi.org/10.1371/journal.pcbi.1012639). This is an independent educational implementation, not a reproduction of their model results. Code is [MIT licensed](LICENSE); the adapted scientific data retain [CC BY 4.0 attribution](DATA_LICENSE.md).

## Documentation

| Guide | What you will find |
| --- | --- |
| [Project context](docs/project-context.md) | Motivation and main themes |
| [Biology and concepts](docs/biology-and-concepts.md) | GFP phenotype and the learning problem |
| [Methods](docs/methods.md) | Features, policies, metrics and limits |
| [Glossary](docs/glossary.md) | Biological, statistical and software vocabulary |
| [Assumptions](docs/assumptions.md) | Design choices, rationales, checks and consequences |
| [Reference audit](docs/reference-audit.json) and [review record](docs/review-2026-10-20.md) | Verified source coverage and corrections |
| [Maintenance review, 21 October 2026](docs/review-2026-10-21.md) | Current source checks, reproduction and remaining work |
| [References](docs/references.md) | Scientific sources |
| [Data provenance](docs/data-provenance.md) | Exact source matching, splits and exclusions |
| [Practical use](docs/practical-use.md) | Audit contract and worked example |
| [Literature review](docs/literature-review.md) | Documented search and appraisal |
| [Related tools](docs/related-tools.md) | Independent tools and conceptual relationships |

## Development and reuse

Run the tests, reproduce the benchmark and compare the outputs before changing the model or policies. The audit is designed for the current fixed seeds, budgets, descriptors and model configuration. A deliberate protocol change needs a new evaluation plan and updated tests. See [CONTRIBUTING.md](CONTRIBUTING.md). No external analysis code was copied.
