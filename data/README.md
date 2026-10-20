# Included data

`dataset.csv` contains 3,600 already measured, full-length GFP records. It is a deterministic subset of the original Sarkisyan phenotype table matched to TAPE sequence records. See [provenance](../docs/data-provenance.md), [methods](../docs/methods.md), and [CC BY 4.0 attribution](../DATA_LICENSE.md).

| Column | Meaning |
| --- | --- |
| `record_id` | Original TAPE split plus zero-based JSON record index |
| `role` | `pool`, `local_test`, or `distant_test`; fixed before acquisition |
| `source_split` | Original TAPE `train`, `valid`, or `test` split |
| `source_index` | Zero-based JSON record index within that split |
| `original_table_line` | One-based physical line in original TSV, header included |
| `sequence` | Recorded 237-residue amino-acid string; canonical letters only |
| `mutation_count` | Source reference-relative substitution count |
| `log_brightness` | Original `medianBrightness`: median log-brightness across associated barcodes |
| `sequence_sha256` | SHA-256 of exact sequence text |

The label remains visible in this public file because the study is retrospective. `PoolOracle` controls when a simulation can read pool labels; acquisition functions never accept the label array or evaluation outcomes. This is a software boundary for benchmarking, not a claim that previously public outcomes are blinded to humans.

`manifest.json` records strict source, archive-member, and final-input hashes. `source_metadata.json` is a compact license/provenance record from the original archive. No network access is needed for the normal analysis.
