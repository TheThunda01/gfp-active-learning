# GFP policy ablation: learning checkpoint

Prediction recorded before this ablation: **combined selection would help most on more-distant variants**. No reason was supplied. These are reused historical outcomes, not a new blind holdout.

| Evaluation | Policy | Final mean RMSE | Descriptive SD |
| --- | --- | ---: | ---: |
| local_test | random | 0.7715 | 0.0096 |
| local_test | uncertainty_only | 0.7535 | 0.0235 |
| local_test | diversity_only | 0.7699 | 0.0093 |
| local_test | combined | 0.7570 | 0.0162 |
| distant_test | random | 1.1651 | 0.0632 |
| distant_test | uncertainty_only | 1.1897 | 0.0380 |
| distant_test | diversity_only | 1.1428 | 0.0111 |
| distant_test | combined | 1.1799 | 0.0406 |

The lowest distant-set mean RMSE was **diversity_only**. The mean distant-minus-local combined benefit was **-0.0293** RMSE units; positive would favor the predicted distance pattern.

This fixed exploratory extension does not support the recorded combined-at-distance prediction. The result is specific to these outcomes, seeds and model; it is not a general ranking of acquisition algorithms.

| Seed | Combined benefit locally | Combined benefit distantly | Distant minus local benefit |
| ---: | ---: | ---: | ---: |
| 11 | +0.0317 | +0.0367 | +0.0050 |
| 29 | +0.0067 | -0.0719 | -0.0786 |
| 47 | +0.0212 | +0.0748 | +0.0536 |
| 83 | -0.0012 | -0.0985 | -0.0973 |

Benefit means random RMSE minus combined RMSE; positive is better for combined. The contrast is positive in two seeds and negative in two. Four seeds share the same evaluation observations; these are descriptive comparisons, not a significance test.

## Does tree disagreement track error?

| Policy | Local mean rank association | Distant mean rank association |
| --- | ---: | ---: |
| random | 0.5609 | 0.1138 |
| uncertainty_only | 0.5682 | 0.1048 |
| diversity_only | 0.5924 | 0.1219 |
| combined | 0.5496 | 0.0688 |

Each value averages four separately computed Spearman associations between tree spread and absolute prediction error at the final budget. The observations are reused across seeds. These are heuristic association diagnostics, not calibration, error bars, or confidence-interval coverage.

Spread/error association is much weaker on this distant set. This is consistent with disagreement being a less useful warning of error there, but does not prove why the combined acquisition policy lost. Uncertainty screening can exclude candidates that diversity-only would consider; its causal contribution would need a further fixed comparison.

![Learning curves](learning_curves.png)

The existing random and combined acquisition orders and metrics were reproduced. Uncertainty-only removes the diversity step; diversity-only removes uncertainty screening. All models still discard residue position, and the distant set extends beyond the pool’s mutation-count range. Neither this ablation nor its reused evaluation labels establish prospective or protein-family generalization.
