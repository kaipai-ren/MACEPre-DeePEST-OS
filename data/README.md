# Training data

The large reaction-path sampling data and the final DFT-labeled active-learning
training dataset are distributed separately through Zenodo.

## Zenodo record

```text
DOI: 10.5281/zenodo.22993923
URL: https://doi.org/10.5281/zenodo.22993923
```

## Released data

The reaction-path sampling pool contains approximately 19 million molecular
conformations and is distributed across ten compressed archives, from
`mixed-db_conformations_part0.tar.xz` through
`mixed-db_conformations_part9.tar.xz`.

The final active-learning dataset is released as:

```text
qbc-35w.xyz
```

It contains **357,093 DFT-labeled structures** in extended XYZ format selected
from the sampled configuration space by the query-by-committee workflow.

The released training YAML files use the same filename:

```text
qbc-35w.xyz
```

After downloading the Zenodo file, place `qbc-35w.xyz` in the working directory
used for MACE training, or edit the `train_file` path if a different location is
preferred.

For reproduction of the reported model training, rerunning the
quantum-chemical labeling stage is not required. The released Zenodo dataset
contains the DFT labels used for training. The QC-labeling checkpoint in
`scripts/active_learning/` is intended for users who apply the active-learning
workflow to new candidate pools.
