# Active-learning workflow

This directory contains the active-learning workflow used to select informative
reaction conformations for quantum-chemical labeling before fine-tuning
MACE-OMol.

The public workflow is intentionally **semi-automated**. Committee training,
committee-based uncertainty evaluation, candidate selection, and convergence
analysis are automated. High-level quantum-chemistry (QC) labeling is kept as
an explicit checkpoint because the QC job-submission and output-parsing
workflow depends on the user's external electronic-structure/HPC environment.

## Files

```text
configs/
└── active_learning.yaml

scripts/active_learning/
├── README.md
├── common.py
├── train_committee.py
├── score_candidates.py
├── select_candidates.py
├── check_convergence.py
└── run_generation.py
```

- **train_committee.py** trains four MACE committee members in parallel.
- **score_candidates.py** evaluates candidate extxyz shards with the committee
  and caches the force-disagreement scores.
- **select_candidates.py** applies the manuscript selection rule and writes the
  selected structures for QC labeling.
- **check_convergence.py** follows the generation-to-generation P50/P90 trend.
- **run_generation.py** runs one generation through the QC-labeling checkpoint.

## Environment

Create and activate the repository environment:

```bash
conda env create -f environment.yml
conda activate macepre_deepest_os
```

The active-learning scripts expect `mace_run_train` from the active
environment to be available on `PATH`. No private cluster path is hard-coded
in the public scripts.

## Directory convention

A generation directory contains the cumulative labeled training set for that
generation:

```text
active_learning_runs/
├── gen001/
│   ├── gen001.xyz
│   ├── models/
│   ├── qbc_eval_scores/
│   └── qbc_eval_log/
└── gen002/
    └── candidate_xyzdata/
```

For `gen001`, the input training set must be named `gen001/gen001.xyz`.
After candidate selection, structures requiring QC labeling are written to the
next generation, for example
`gen002/candidate_xyzdata/`.

After QC calculations are complete, combine the newly labeled structures with
the cumulative labeled data and save the next training set as
`gen002/gen002.xyz`.

## Committee training and random seeds

Four committee members are trained with identical model/training settings and
different random seeds.

The seeds listed in `configs/active_learning.yaml` for `gen001` through
`gen007` are the exact seeds recorded from the original calculations. **They
were randomly generated during the original study and were not selected,
optimized, or tuned according to model performance.** They are retained only
to facilitate reproduction of the reported committee runs.

If a generation is not listed in `paper_committee_seeds`, new distinct seeds
are generated and recorded in `committee_seeds.tsv`.

The model and training settings in the public configuration follow the
submitted `train_committee_parallel.py` workflow; the historical per-generation
training YAML files are used only as the source of the original random seeds.

Run committee training alone with:

```bash
python scripts/active_learning/train_committee.py \
  --config configs/active_learning.yaml \
  --generation-dir active_learning_runs/gen001
```

## QBC force-disagreement score

Each candidate structure is evaluated by the four committee models. For every
atom, the standard deviation-like committee force disagreement is computed
from the four force predictions. The structure-level quantities are

```text
force_rms = RMS of atomic committee-force disagreement
force_p95 = 95th percentile of atomic committee-force disagreement
force_score = 0.5 * force_rms + 0.5 * force_p95
```

The score is an **uncertainty/disagreement score**, not an error against a DFT
reference.

Candidate structures should be packed into multi-frame extxyz/xyz shards. The
locations and filename pattern are configured under `qbc:` in
`configs/active_learning.yaml`.

Run scoring alone with:

```bash
python scripts/active_learning/score_candidates.py \
  --config configs/active_learning.yaml \
  --generation-dir active_learning_runs/gen001
```

Score caches are written to

```text
gen001/qbc_eval_scores/
```

so candidate selection can be repeated without rerunning committee inference.

## Candidate-selection rule

The public code implements the selection rule used for the manuscript:

1. Calculate the P75 and P99 percentiles of the QBC force score over the full
   candidate pool.
2. Among structures with
   `P75 <= force_score <= P99`, select the **50,000 structures with the
   largest force scores**.
3. Among structures with `force_score > P99`, **randomly select 500
   structures**.
4. The two quotas are independent, so a generation contains at most **50,500**
   selected structures.
5. If either pool contains fewer structures than its requested quota, all
   available structures from that pool are used. No lower-score fallback is
   used to fill the missing quota.

Run selection alone with:

```bash
python scripts/active_learning/select_candidates.py \
  --config configs/active_learning.yaml \
  --generation-dir active_learning_runs/gen001
```

The random draw from the `>P99` pool uses an explicit random seed when one is
provided. If no selection seed is configured, a seed is generated for that run
and written to `selected_qbc_summary.tsv`. This seed is separate from the
committee-training seeds.

Selected structures are written to

```text
gen002/candidate_xyzdata/
```

and the selection table is written to

```text
gen001/qbc_eval_log/selected_qbc_candidates.tsv
```

## QC-labeling checkpoint

The selected structures must next be labeled with the high-level
quantum-chemistry procedure used for the study. This step is intentionally not
launched by the active-learning scripts.

After labeling:

1. convert the QC results to the energy/force extxyz format required by MACE;
2. append the new labeled structures to the cumulative training set;
3. save the result as the next generation, e.g. `gen002/gen002.xyz`;
4. train the next committee and repeat the workflow.

This separation keeps the public Python workflow independent of a particular
QC program, scheduler, filesystem, or HPC installation.

## Convergence criterion

For every generation, `selected_qbc_summary.tsv` stores the P50 and P90 of
the selected QBC force scores.

Between consecutive generations, the relative change is evaluated as

```text
(previous - current) / previous
```

A generation is considered stable when the absolute relative changes of both
P50 and P90 are below 5%. Active learning is considered converged after this
condition is satisfied for **three consecutive generations**.

Run the convergence analysis with:

```bash
python scripts/active_learning/check_convergence.py \
  --config configs/active_learning.yaml \
  --root active_learning_runs
```

The trend table is written to

```text
active_learning_runs/qbc_selected_force_score_trend.tsv
```

## Run a complete generation

After preparing the cumulative labeled training set and the candidate shards:

```bash
python scripts/active_learning/run_generation.py \
  --config configs/active_learning.yaml \
  --generation-dir active_learning_runs/gen001
```

This executes:

```text
committee training
      ↓
QBC candidate scoring
      ↓
candidate selection
      ↓
convergence analysis
      ↓
QC-labeling checkpoint
```

If committee models or score caches already exist, they can be reused:

```bash
python scripts/active_learning/run_generation.py \
  --config configs/active_learning.yaml \
  --generation-dir active_learning_runs/gen001 \
  --skip-training \
  --skip-scoring
```

## Reproducibility notes

- The stored committee seeds reproduce the random seeds used for the reported
  committee calculations; the numerical values have no special methodological
  meaning.
- Machine/GPU paths are not stored in the public scripts.
- The QBC score caches are separated from candidate selection so that selection
  rules can be inspected or rerun without repeating inference over the full
  candidate pool.
- The QC step remains external and must use the same electronic-structure
  settings described for the study when reproducing the reported training data.
