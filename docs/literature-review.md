# Rapid literature and practice review

## Question and scope

Which bounded improvement would make this retrospective GFP benchmark easier to inspect and reuse? The review focused on evaluation reliability, uncertainty-driven acquisition and reproducible result records. It did not seek new sequence designs or a larger prediction model. Recent discovery covered 2022-01-01 through 2026-10-20, with earlier data and benchmark sources retained for context.

**Round 02, also 2026-10-20.** This focused update asks whether final-budget model metrics can be reconstructed from source-linked predictions. It addresses a new implementation gap on the same day; it is not elapsed-time surveillance. The earlier search remains unchanged, and [search-update-02.json](search-update-02.json) records the new search.

## Search record

PubMed was searched first for protein active learning combined with benchmarking, reproducibility or uncertainty. The query returned 25 records: the first page contained 12 and the second 13; all were screened by title and abstract. A subsequent quoted-title query for the known Greenman paper returned zero with a provider warning, so its already retrieved PMID was used to obtain the record directly. Two recent papers were retained, one for the main rationale and one as an alternative deliberately not implemented. [search-log.json](search-log.json) records exact syntax, publication-date limits, sorting, IDs, decisions and access limits.

Excluded records concerned other targets or prediction tasks, objective-maximizing rather than model-improving campaigns, reviews or preprints. A returned December 2026 issue-dated review was not used; its timing relative to the cutoff was unresolved. Official repository and versioned API pages were inspected as supplementary sources, with no discoverable total-result count asserted. The original Sarkisyan and TAPE sources are prior foundational context, not new PubMed yields.

A PubMed query combined reproducibility/data leakage, protein and benchmarking terms within 2022-01-01 through 2026-10-20. It returned 130 records; only the first six relevance-ranked records were screened. One primary protein-prediction benchmarking study was retained from its complete abstract. Five experimental measurement/workflow papers were not selected. No subsequent page was retrieved and no full-text claim is made for the selected paper. Official versioned regression-metric documentation was inspected separately.

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

| Round-02 source | Access and relevant support | Limit and code consequence |
| --- | --- | --- |
| [Luo et al., PMID 39657630](https://pubmed.ncbi.nlm.nih.gov/39657630/) | Primary DNA-binding-protein evaluation; complete abstract reports that dataset leakage inflated conventional benchmark performance. | Different task and models; no performance estimate transfers to GFP. Keep held-out identities explicit and source-linked. |
| [scikit-learn 1.8.0 metric reference](https://scikit-learn.org/1.8/modules/model_evaluation.html#regression-metrics) | Official metric definitions and evaluation semantics. | Correct arithmetic does not establish a valid biological test set. Implement direct error calculations and test their definitions. |
| [Greenman et al., PMID 39775201](https://pubmed.ncbi.nlm.nih.gov/39775201/) | Earlier-round publisher appraisal retained: acquisition and uncertainty outcomes depend on evaluation setting. | Not newly discovered here. Preserve the mixed baseline results instead of adjusting policy choices after viewing them. |

No external model or metric code was copied. Average-tie rank correlation is implemented independently from its definition and checked against known examples.

## Changes made

`gfp_active_learning/audit.py` independently checks the saved query and result tables against the verified input. It recalculates summaries, paired differences and sequence-distance statistics, checks seeded initial sets and counts, and exports the reviewed file hashes. New tests intentionally corrupt source labels, acquisitions, counts, missing rows and aggregates. CI audits the reproduced results after the existing comparison step. The baseline model, data, policies and scientific result files are unchanged.

Round 02 exports only the eight final-budget models' 9,600 evaluation predictions in one compact gzip CSV. A separate verifier joins outcomes by source record ID, checks complete role-correct keys, independently computes RMSE, MAE and average-tie rank correlation, and compares all 16 metric rows with the saved results (`rtol=1e-8`, `atol=1e-10`). Source and output hashes are retained. Earlier result files and acquisition policies are unchanged.

## Remaining work

Exporting per-observation predictions would allow a stronger independent check of RMSE and rank metrics. Protocol versioning and predeclared multiple subsets would make broader reuse clearer. Each is listed with acceptance criteria in [practical use](practical-use.md); none is represented as already implemented.

Per-observation final-budget verification is now implemented. Earlier checkpoints, multiple prespecified subsets and calibrated uncertainty analysis remain separate future work. Recreating a metric from stored predictions does not independently validate how those predictions were trained.

## Limits of this review

This is a bounded rapid review, not a complete systematic review: one database, one reviewer, limited query vocabulary and no independent duplicate screening. All returned records were screened, but that is not the same as all relevant literature being found. One retained alternative was abstract-only. Publication-date filters can reflect multiple dates, as the issue-date anomaly illustrates. No abstracts or paper text are redistributed, and no model-comparison claim is inferred from documentation alone.

Only six of 130 relevance-ranked records were screened in this targeted update, by one reviewer. The included new paper was abstract-only, and no general performance claims are drawn from it. The export improves numerical traceability; it does not solve biological domain shift, experimental dependence or public-benchmark overfitting.
