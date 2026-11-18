# Did the first shortlist exclude choices made by the full-pool rule?

**Decision record · November 17, 2026.** This follow-up asks a neutral question about decisions in the archived GFP benchmark. The four-policy results were already public. This note records the comparison before computing the new overlap counts. The October prediction and its original rationale record remain available in the [historical plan](../uncertainty_ablation/PLAN.md).

## Comparison

For each of the four published seeds, start at the point where the combined and diversity-only rules still have the same 64 labeled records. How many of the diversity-only rule’s next 64 choices were eligible for the combined rule’s 256-record uncertainty shortlist? Report the counts inside and outside the shortlist. Separate candidates that were eligible from those the combined rule actually chose. Do not pool the seeds as independent biological observations.

The archive saved selections but did not save the complete shortlist. Reconstruct only the first shortlist with the historical settings. Check the reconstruction against the ordered first-round decisions in the archive. If it does not reproduce those decisions, identify the discrepancy and withhold exact exclusion counts for the affected run. Document the runtime in which the check passes.

## Interpretation decided in advance

If all 64 choices survived the screen, it could not have excluded a diversity-only choice at that step. If some were excluded, screening changed which choices were possible. The number excluded alone cannot establish whether those choices would have reduced error. Even when both rules could select a record, choosing a different first record can change later choices.

Read the existing prediction errors after that first batch (128 labels) and at the final budget (384 labels). State the comparator and direction for each difference. Keep the original distant-minus-local benefit versus random distinct from the comparison between combined and diversity-only. Later rounds use different training histories. This follow-up does not assign their final error difference to the first shortlist.

Brandon selected a neutral question for this follow-up. The analysis, figures, and writing were prepared with AI assistance using the existing public records.
