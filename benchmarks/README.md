# Benchmarks

This directory contains the structures used to evaluate transition-state
optimization, electronic energies, and Gibbs free-energy barriers in the study.
Each benchmark has its own README with the exact contents and calculation
definitions.

## Overview

| Benchmark | Scope | Main archived quantities |
| --- | --- | --- |
| `DORTS-100` | 100 transition-state initial guesses optimized with Sella | optimized TS structures and electronic energies |
| `RGD1-100` | 100 transition-state initial guesses optimized with Sella | optimized TS structures and electronic energies |
| `T1x-100` | 100 transition-state initial guesses optimized with Sella | optimized TS structures and electronic energies |
| `OrgReact` | organic-reaction TS benchmark with Sella and Gaussian workflows | electronic energies; Gaussian workflow also contains gas-phase Gibbs free energies |
| `Ugi` | 22 reported Ugi transition-state pathways | electronic energies, gas-phase Gibbs free energies, and SMD(toluene) Gibbs free energies where available |
| `Biginelli` | seven elementary Biginelli transition-state pathways | gas-phase Gibbs free energies |
| `Metal-Lewis-Acid` | 3 reaction classes × 7 Lewis-acid conditions | gas-phase Gibbs free energies |

## Quantum-chemistry reference levels

For `DORTS-100`, `RGD1-100`, and `T1x-100`, the DFT geometry optimization
and frequency analysis were performed at the ωB97M-V/def2-TZVP level.

The Gaussian OrgReact and Ugi mixed-level reference calculations use
M06-2X/def2-SVP geometry optimization and frequency analysis together with
ωB97M-V/def2-TZVP electronic energies. Ugi additionally contains
SMD(toluene)-corrected solution-phase free energies for the methods described
in its README.

The Biginelli reference uses M06-2X/def2-SVP geometry optimization and
frequency analysis with ωB97M-V/def2-TZVP electronic energies.

The Metal-Lewis-Acid reference uses B3LYP-D3(BJ)/def2-SVP geometry optimization
and frequency analysis with ωB97M-V/def2-TZVP electronic energies.

## File conventions

Initial transition-state guesses are stored under `initial-guess-ts/` and have
a blank second XYZ line.

Optimized structures use eV for values stored in the XYZ comment line. Depending
on the benchmark, the metadata field is one or more of:

```text
energy=<electronic energy>
free_energy=<Gibbs free energy>
gibbs_free_energy_gas=<gas-phase Gibbs free energy>
gibbs_free_energy_smd_toluene=<SMD(toluene) Gibbs free energy>
```

Only fields relevant to a given benchmark are retained. See the benchmark-level
README before using the data.

The manuscript and Supporting Information define the reported RMSD and barrier
error metrics. Separate evaluation scripts are intentionally not duplicated in
this repository.
