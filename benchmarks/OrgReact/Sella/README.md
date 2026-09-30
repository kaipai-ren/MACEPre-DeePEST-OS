# OrgReact Sella benchmark

This benchmark contains 500 transition-state initial guesses spanning 10 bond-forming/bond-breaking categories. Transition-state structures were optimized with the Sella optimizer. For XYZ files that contain an `energy` value, the value is the electronic energy in eV.

## Contents

| Folder | Description | Number of structures |
| --- | --- | ---: |
| `initial-guess-ts` | Initial transition-state guesses used as the starting structures for optimization. | 500 |
| `DFT-opt` | Successfully optimized transition states using DFT as the calculator. | 500 |
| `MACE-OMol-opt` | Successfully optimized transition states using MACE-OMol. | 477 |
| `MACEpre-DeePEST-OS` | Successfully optimized transition states using MACEpre-DeePEST-OS. | 500 |

Each optimization-result folder also contains an `all_log.txt` summary for the corresponding successful optimizations.
