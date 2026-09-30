# MACEPre-DeePEST-OS

Repository for the manuscript **“Data-Efficient Machine Learning Potentials for Organic Reactions through Active-Learning-Guided Fine-Tuning.”**

MACEPre-DeePEST-OS is a machine-learning interatomic potential for organic
reaction and transition-state calculations obtained by fine-tuning a pretrained
MACE-OMol model on an active-learning-selected DFT dataset. This repository
contains the training configurations, active-learning workflow, transition-state
optimization workflows, and the benchmark structures used in the study.

## Repository layout

```text
MACEPre-DeePEST-OS/
├── README.md
├── LICENSE
├── CITATION.cff
├── environment.yml
├── requirements.txt
├── configs/
│   ├── active_learning.yaml
│   └── training/
├── scripts/
│   ├── active_learning/
│   └── ts_optimization/
├── benchmarks/
├── examples/
├── data/
├── pretrained_models/
└── docs/
```

The benchmark data are stored directly in this repository. Large reaction-path
sampling data, the final active-learning training set, and the model files used
in the study are distributed separately through Zenodo so that the GitHub
repository remains lightweight.

## Installation

The authoritative software environment for reproducing the calculations is
`environment.yml`:

```bash
conda env create -f environment.yml
conda activate macepre_deepest_os
```

A shorter `requirements.txt` is also provided as a convenience for users who
already have a compatible Python/CUDA environment. For exact reproduction,
prefer the Conda environment.

## Zenodo data and model archive

The large datasets and model files associated with this study are archived on
Zenodo:

- **DOI:** `10.5281/zenodo.22993923`
- **DOI URL:** <https://doi.org/10.5281/zenodo.22993923>

The Zenodo record contains three main groups of artifacts:

1. **Reaction-path sampling pool.** Approximately 19 million molecular
   conformations generated during reaction-path sampling are distributed across
   ten compressed archives, from `mixed-db_conformations_part0.tar.xz` through
   `mixed-db_conformations_part9.tar.xz`.
2. **Active-learning training data.** `qbc-35w.xyz` contains **357,093**
   DFT-labeled structures selected from the sampled configuration space by the
   query-by-committee active-learning workflow.
3. **Models used in the manuscript.** The record includes
   `MACE-omol-0-extra-large-1024.model`, `DeePEST-OS.model`,
   `Active-learning.model`, and `MACEpre-DeePEST-OS.model`.

The released training YAML files use the same filename as the Zenodo record:
`qbc-35w.xyz`. See `data/README.md` for details.

For transition-state calculations, place the final fine-tuned model at:

```text
pretrained_models/MACEpre-DeePEST-OS.model
```

unless an explicit model path is supplied on the command line. See
`pretrained_models/README.md` for the complete model list and expected paths.

## Model training

The two final model configurations are under `configs/training/`:

- `Active-learning.yaml`: trains the active-learning baseline from scratch.
- `MACEpre-DeePEST-OS.yaml`: fine-tunes the pretrained MACE-OMol model on the
  same final active-learning dataset.

MACE provides the training entry point, so no additional training wrapper is
needed. See `configs/training/README.md` for the exact commands and expected
input layout.

## Active learning

The public active-learning workflow is under `scripts/active_learning/`. It
contains committee training, committee-based force-disagreement scoring,
candidate selection, and convergence analysis.

The workflow is intentionally semi-automated. Quantum-chemical labeling is an
explicit external checkpoint because job submission and output parsing depend
on the electronic-structure program and HPC environment. For reproduction of
the reported model training, rerunning this QC-labeling stage is not required:
the final labeled training dataset is released separately through Zenodo.

See `scripts/active_learning/README.md` for the recorded committee seeds,
selection rule, and generation workflow.

## Transition-state optimization

Two routes are provided under `scripts/ts_optimization/`:

1. **ASE + Sella** using `sella_ts_irc.py`.
2. **Gaussian + external MACE interface** through
   [Gauoptimizer-MLPs-interface](https://github.com/Senppoa/Gauoptimizer-MLPs-interface).

Both routes use the final MACEPre-DeePEST-OS model. See
`scripts/ts_optimization/README.md` for details.

A small DORTS-100 transition-state initial guess is provided under `examples/`
as a ready-to-use Sella input example.

## Benchmarks

The repository currently contains seven benchmark collections:

- `DORTS-100`
- `RGD1-100`
- `T1x-100`
- `OrgReact`
- `Ugi`
- `Biginelli`
- `Metal-Lewis-Acid`

Each benchmark directory contains its own README describing the calculation
workflow, energy definitions, and structure counts. A cross-benchmark overview
is provided in `benchmarks/README.md`.

Benchmark XYZ metadata use eV. Initial-guess XYZ comment lines are blank.
Optimized structures contain only the benchmark-relevant energy/free-energy
fields described in the corresponding README.

## Reproducibility

A repository-level reproduction guide is provided in
`docs/reproducibility.md`. The benchmark structures and energies are released
directly in this repository, while the final training data and model files are
distributed through Zenodo.

The manuscript and Supporting Information describe the statistical definitions
used for structure and barrier-error analysis; those analysis scripts are not
duplicated here.

## Citation

The current reference for this repository is the ChemRxiv preprint:

> Kaipai Ren, Yujing Zhao, Kun Tang, Juntao Wang, Guangran Zhang, and Qilei Liu. **Data-Efficient Machine Learning Potentials for Organic Reactions through Active-Learning-Guided Fine-Tuning.** ChemRxiv (2026). DOI: `10.26434/chemrxiv.15009333/v1`.

The same metadata are provided in `CITATION.cff`. The citation should be updated to the peer-reviewed article after publication.

## License

The repository is released under the MIT License. See `LICENSE`.
