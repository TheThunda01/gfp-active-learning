# Glossary

This guide defines the technical vocabulary used in the README, methods, data records and policy ablation. Definitions describe this project’s use of the terms; they do not turn a computational result into biological evidence.

## Biology and measurements

| Term | Meaning here |
| --- | --- |
| GFP / avGFP | Green fluorescent protein; avGFP refers to the protein from *Aequorea victoria* and the related sequences in this dataset. |
| Amino acid / residue | A protein building block; a residue is an amino acid incorporated into a chain. The model uses the 20 canonical amino acids. |
| Genotype | The sequence identity of an observed variant; this project works at the amino-acid level. |
| Phenotype | An observed trait. Here it is the archived cellular fluorescence measurement. |
| Reporter | A measurable signal used to study another biological process. GFP is often used as a fluorescent reporter. |
| Fluorescence / chromophore | Light emission after absorbing light; the chromophore is the chemical group responsible for that absorption and emission. |
| Expression / folding / maturation | Protein production; adoption of a three-dimensional structure; chemical changes needed to create a fluorescent chromophore. These can affect the cellular signal. |
| Photophysical property / quantum yield | A property of interaction with light; quantum yield is the fraction of absorbed photons re-emitted as fluorescence. Neither is measured separately here. |
| Barcode | A short DNA identifier used in the source experiment to associate measurements with a genotype. Barcode identifiers are not included in this subset. |
| Landscape | A mapping from many related sequences to an observed trait, not a literal physical landscape. |
| Mutation / substitution / reference | A sequence change; here mutation count records amino-acid substitutions relative to a specified reference sequence. It is not distance to the nearest training sequence. |
| Epistasis | Combined effects of sequence changes that depart from the chosen additive expectation. This coarse model does not establish a mechanism of epistasis. |
| Biological replicate | An independently generated biological experimental unit. Re-running code with another seed is not a biological replicate. |

## Modeling and evaluation

| Term | Meaning here |
| --- | --- |
| TAPE | Tasks Assessing Protein Embeddings, the benchmark that supplies this dataset’s sequence/split derivative. Its original model scores are not reproduced here. |
| Feature / descriptor / representation | A numerical summary supplied to a model. Here: 20 residue fractions and reference-relative substitution count. |
| Label / target | The measured value a model tries to predict: the source’s log-brightness value. |
| Log scale | A logarithmic representation. The archived fluorescence scale is preserved, rather than renamed as absolute molecular brightness. |
| Regression / random forest / decision tree | Prediction of a numerical value; a forest averages fitted trees; a tree partitions feature space and predicts from observations in terminal groups, or leaves. |
| Bootstrap sampling | Drawing training rows with replacement for each tree. This does not create new independent measurements. |
| Hyperparameter | A setting chosen outside model fitting, such as tree count or maximum depth. Settings are fixed here. |
| Pool / oracle / acquisition | The candidate observations whose labels can be revealed; the interface restricting access to acquired labels; selection of the next stored observations. |
| Policy / heuristic | A decision rule; a practical rule without an optimality guarantee. |
| Active learning / label budget | Repeatedly choosing labels to learn from; the number of labels the model is allowed to reveal, including its starting set. |
| Ablation | A controlled comparison that removes components of a method. The new experiment removes uncertainty screening or diversity selection. |
| Hamming distance / diversity | Fraction of aligned positions that differ; selecting less similar sequences under that metric. The distance audit reports mismatch counts instead. |
| Tree spread / disagreement | Standard deviation across individual-tree predictions (population divisor, `ddof=0`). It is a ranking score, not a calibrated probability or interval. |
| Bayesian optimization | Sequentially choosing inputs using a predictive model and uncertainty to improve a specified objective. The aim here is prediction accuracy, not finding the brightest observation. |
| xGPR | The alternative Gaussian-process regression software associated with Parkinson and Wang (2023); it is not used by this project. |
| Calibration / prediction interval | Agreement between stated uncertainty and observed frequencies; a range for a future outcome with defined coverage. Neither is supplied by tree spread here. |
| RMSE / MAE | Root mean squared error / mean absolute error. Both compare predictions with labels; RMSE gives larger errors greater influence. |
| Spearman correlation | Correlation of ranks, using average ranks for tied values. It measures ordered association, not causation; constant ranks make it undefined. |
| SD / confidence interval | Standard deviation describes spread; a confidence interval targets uncertainty in an estimated quantity under stated assumptions. Shading here is sample SD across four seeds, not a confidence interval. |
| Seed / RNG | A numerical initialization / random-number generator. Fixed seeds make the computational sequence repeatable; they do not quantify all sources of uncertainty. |
| Holdout / leakage / blinding | Data excluded from fitting; unavailable-at-prediction information influencing development; concealment of outcomes from developers. Code excludes evaluation labels from decisions, but these public data are not human-blinded. |
| Distribution shift / extrapolation / generalization | A change in the data encountered; predicting outside the represented training range; performance on new observations under a specified setting. “Distant” here still refers to relatives in one GFP dataset. |
| Retrospective / prospective | Reusing already observed outcomes / evaluating on observations collected after a prediction plan. This study is retrospective. |
| Baseline / paired comparison | A simple reference method / comparison using the same starting set and evaluation records within a seed. |

## Files and computation

| Term | Meaning here |
| --- | --- |
| CSV / TSV / JSON | Comma-separated values / tab-separated values / JavaScript Object Notation, text formats for tables or structured records. |
| SHA-256 / checksum / fingerprint | A hash algorithm / a content-derived value used to detect changes. Matching hashes do not authenticate authorship or prove scientific correctness. |
| Manifest / provenance / receipt | A record of inputs and settings / where data came from and how they changed / metadata accompanying an export. |
| gzip / archive member | A compression format / one file inside a bundled archive. |
| CLI / API / CPU / GPU | Command-line interface / application programming interface / central processing unit / graphics processing unit. No GPU or paid API is needed here. |
| CI | Continuous integration: automated checks after repository changes. It is distinct from a confidence interval. |
| Relative / absolute tolerance | Allowed comparison differences scaled to a value / expressed in that value’s units. Floating-point checks allow small rounding differences. |
| MIT / CC BY 4.0 | The code’s software license / the source data’s Creative Commons Attribution license. Read the actual license notices for reuse terms. |

See [biology and concepts](biology-and-concepts.md), [methods](methods.md), [assumptions](assumptions.md), and [references](references.md) for context and evidence.
