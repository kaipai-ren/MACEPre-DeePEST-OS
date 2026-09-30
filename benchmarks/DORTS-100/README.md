# DORTS-100 benchmark

DORTS-100 contains 100 transition-state initial guesses and the corresponding
successfully optimized transition-state structures obtained with the Sella
optimizer. For XYZ files that contain an `energy` value, the value is the
electronic energy in eV. The DFT geometry optimizations and frequency analyses were performed at the ωB97M-V/def2-TZVP level of theory.

## Contents

| Folder | Description | Number of structures |
| --- | --- | ---: |
| `initial-guess-ts` | Initial transition-state guesses used as the starting structures for optimization. | 100 |
| `DFT-opt` | Successfully optimized transition states using DFT as the calculator. | 100 |
| `MACE-OMol-opt` | Successfully optimized transition states using MACE-OMol. | 93 |
| `DeePEST-OS-opt` | Successfully optimized transition states using DeePEST-OS. | 100 |
| `Active-learning-opt` | Successfully optimized transition states using the Active-learning model. | 98 |
| `MACEpre-DeePEST-OS` | Successfully optimized transition states using MACEpre-DeePEST-OS. | 96 |

Each optimization-result folder also contains an `all_log.txt` summary for the
corresponding successful optimizations.
