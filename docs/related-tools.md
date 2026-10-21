# Related tools and what we borrow

These are useful next steps for readers, not dependencies required to run this repository. Links were checked against the official repositories on 2026-10-20.

| Project | Relevant idea | Relationship to this project |
| --- | --- | --- |
| [TAPE](https://github.com/songlab-cal/tape) | Public sequence tasks with explicit splits and documented original datasets | Supplies the sequence/split derivative linked in its README. We restore the original phenotype and define a small subset. We do not run TAPE neural models or reproduce its published scores. |
| [Protein UQ](https://github.com/microsoft/protein-uq) | Evaluate uncertainty and iterative acquisition rather than assuming confidence scores are useful | Its [2025 paper](https://doi.org/10.1371/journal.pcbi.1012639) motivates comparison against random selection. Our forest-disagreement/diversity heuristic differs from its studied models and is not an implementation-equivalent reproduction. |
| [scikit-learn random forests](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.RandomForestRegressor.html) | Bootstrap sampling (sampling training rows with replacement), regression predictions, and seeded CPU execution | The only fitted model family here. Dispersion across trees is computed locally as a ranking heuristic; scikit-learn does not thereby certify a calibrated uncertainty interval. |

TAPE's current README distinguishes its later PyTorch code from the original paper code and cautions about reproducing original results. Data provenance and a shared task name do not make two benchmark protocols equivalent. Similarly, a more elaborate uncertainty model would need its own calibration and acquisition evaluation; it cannot be assumed to improve this fixed benchmark.

No external project code was copied. Each project's code/data licenses apply to its own material; [our data notice](../DATA_LICENSE.md) explains the measured-data attribution retained here.
