# Transition-state optimization

Two transition-state optimization routes are provided for
MACEPre-DeePEST-OS.

## Method 1: Sella + ASE

`sella_ts_irc.py` is a cleaned command-line version of the Sella workflow
used in the study. It performs:

```text
initial TS guess
      ↓
Sella TS optimization
      ↓
frequency check
      ↓
forward + reverse IRC
      ↓
BFGS optimization of both IRC endpoints
      ↓
trajectories / structures / barrier summary
```

The public version uses **only**:

```text
MACEpre-DeePEST-OS.model
```

through `MACECalculator`. The previous mixed MACE + xTB
`SumCalculator`/delta-learning setup from the working notebook is not used.

By default the script looks for:

```text
<repository-root>/pretrained_models/MACEpre-DeePEST-OS.model
```

and expects input XYZ files under `inputs/`.

Example:

```bash
python scripts/ts_optimization/sella_ts_irc.py \
  --input-dir inputs \
  --output-dir outputs \
  --model pretrained_models/MACEpre-DeePEST-OS.model \
  --device cuda
```

The default calculation parameters retained from the notebook are:

```text
TS fmax       = 0.0025 eV/Å
IRC fmax      = 0.005 eV/Å
maximum steps = 1000
retry count   = 2
charge        = 0
spin          = 1
```

These values can be overridden from the command line.

## Method 2: Gaussian optimizer + external MACE interface

For Gaussian-based TS optimization, this repository uses the external project:

https://github.com/Senppoa/Gauoptimizer-MLPs-interface

rather than duplicating its source code.

See:

```text
gaussian_external/README.md
gaussian_external/ts_opt_template.gjf
```

The external interface runs `MACEpre-DeePEST-OS.model` as a persistent local
MACE calculator and lets Gaussian obtain energies, gradients, and Hessian
information through its `external=` interface.

The two routes therefore use the **same final MACE model**, but different
optimization engines:

```text
MACEpre-DeePEST-OS.model
        ├── ASE / Sella
        └── Gaussian optimizer via Gauoptimizer-MLPs-interface
```

## Scope

The scripts here are intended for TS optimization and related validation.
Benchmark-specific structures and energy definitions are released under
`benchmarks/`. RMSD and barrier-error definitions are described in the
manuscript and Supporting Information and are not duplicated here as a
separate evaluation-script package.
