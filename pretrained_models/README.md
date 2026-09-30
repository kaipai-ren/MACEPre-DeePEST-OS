# Trained models

The model files used in the study are distributed through Zenodo rather than
committed to the GitHub repository.

## Zenodo record

```text
DOI: 10.5281/zenodo.22993923
URL: https://doi.org/10.5281/zenodo.22993923
```

The record contains the four model files used in the manuscript:

- `MACE-omol-0-extra-large-1024.model` — pretrained MACE-OMol foundation model;
- `DeePEST-OS.model` — DeePEST-OS comparison model;
- `Active-learning.model` — model trained from scratch on the final
  active-learning dataset;
- `MACEpre-DeePEST-OS.model` — final fine-tuned model developed in this work.

The transition-state optimization scripts use the final fine-tuned model and,
by default, expect it at:

```text
pretrained_models/MACEpre-DeePEST-OS.model
```

After downloading the model from Zenodo, place it at that path or pass an
explicit model path to the relevant command.

For fine-tuning reproduction, the training configuration expects the foundation
model as:

```text
MACE-omol-0-extra-large-1024.model
```

at the path specified by `foundation_model` in
`configs/training/MACEpre-DeePEST-OS.yaml`.
