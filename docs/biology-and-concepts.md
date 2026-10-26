# The biology and the learning problem

## Why GFP is useful here

Green fluorescent protein, or GFP, is a fluorescent reporter: its signal lets researchers observe biological processes through light. A protein's amino-acid sequence helps determine whether it folds into a structure that can support fluorescence. The chromophore—the molecular group responsible for light emission—also has to mature through chemical changes. A sequence that looks plausible on paper may therefore produce little observed signal.

This project uses the *Aequorea victoria* GFP (avGFP) landscape measured by [Sarkisyan et al. (2016)](https://doi.org/10.1038/nature17995). Their table links amino-acid genotypes (protein sequence identities) to cellular fluorescence. These existing measurements let the benchmark test how a statistical model learns a sequence–phenotype relationship: how sequence relates to an observed trait. The repository neither invents proteins nor conducts the underlying experiments.

## What the number actually means

The target is the original table's `medianBrightness`. For each amino-acid genotype, this value summarizes the median log-brightness across associated barcodes, the short DNA identifiers used to track measurements. The repository preserves those original values. They do not measure absolute photon counts per purified molecule, quantum yield (the fraction of absorbed photons re-emitted as fluorescence), or an enzyme's catalytic rate.

Cellular fluorescence can reflect protein abundance and expression, folding, chromophore maturation, and the measurement context. [Balleza et al. (2018)](https://doi.org/10.1038/nmeth.4509) directly characterized fluorescent-protein maturation in living cells, illustrating why time-dependent maturation matters when interpreting reporter signals. Consequently, a sequence associated with lower brightness here is not automatically less useful in every imaging application. This benchmark cannot separate those contributing mechanisms from one aggregate label.

The original table also reports variability across associated barcodes. We retain the source's median phenotype but do not model that variability as observation-specific noise. Repeated acquisition simulations do not create additional biological replicates or improve the original measurement precision.

## From a sequence to a prediction

The model receives 21 numbers: the fraction of each of the 20 canonical amino acids and the source-reported number of substitutions relative to the reference. These coarse descriptors preserve composition and distance from the reference but discard residue positions. Two distinct sequences can therefore receive the same descriptor vector.

A random forest combines predictions from many fitted decision trees. This baseline runs on an ordinary central processing unit (CPU) and learns associations in the descriptors. It does not model folding or explain why a particular residue changes fluorescence. It also cannot extrapolate its mutation-count response beyond values represented in training: predictions from trees remain averages of observations in terminal leaves.

The original GFP study discusses epistasis: combined sequence changes can have effects that differ from the sum of their individual effects. Our coarse model does not measure or establish such interactions. A model error could reflect missing positional information, a difficult biological relationship, noisy measurement, or several of these at once.

## What “active learning” means in this repository

Imagine a table in which sequence identities are visible but most measured brightness values are temporarily covered. The program starts by uncovering 64 pool labels. It fits a model, chooses another batch using only visible labels and available sequences, then uncovers the selected values and fits again. This repeats until 384 labels are visible.

The random policy chooses uniformly from the remaining pool. The second policy first considers observations with high disagreement among the forest's trees, then spreads the batch across sequences using Hamming distance—the fraction of aligned positions with different residues. This is an explicit heuristic, not an optimal selection rule. Tree disagreement need not track actual prediction error and is not a calibrated probability or prediction interval.

The goal is better prediction with a limited label budget, not discovery of the brightest variant. An optimization campaign would instead select candidates for high expected performance. Here, every selected observation already has a measured label in the public archive. The program generates no sequences, synthesis plans, or laboratory recommendations.

## Why two evaluation sets matter

[Tasks Assessing Protein Embeddings (TAPE; Rao et al., 2019)](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html) separates GFP observations partly by mutation distance. We preserve that broad distinction: pool and local evaluation records have at most three source substitutions, while the second evaluation set has at least four. The latter asks a harder distribution-shift question, but all records remain close relatives within one GFP landscape.

Sequence identities never overlap across roles, but different records can be only a few residues apart. The distance audit measures that relatedness. Holding out a sequence does not make it an unrelated, independent evolutionary example.

Root mean squared error (RMSE) summarizes error magnitude on the source scale; Spearman rank correlation compares the ordering of predictions and measurements. Neither alone establishes practical usefulness. The shaded learning curves show variation across four acquisition seeds on the same fixed pool and evaluation sets. They do not quantify all uncertainty from measurement, subset choice, model choice, or future experiments.

## What a useful result looks like

An honest result may be that a selection rule helps locally and fails to help farther away. [Greenman et al. (2025)](https://doi.org/10.1371/journal.pcbi.1012639) found that uncertainty methods and acquisition outcomes depend on the landscape, split, and metric. Their larger benchmark motivates checking outcomes rather than assuming uncertainty sampling always wins; this repository does not reproduce their models.

The most transferable output is the evaluation discipline: keep hidden labels hidden from decisions, state the biological meaning of the phenotype, inspect sequence relatedness, and report unfavorable results. A prospective experiment or a different protein system would require its own validation.
