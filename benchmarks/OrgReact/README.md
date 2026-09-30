# OrgReact benchmark

OrgReact contains 500 transition-state initial guesses spanning 10 bond-forming/bond-breaking categories. The benchmark is organized into two complementary calculation workflows, `Sella/` and `Gaussian/`, which use the same set of initial transition-state guesses.

## Sella workflow

In the `Sella/` benchmark, the initial transition-state structures are optimized with the Sella optimizer. DFT, MACE-OMol, and MACEpre-DeePEST-OS are used separately as the calculator during the Sella transition-state optimization. The comparison in this workflow is based only on the electronic energy of the optimized transition state; thermal corrections and Gibbs free energies are not included.

The corresponding results are stored in:

- `initial-guess-ts/`: the 500 transition-state initial guesses.
- `DFT-opt/`: successfully optimized DFT transition states.
- `MACE-OMol-opt/`: successfully optimized transition states using MACE-OMol.
- `MACEpre-DeePEST-OS/`: successfully optimized transition states using MACEpre-DeePEST-OS.

For optimized structures, the XYZ comment line contains the electronic energy in eV as `energy=<value>`.

## Gaussian workflow

In the `Gaussian/` benchmark, geometry optimization and frequency analysis are performed through Gaussian, and transition states, reactants, and products are retained for each complete reaction so that both electronic and Gibbs free-energy barriers can be evaluated.

For the DFT reference, geometry optimization and frequency analysis are first performed at the M06-2X/def2-SVP level. A single-point electronic energy is then calculated at the ωB97M-V/def2-TZVP level on the optimized geometry. The reported DFT Gibbs free energy is constructed from the ωB97M-V/def2-TZVP electronic energy plus the Gibbs thermal correction obtained from the M06-2X/def2-SVP frequency calculation.

For MACE-OMol and MACEpre-DeePEST-OS, Gaussian calls the corresponding machine-learning potential through the external interface during geometry optimization and frequency analysis. The resulting optimized transition-state, reactant, and product structures are archived together with the electronic energy and Gibbs free energy obtained from the corresponding MLP calculation.

For these structures, the XYZ comment line is:

```text
energy=<electronic energy in eV> free_energy=<Gibbs free energy in eV>
```

Detailed structure counts for each workflow are provided in the README inside the corresponding `Sella/` and `Gaussian/` directories.
