# Metal Lewis acid catalysis benchmark

This benchmark contains 21 reaction pathways covering three reaction classes
and seven Lewis-acid conditions:

- Diels-Alder
- Carbonyl-ene
- Alder-ene

The included Lewis-acid conditions are `None`, `GaCl3`, `InCl3`,
`SnCl4`, `TiCl4`, `ZnCl2`, and `ZrCl4`. Public filenames directly
encode the reaction class and catalyst, for example
`Diels-Alder-GaCl3.xyz`, `Carbonyl-ene-SnCl4.xyz`, and
`Alder-ene-ZrCl4.xyz`.

## Barrier definition

For each pathway, the reported gas-phase activation free energy is defined as

```text
ΔG‡ = G(TS) - G(reactant-1) - G(reactant-2)
```

`reactant-1` is the reaction-class-specific co-reactant shared across the
seven catalyst conditions, while `reactant-2` is the catalyst-dependent
reaction partner. The source benchmark does not use product structures in the
reported activation-free-energy comparison, so the archive contains
`reactant-1/`, `reactant-2/`, and `ts/` rather than a product folder.

## Calculation workflow

For the DFT reference, geometry optimization and frequency analysis were
performed at the B3LYP-D3(BJ)/def2-SVP level. Electronic energies were then
evaluated at the ωB97M-V/def2-TZVP level. The reported DFT gas-phase Gibbs free
energy combines the ωB97M-V/def2-TZVP electronic energy with the Gibbs thermal
correction obtained from the B3LYP-D3(BJ)/def2-SVP frequency calculation.

For MACE-OMol and MACEpre-DeePEST-OS, Gaussian calls the corresponding
machine-learning potential through the external interface for geometry
optimization and frequency analysis. The reported gas-phase Gibbs free energy
is obtained from the corresponding MLP calculation.

All optimized XYZ files contain the Gibbs free energy used in the reported
barrier comparison:

```text
gibbs_free_energy_gas=<Gibbs free energy in eV>
```

The 21 structures in `initial-guess-ts/` are the starting geometries used for
the DFT transition-state optimizations. Their XYZ comment lines are blank.

## Contents

| Folder | Reactant 1 | Reactant 2 | TS |
| --- | ---: | ---: | ---: |
| `initial-guess-ts` | — | — | 21 |
| `DFT-opt` | 21 | 21 | 21 |
| `MACE-OMol-opt` | 21 | 21 | 21 |
| `MACEpre-DeePEST-OS` | 21 | 21 | 21 |

The optimized transition-state structures also provide the structures used for
the metal-O distance comparison across Lewis acids.
