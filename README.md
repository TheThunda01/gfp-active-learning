# GFP active learning

**Can a model choose which existing brightness measurements to reveal next and learn more efficiently than random sampling?** This repository turns that question into a small, reproducible benchmark with an answer that depends on the evaluation set.

The data come from the measured green fluorescent protein landscape of [Sarkisyan et al. (2016)](https://doi.org/10.1038/nature17995). Every sequence and label already existed before this project. The program hides and reveals stored measurements; it does not design proteins, run experiments, or recommend sequences for testing.

Start with the short [project context](docs/project-context.md) or the [biology and concepts guide](docs/biology-and-concepts.md), then the [methods](docs/methods.md). The [data provenance](docs/data-provenance.md) explains how the original phenotype was matched to TAPE sequence records. [Related tools](docs/related-tools.md) connects this compact implementation to larger research projects; [references](docs/references.md) collects the scientific sources.

## What this project demonstrates

- Traceable scientific data preparation, checksums, and separate code/data licenses.
- A label-access boundary, seeded acquisition policies, and explicit pool/test separation.
- Simple sequence descriptors, random-forest regression, and a diversity-aware acquisition heuristic.
- Repeated-seed learning curves, paired comparisons, and tests against hidden-label leakage.
- Careful interpretation when a promising local result does not extend to more mutated sequences.

The pool has 2,400 observations. Two fixed evaluation sets contain 400 nearby and 800 more mutated sequences. Their labels never enter training or acquisition. Each policy starts from the same 64 observations within a seed and reaches 384 revealed labels. Four seeds compare uniform random selection with tree-disagreement screening followed by sequence-diversity selection.

## What happened in the included run

At 384 revealed labels, lower root mean squared error (RMSE) is better:

| Evaluation set | Random RMSE, mean ± SD | Uncertainty + diversity RMSE, mean ± SD |
| --- | ---: | ---: |
| Local, ≤3 source substitutions | 0.7715 ± 0.0096 | 0.7570 ± 0.0162 |
| More mutated, ≥4 source substitutions | 1.1651 ± 0.0632 | 1.1799 ± 0.0406 |

Units are the source's log-brightness scale. SD describes variation across four seeds on the same data; it is not a confidence interval or biological replication. The heuristic's small average local advantage did not carry over to the more mutated set. This is a descriptive result from one frozen subset and one deliberately simple model, not proof that either policy is generally better.

![Learning curves](results/learning_curves.png)

The dashed reference uses every pool label with the same model family. It is contextual, not a guaranteed upper bound. The evaluation sequences remain related to the pool: the median nearest-pool distance is two residues locally and four in the more mutated set. These are not tests on unseen protein families.

## Run it

Python 3.12 is used in CI. The included 1.3 MB CSV makes the analysis offline after dependency installation; no account, API key, GPU, or model download is needed.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m gfp_active_learning --output-dir reproduced-results
python scripts/check_reproduction.py results reproduced-results
```

The full benchmark takes well under two minutes on the development CPU. It writes six CSV tables, a run manifest, a plot, and a short [results report](results/report.md). The reproduction check uses strict input hashes and tolerant numeric comparisons; it does not require identical PNG bytes across platforms.

To rebuild the subset from the two pinned public source downloads:

```bash
python scripts/prepare_data.py --download --output rebuilt-data
```

This optional step verifies source and archive-member checksums before matching records. Normal analysis does not download anything. Remove `rebuilt-data` after checking it if you do not want a second data copy.

## Read the results with these limits in mind

Cell-based GFP fluorescence depends on expression, folding, and maturation as well as the protein's photophysical properties. It is not a direct measurement of intrinsic molecular brightness or a general enzyme-activity label. The model uses residue composition and mutation count, so it discards position-specific information. Its tree disagreement is a ranking heuristic, not calibrated uncertainty. The fixed measured pool omits prospective assay failures, changing experimental conditions, and unobserved sequence space.

The scientific starting points are [Sarkisyan et al.](https://doi.org/10.1038/nature17995), [TAPE](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html), and [Greenman et al.'s uncertainty benchmark](https://doi.org/10.1371/journal.pcbi.1012639). This is an independent educational implementation, not a reproduction of their model results. Code is [MIT licensed](LICENSE); the adapted scientific data retain [CC BY 4.0 attribution](DATA_LICENSE.md).
