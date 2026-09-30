# Ugi benchmark

The Ugi benchmark uses the mixed-level Gaussian-based workflow and contains the
22 transition-state pathways used in the reported comparison. These pathways
are grouped according to Reactions A-L in the reaction-network figure; files
are named accordingly, for example `Reaction-A-TS1.xyz` and
`Reaction-L-TS5.xyz`.

The benchmark does not count every available TS/R/P file as an independent
reaction. Only the 22 pathways included in the reported comparison are
archived. The corresponding 22 transition-state starting geometries are
provided in `initial-guess-ts/`.

## Included pathways

| Reaction | Included transition states |
| --- | --- |
| A | TS1, TS2, TS3 |
| B | TS1, TS2, TS3, TS4 |
| C | TS2, TS3 |
| D | TS2 |
| E | TS1 |
| F | TS2 |
| G | TS2 |
| H | TS2, TS3 |
| I | TS3 |
| J | TS3 |
| K | TS3 |
| L | TS2, TS3, TS4, TS5 |

This gives 22 pathways in total. For every pathway, the transition state,
reactant, and product are archived.

## Energy definitions

Three energy quantities are used in this benchmark:

- `energy`: electronic energy.
- `gibbs_free_energy_gas`: gas-phase Gibbs free energy.
- `gibbs_free_energy_smd_toluene`: solution-phase Gibbs free energy with
  SMD(toluene) correction.

All values stored in the XYZ comment line are in eV.

For the DFT reference, geometry optimization and frequency analysis were
performed at the M06-2X/def2-SVP level. The gas-phase electronic energy was
then evaluated at the ωB97M-V/def2-TZVP level. The gas-phase Gibbs free energy
is the ωB97M-V/def2-TZVP electronic energy plus the Gibbs thermal correction
from the M06-2X/def2-SVP frequency calculation. The solution-phase Gibbs free
energy uses a ωB97M-V/def2-TZVP SMD(toluene) single-point energy on the same
optimized geometry plus the same thermal correction.

For MACEpre-DeePEST-OS, Gaussian calls the MLP through the external interface
for geometry optimization and frequency analysis. The reported `energy` and
`gibbs_free_energy_gas` are obtained from that MLP calculation. For the
solution-phase value, a ωB97M-V/def2-TZVP SMD(toluene) single-point calculation
is performed on the MACEpre-DeePEST-OS-optimized geometry and combined with
the Gibbs thermal correction from the MACEpre-DeePEST-OS frequency analysis.

For MACE-OMol, only the electronic energy is included in this benchmark.

## Contents

| Folder | TS | Reactants | Products | Electronic energy | Gas-phase Gibbs | SMD(toluene) Gibbs |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `initial-guess-ts` | 22 | — | — | No | No | No |
| `DFT-opt` | 22 | 22 | 22 | Yes | Yes | Yes |
| `MACE-OMol-opt` | 22 | 22 | 22 | Yes | No | No |
| `MACEpre-DeePEST-OS` | 22 | 22 | 22 | Yes | Yes | Yes |

Each method folder contains `ts/`, `reactant/`, and `product/`
subfolders.

For DFT and MACEpre-DeePEST-OS, the XYZ comment line has the form:

```text
energy=<electronic energy> gibbs_free_energy_gas=<gas-phase Gibbs free energy> gibbs_free_energy_smd_toluene=<SMD(toluene) Gibbs free energy>
```

For MACE-OMol, the XYZ comment line contains only:

```text
energy=<electronic energy>
```
