# What this project is trying to show

A dataset may contain thousands of measurements, but a laboratory project may afford only a small next batch. Choosing that batch differs from fitting a model to a complete table. This repository explores the choice by hiding and revealing existing measurements. It proposes no new proteins or laboratory experiments.

The [original study](https://doi.org/10.1038/nature17995) supplies a public landscape of measured green fluorescent protein (GFP) sequences. Their cellular brightness reflects expression (protein production), folding (adopting a three-dimensional structure), and maturation of the chromophore (the light-emitting group). Brightness therefore cannot serve as a universal measure of protein quality. This project uses those observations in a small computational experiment whose data and decisions can be audited.

The program starts with a few revealed labels—stored measurements—from a fixed pool of candidate observations. It compares choosing additional records uniformly at random with choosing records through model disagreement and sequence diversity. Both policies share their initial observations and label budgets. Two separate evaluation sets ask whether learning is useful for nearby sequences and for a more mutated part of the same landscape.

The heuristic's advantage depends on the evaluation set. In the included run, it had slightly lower average error locally but slightly higher average error on the more mutated set. One favorable curve would miss that difference. The [2025 Protein UQ study](https://doi.org/10.1371/journal.pcbi.1012639) provides a broader reason to test acquisition outcomes rather than assume uncertainty scores will help.

Readers can inspect how the project traces data, separates related sequences, controls label access, and repeats comparisons. These checks support computational reproducibility. All records were already measured, so repeating the simulation does not produce biological replication. Future changes guided by the public evaluation metrics are benchmark development rather than fresh confirmation.

The [glossary](glossary.md) defines the terms and the [assumptions](assumptions.md) explain the design choices. Read the [biology guide](biology-and-concepts.md) for the conceptual background, [methods](methods.md) for exact choices, and [provenance](data-provenance.md) to trace the original data. The project is intended to demonstrate careful computational practice, not a validated strategy for a laboratory campaign.
