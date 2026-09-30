# Model training

No additional Python wrapper is required for the two models reported in the
paper. Both models are trained directly with MACE using the YAML configuration
files in this directory.

## Training data

Both configurations use:

```text
qbc-35w.xyz
```

This file is the final DFT-labeled active-learning training dataset used in the
study. The public Zenodo release is `qbc-35w.xyz` and contains 357,093
structures. The training configurations use the same filename. See
`data/README.md` for the Zenodo DOI and data-release details.

The paths in the YAML files are intentionally relative. The simplest
reproduction layout is:

```text
working_directory/
├── qbc-35w.xyz
├── MACE-omol-0-extra-large-1024.model   # required only for fine-tuning
└── configs/
    └── training/
        ├── Active-learning.yaml
        └── MACEpre-DeePEST-OS.yaml
```

You may instead edit the relative input paths in the YAML files.

## 1. Active-learning baseline

`Active-learning.yaml` trains a MACE model **from scratch** on the final
active-learning dataset. This is the "Active learning" baseline used to
separate the benefit of active data selection from the benefit of pretrained
initialization.

The configuration uses distributed training:

```yaml
distributed: true
launcher: torchrun
```

For a single node with multiple GPUs, run for example:

```bash
torchrun --standalone --nnodes=1 --nproc_per_node=4 \
  "$(which mace_run_train)" \
  --config=configs/training/Active-learning.yaml
```

Adjust `--nproc_per_node` to the number of GPUs allocated to the job.

## 2. MACEPre-DeePEST-OS

`MACEpre-DeePEST-OS.yaml` fine-tunes the pretrained
`MACE-omol-0-extra-large-1024.model` on the same final active-learning
training dataset.

The configuration uses:

```yaml
foundation_model: ./MACE-omol-0-extra-large-1024.model
multiheads_finetuning: false
foundation_model_elements: true
E0s: foundation
distributed: false
```

Run:

```bash
mace_run_train --config=configs/training/MACEpre-DeePEST-OS.yaml
```

The pretrained MACE-OMol model file itself is not duplicated in this GitHub
repository, but `MACE-omol-0-extra-large-1024.model` is included in the same
Zenodo record as the training data and reported models. Place it at the path
specified by `foundation_model`, or edit that path in the YAML file.

## Reproducibility

These YAML files contain the model and optimization settings used for the two
models reported in the paper. They should be treated as the authoritative
training configurations for these final models.

The active-learning committee-training settings are separate and are documented
under `scripts/active_learning/`; those committee models are used for data
selection and are not the final "Active learning" baseline model described
above.

No `scripts/training/` wrapper is provided because `mace_run_train` is
already the training entry point supplied by MACE.
