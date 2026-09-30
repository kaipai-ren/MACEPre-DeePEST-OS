# OrgReact Gaussian benchmark

This benchmark uses the same 500 transition-state initial guesses as the Sella benchmark. Transition states, reactants, and products are archived for each successful complete reaction.

For the DFT reference, geometry optimization and frequency analysis were performed at the M06-2X/def2-SVP level. Electronic energies were then evaluated at the ωB97M-V/def2-TZVP level. The reported DFT Gibbs free energy combines the ωB97M-V/def2-TZVP electronic energy with the Gibbs thermal correction obtained from the M06-2X/def2-SVP frequency calculation.

For MACE-OMol and MACEpre-DeePEST-OS, Gaussian was used with the corresponding MLP through the external interface for geometry optimization and frequency analysis. The reported electronic energy and Gibbs free energy are those of the corresponding MLP calculation.

All `energy` and `free_energy` values in the XYZ comment line are in eV:

```text
energy=<electronic energy> free_energy=<Gibbs free energy>
```

## Contents

| Folder | Complete reactions | TS | Reactants | Products |
| --- | ---: | ---: | ---: | ---: |
| `initial-guess-ts` | — | 500 | — | — |
| `DFT-opt` | 487 | 487 | 487 | 487 |
| `MACE-OMol-opt` | 477 | 477 | 477 | 477 |
| `MACEpre-DeePEST-OS` | 482 | 482 | 482 | 482 |

Each method folder contains `ts/`, `reactant/`, and `product/` subfolders. 
