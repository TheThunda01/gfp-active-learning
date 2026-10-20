# Rapid literature and practice review

## Question and scope

Which bounded improvement would make this retrospective GFP benchmark easier to inspect and reuse? The review focused on evaluation reliability, uncertainty-driven acquisition and reproducible result records. It did not seek new sequence designs or a larger prediction model. Recent discovery covered 2022-01-01 through 2026-10-20, with earlier data and benchmark sources retained for context.

## Search record

PubMed was searched first for protein active learning combined with benchmarking, reproducibility or uncertainty. The query returned 25 records: the first page contained 12 and the second 13; all were screened by title and abstract. A subsequent quoted-title query for the known Greenman paper returned zero with a provider warning, so its already retrieved PMID was used to obtain the record directly. Two recent papers were retained, one for the main rationale and one as an alternative deliberately not implemented. [search-log.json](search-log.json) records exact syntax, publication-date limits, sorting, IDs, decisions and access limits.

Excluded records concerned other targets or prediction tasks, objective-maximizing rather than model-improving campaigns, reviews or preprints. A returned December 2026 issue-dated review was not used; its timing relative to the cutoff was unresolved. Official repository and versioned API pages were inspected as supplementary sources, with no discoverable total-result count asserted. The original Sarkisyan and TAPE sources are prior foundational context, not new PubMed yields.

## What the sources support

| Source | Type and access | Relevant finding or resource | Limit | Implementation consequence |
| --- | --- | --- | --- | --- |
| [Greenman et al., PMID 39775201](https://pubmed.ncbi.nlm.nih.gov/39775201/), 2025 | Primary benchmark; publisher full text, particularly active-learning results and conclusions | Acquisition outcomes and uncertainty quality vary across tasks; retrospective comparisons can expose failures. | Different data, representations and models; does not validate this GFP heuristic. | Preserve mixed results, paired seeds and separate evaluation roles; audit the recorded comparisons. |
| [Parkinson and Wang, PMID 37498239](https://pubmed.ncbi.nlm.nih.gov/37498239/), 2023 | Primary alternative regression method; PubMed abstract only | Reports sequence kernels and uncertainty evaluation over multiple tasks. | No full-text appraisal or reproduction here; abstract performance claims are not transferred. | Defer a new model family; first improve traceability of the existing baseline. |
| [Sarkisyan et al., 2016](https://doi.org/10.1038/nature17995) | Primary source study; prior data/phenotype appraisal retained | Supplies the measured sequence–phenotype landscape. | The cellular readout and related sequences constrain generalization. | Verify queried labels and identities against the original-source-matched snapshot. |
| [TAPE, 2019](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html) | Primary benchmark; task definition inspected | Defines sequence/split provenance and the mutation-distance task. | Our subset and model are different from TAPE's published benchmark. | Audit fixed roles, distances and evaluation counts; do not report these as TAPE scores. |
| [Protein UQ repository](https://github.com/microsoft/protein-uq/tree/5e7b2b9cd219805eaabe73b21d4d9955cf882448) | Official software; README and MIT license inspected at commit `5e7b2b9cd219805eaabe73b21d4d9955cf882448` | Documents environments, configurations and separate reproduction steps for its analyses. | Model source was not executed or copied, and its data scope differs. | Add an explicit saved-run verification step alongside full reproduction. |
| [scikit-learn 1.8.0 forest documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.RandomForestRegressor.html) | Official versioned API documentation | Specifies random-state and estimator configuration behavior. | Estimator semantics do not establish calibrated uncertainty. | Audit the exact forest settings and seed rule while retaining the heuristic caveat. |

The audit is original code, not a port of Protein UQ or xGPR. The paper supports the need to assess an acquisition procedure; it does not prescribe this audit or prove absence of leakage. The repository inspection covered the named README and license only. Original code remains MIT; source scientific data retain CC BY 4.0 attribution.

## Changes made

`gfp_active_learning/audit.py` independently checks the saved query and result tables against the verified input. It recalculates summaries, paired differences and sequence-distance statistics, checks seeded initial sets and counts, and exports the reviewed file hashes. New tests intentionally corrupt source labels, acquisitions, counts, missing rows and aggregates. CI audits the reproduced results after the existing comparison step. The baseline model, data, policies and scientific result files are unchanged.

## Remaining work

Exporting per-observation predictions would allow a stronger independent check of RMSE and rank metrics. Protocol versioning and predeclared multiple subsets would make broader reuse clearer. Each is listed with acceptance criteria in [practical use](practical-use.md); none is represented as already implemented.

## Limits of this review

This is a bounded rapid review, not a complete systematic review: one database, one reviewer, limited query vocabulary and no independent duplicate screening. All returned records were screened, but that is not the same as all relevant literature being found. One retained alternative was abstract-only. Publication-date filters can reflect multiple dates, as the issue-date anomaly illustrates. No abstracts or paper text are redistributed, and no model-comparison claim is inferred from documentation alone.
