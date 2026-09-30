# Biginelli benchmark

The Biginelli benchmark contains the seven elementary transition-state pathways
shown as TS1-TS7 in the reaction-network figure. The original internal
`A1UE-*` labels have been normalized to the public names
`Reaction-TS1` through `Reaction-TS7`.

For each pathway, the transition state, the reactant state used to define the
reported activation free energy, and the corresponding product state are
archived. Seven transition-state starting geometries are also provided in
`initial-guess-ts/`.

## Included pathways

| Public name | Reaction step |
| --- | --- |
| `Reaction-TS1` | C-N bond formation |
| `Reaction-TS2` | Proton transfer |
| `Reaction-TS3` | Dehydration |
| `Reaction-TS4` | C-C bond formation |
| `Reaction-TS5` | Cyclization |
| `Reaction-TS6` | Dehydration |
| `Reaction-TS7` | Deprotonation |

The seven pathways correspond exactly to the seven activation free energies
reported in the benchmark parity comparison. Alternative conformers and
intermediate structures that are not used to define those seven reported
barriers are not archived as additional benchmark reactions.

## Calculation workflow

For the DFT reference, geometry optimization and frequency analysis were
performed at the M06-2X/def2-SVP level. Electronic energies were evaluated at
the ωB97M-V/def2-TZVP level, and the gas-phase Gibbs free energy was obtained
by combining the ωB97M-V/def2-TZVP electronic energy with the Gibbs thermal
correction from the M06-2X/def2-SVP frequency calculation.

For MACE-OMol and MACEpre-DeePEST-OS, Gaussian calls the corresponding
machine-learning potential through the external interface for geometry
optimization and frequency analysis.

The `gibbs_free_energy_gas` value stored in each optimized XYZ file is the
gas-phase Gibbs free energy used in the reported Biginelli benchmark
workbooks and activation-barrier comparison. Values are in eV.

## Contents

| Folder | TS | Reactants | Products |
| --- | ---: | ---: | ---: |
| `initial-guess-ts` | 7 | — | — |
| `DFT-opt` | 7 | 7 | 7 |
| `MACE-OMol-opt` | 7 | 7 | 7 |
| `MACEpre-DeePEST-OS` | 7 | 7 | 7 |

Each method folder contains `ts/`, `reactant/`, and `product/`
subfolders. The XYZ comment line for optimized structures has the form:

```text
gibbs_free_energy_gas=<Gibbs free energy in eV>
```

The second line of each `initial-guess-ts` XYZ file is blank.
