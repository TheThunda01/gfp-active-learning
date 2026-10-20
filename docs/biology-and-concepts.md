# The biology and the learning problem

## Why GFP is useful here

Green fluorescent protein, or GFP, is a fluorescent reporter: its signal lets researchers observe biological processes through light. A protein's amino-acid sequence helps determine whether it folds into a structure that can support fluorescence. The chromophore also has to mature. A sequence that looks plausible on paper may therefore produce little observed signal.

This project uses the avGFP landscape measured by [Sarkisyan and colleagues](https://doi.org/10.1038/nature17995), not a collection of computationally invented proteins. Their study connected many amino-acid genotypes to a cellular fluorescence readout. That makes it useful for asking how a statistical model learns a measured sequence–phenotype relationship, while keeping the experiment itself outside the scope of this repository.

## What the number actually means

The target is the original table's `medianBrightness`: a median on the study's log-brightness scale over barcodes associated with an amino-acid genotype. The repository preserves those original values. The name is easy to overread. It is not an absolute photon count per purified molecule, a quantum-yield measurement, or an enzyme's catalytic rate.

Cellular fluorescence can reflect protein abundance and expression, folding, chromophore maturation, and the measurement context. [Balleza, Kim, and Cluzel](https://doi.org/10.1038/nmeth.4509) directly characterized fluorescent-protein maturation in living cells, illustrating why time-dependent maturation matters when interpreting reporter signals. Consequently, a sequence associated with lower brightness here is not automatically less useful in every imaging application. This benchmark cannot separate those contributing mechanisms from one aggregate label.

The original table also reports variability across associated barcodes. We retain the source's median phenotype but do not model that variability as observation-specific noise. Repeated acquisition simulations do not create additional biological replicates or improve the original measurement precision.

## From a sequence to a prediction

The model receives 21 numbers: the fraction of each of the 20 canonical amino acids and the source-reported number of substitutions relative to the reference. These descriptors are intentionally modest. They preserve broad composition and distance from the reference but discard which position contains most residues. Two distinct sequences can therefore receive the same descriptor vector.

A random forest combines predictions from many fitted decision trees. Here it is a practical, CPU-friendly baseline rather than a mechanistic model of folding. It can learn associations in the observed descriptors but cannot explain why a particular residue changes fluorescence. It also cannot extrapolate its mutation-count response beyond values represented in training: predictions from trees remain averages of observations in terminal leaves.

The original GFP study discusses non-additive sequence effects. Our coarse model does not measure or establish such interactions. A model error could reflect missing positional information, a difficult biological relationship, noisy measurement, or several of these at once.

## What “active learning” means in this repository

Imagine a table in which sequence identities are visible but most measured brightness values are temporarily covered. The program starts by uncovering 64 pool labels. It fits a model, chooses another batch using only visible labels and available sequences, then uncovers the selected values and fits again. This repeats until 384 labels are visible.

The random policy chooses uniformly from the remaining pool. The second policy first considers observations with high disagreement among the forest's trees, then spreads the batch across sequences using Hamming distance—the fraction of aligned positions with different residues. This is an explicit heuristic, not an optimal selection rule. Tree disagreement need not track actual prediction error and is not a calibrated probability or prediction interval.

The goal is better prediction with a limited label budget, not discovery of the brightest variant. That distinction separates this example from an optimization campaign that selects candidates for high expected performance. Every selected observation already has a measured label in the public archive. No sequence generation, synthesis plan, or laboratory recommendation is produced.

## Why two evaluation sets matter

[TAPE](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html) separates GFP observations partly by mutation distance. We preserve that broad distinction: pool and local evaluation records have at most three source substitutions, while the second evaluation set has at least four. The latter asks a harder distribution-shift question, but all records remain close relatives within one GFP landscape.

Sequence identities never overlap across roles. Nevertheless, different records can be only a few residues apart. The distance audit therefore matters alongside a clean split. It prevents “held out” from being mistaken for unrelated, independent evolutionary examples.

RMSE summarizes error magnitude on the source scale; Spearman correlation summarizes ranking. Neither alone establishes practical usefulness. The shaded learning curves show variation across four acquisition seeds on the same fixed pool and evaluation sets. They do not quantify all uncertainty from measurement, subset choice, model choice, or future experiments.

## What a useful result looks like

An honest result may be that a selection rule helps locally and fails to help farther away. [Greenman and colleagues](https://doi.org/10.1371/journal.pcbi.1012639) found that uncertainty methods and acquisition outcomes depend on the landscape, split, and metric. Their larger benchmark motivates checking outcomes rather than assuming uncertainty sampling always wins; this repository does not reproduce their models.

The most transferable output is the evaluation discipline: keep hidden labels hidden from decisions, state the biological meaning of the phenotype, inspect sequence relatedness, and report unfavorable results. A prospective experiment or a different protein system would require its own validation.
