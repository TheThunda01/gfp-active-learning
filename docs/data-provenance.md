# Data provenance and reconstruction

## Primary source and derivative

The scientific source is [Sarkisyan et al., Nature (2016)](https://doi.org/10.1038/nature17995), with original files archived as [Figshare article 3102154, version 1](https://doi.org/10.6084/m9.figshare.3102154.v1). The archive's [version-specific metadata](https://api.figshare.com/v2/articles/3102154/versions/1) identifies the data license as CC BY 4.0. The [attribution notice](../DATA_LICENSE.md) is separate from this project's MIT code license.

The original amino-acid table has 54,025 records. Its `medianBrightness` column contains median log-brightness across barcodes sharing an amino-acid genotype. The `std` column describes across-barcode variation and is empty for a single-barcode genotype; it is not used as an independent replicate or uncertainty model here.

The [official TAPE repository](https://github.com/songlab-cal/tape#raw-data) links a JSON derivative of this dataset. We use its sequence records and original split membership, then match back to the original amino-acid table for the phenotype. This avoids silently treating rounded derivative values as a different measurement. The TAPE paper is [Rao et al., NeurIPS (2019)](https://proceedings.neurips.cc/paper/2019/hash/37f65c068b7723cd7809ee2d31d7861c-Abstract.html).

## Exact inputs

| Input | Pinned location | SHA-256 |
| --- | --- | --- |
| Original amino-acid table, file 4820647 | [Figshare TSV](https://ndownloader.figshare.com/files/4820647) | `5581230b9888f9960708a4769ce1c9b4453561f0b5f0374525445b4a984d54d5` |
| TAPE fluorescence JSON archive | [Official linked archive](https://s3.amazonaws.com/songlabdata/proteindata/data_raw_pytorch/fluorescence.tar.gz) | `3c7caffd28a40f0dc8791fa311f90af4423654bd90c72fdc1e5bb191c79e175a` |

The original file has 2,334,128 bytes; the TAPE archive has 1,410,354. Individual JSON member checksums are also pinned in [manifest.json](../data/manifest.json). URLs are locators; the checksums are the immutable content checks. A changed download fails instead of silently changing the benchmark.

## Mapping and exclusions

The preparation script identifies the one recorded zero-substitution, 237-residue reference in TAPE's train split. It applies the original table's zero-based substitution annotations to reconstruct **already measured records**, solely for matching to TAPE sequences. It does not propose unmeasured variants. Original stop-containing records are excluded, and only 237-residue canonical-amino-acid TAPE strings are retained. No inferred padding or alignment is used.

| Original TAPE split | JSON records | Full-length records matched |
| --- | ---: | ---: |
| Train | 21,446 | 20,963 |
| Validation | 5,362 | 5,235 |
| Test | 27,217 | 25,517 |
| Total | 54,025 | 51,715 |

All 51,715 retained sequences match a unique original-table genotype. The 2,310 excluded original genotypes contain stops and their corresponding TAPE strings are shorter. The maximum absolute difference between the original label and TAPE's rounded value is `2.3484440436760678e-07`, below the declared `1e-6` tolerance. The included CSV stores the original phenotype string. It contains no patient data or molecular barcode identifiers.

## Final subset and audit fields

Train and validation candidates are merged, ranked by a salted sequence hash, and split into pool/local-test roles; original test candidates are independently ranked for distant evaluation. [Methods](methods.md) gives the exact rule. No label is used to choose subset membership. The 3,600-row CSV is 1,276,273 bytes with SHA-256 `dd507d203c83db659000ff743ecf7afa77b30e284ecc248c2eb22aa4d474bdec`.

`source_index` is the zero-based index within a TAPE JSON split, while `original_table_line` is the one-based physical line in the original TSV, including the header. `sequence_sha256` is the hash of the exact amino-acid string. These fields let a reader audit correspondence without trusting the new record identifier.

The rebuild command is in the README. It checks both input hashes before parsing, uses only named archive members without extracting files to disk, and writes a new dataset and manifest. Verification date: 2026-10-20. A compact [source metadata record](../data/source_metadata.json) retains the license and archive identities used in this verification.
