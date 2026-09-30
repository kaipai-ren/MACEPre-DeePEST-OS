# Reproducibility guide

This document summarizes how the released repository components correspond to
the reported workflow. Benchmark-specific details remain in the README inside
each benchmark directory.

## 1. Environment

For the closest reproduction of the software environment, create the Conda
environment from the repository root:

```bash
conda env create -f environment.yml
conda activate macepre_deepest_os
```

`environment.yml` is the authoritative environment specification.
`requirements.txt` is a shorter convenience list and does not replace the
full Conda environment.

## 2. External data and model artifacts

The large data and model artifacts are hosted on Zenodo under DOI
`10.5281/zenodo.22993923` (<https://doi.org/10.5281/zenodo.22993923>).

The record contains:

1. approximately 19 million reaction-path-sampled molecular conformations in
   ten compressed `mixed-db_conformations_part*.tar.xz` archives;
2. `qbc-35w.xyz`, containing 357,093 DFT-labeled active-learning structures;
3. the four model files used in the study:
   `MACE-omol-0-extra-large-1024.model`, `DeePEST-OS.model`,
   `Active-learning.model`, and `MACEpre-DeePEST-OS.model`.

The training YAML files use the same filename as the Zenodo release,
`qbc-35w.xyz`. See `data/README.md`.

The final fine-tuned model used by the TS workflows is expected at:

```text
pretrained_models/MACEpre-DeePEST-OS.model
```

See `pretrained_models/README.md`.

## 3. Final model training

The authoritative final training configurations are:

```text
configs/training/Active-learning.yaml
configs/training/MACEpre-DeePEST-OS.yaml
```

The first trains the active-learning baseline from scratch. The second
fine-tunes the pretrained MACE-OMol foundation model on the same final
active-learning dataset.

Training is launched directly with the MACE command-line entry point. See
`configs/training/README.md` for the exact commands and expected file layout.

## 4. Active-learning workflow

The active-learning workflow is under `scripts/active_learning/` and contains:

```text
committee training
→ committee force-disagreement scoring
→ candidate selection
→ convergence analysis
→ external QC-labeling checkpoint
```

The released configuration contains the recorded committee random seeds for
the reported generations. Candidate selection uses the P75/P99 force-score
rule documented in `scripts/active_learning/README.md`.

The QC-labeling step is deliberately external to the public Python workflow,
because job submission and output parsing depend on the user's
electronic-structure/HPC environment. For reproducing the reported final
training, use the released labeled dataset rather than rerunning QC.

## 5. Transition-state optimization

Two transition-state optimization routes are provided:

### ASE/Sella

```bash
python scripts/ts_optimization/sella_ts_irc.py \
  --input-dir inputs \
  --output-dir outputs \
  --model pretrained_models/MACEpre-DeePEST-OS.model \
  --device cuda
```

The script performs Sella TS optimization, vibrational analysis, forward and
reverse IRC calculations, and endpoint optimization.

### Gaussian external interface

Gaussian-based optimization uses the separately maintained
`Gauoptimizer-MLPs-interface`. The repository does not vendor that third-party
source. See `scripts/ts_optimization/gaussian_external/README.md` and the
provided Gaussian template.

## 6. Benchmark data

Released benchmark structures are under `benchmarks/`. The repository
contains the initial structures and the optimized structures/energies used for
the reported comparisons.

The benchmark families are:

```text
DORTS-100
RGD1-100
T1x-100
OrgReact
Ugi
Biginelli
Metal-Lewis-Acid
```

All energy and free-energy values stored in XYZ comment lines are in eV.
Initial-guess XYZ comment lines are blank. Benchmark-specific quantum-chemistry
levels and metadata fields are documented in each benchmark README.

## 7. Error metrics and plots

The definitions used for structural RMSD, electronic barrier error, and Gibbs
free-energy barrier error are provided in the manuscript and Supporting
Information. Those analysis scripts are not duplicated here; the repository
focuses on releasing the structures, energies, model/training configuration,
and optimization workflows needed to reproduce or independently analyze the
benchmarks.

## 8. Example input

`examples/DORTS-rxn-1.xyz` is copied from the DORTS-100 initial-guess set and
can be used to test the Sella workflow. See `examples/README.md`.
