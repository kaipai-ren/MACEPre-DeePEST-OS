# Gaussian TS optimization through Gauoptimizer-MLPs-interface

This route uses the external interface maintained at:

https://github.com/Senppoa/Gauoptimizer-MLPs-interface

The third-party interface is **not vendored into this repository**. Install or
clone it separately so users can follow its upstream implementation and
citation instructions.

The interface uses two upstream scripts:

- `server.py`: loads the MACE model once and keeps a local model server alive;
- `mlpint_local.py`: is called by Gaussian through the `external=` keyword.

For this project, the model passed to the server is the final
`MACEpre-DeePEST-OS.model`.

## 1. Obtain the interface

```bash
git clone https://github.com/Senppoa/Gauoptimizer-MLPs-interface.git
cd Gauoptimizer-MLPs-interface
```

Use the same Python environment as the MACE calculations, or another
environment that provides the dependencies required by the upstream
repository. Gaussian itself must be installed and licensed separately.

## 2. Start the MACE server

Use an explicit path to the final model:

```bash
python server.py start \
  --model /absolute/path/to/MACEpre-DeePEST-OS.model \
  --device cuda \
  --threads 1 \
  --hessian numeric \
  --background
```

The upstream interface accepts an explicit model-file path. Its server creates
an ASE `MACECalculator` for that model and exposes energy, gradient, and
Hessian information to Gaussian.

Check the server:

```bash
python server.py status
```

## 3. Prepare a Gaussian TS optimization

A template is provided in `ts_opt_template.gjf`.

The important part of the route section is:

```text
external='python /absolute/path/to/Gauoptimizer-MLPs-interface/mlpint_local.py'
opt=(ts,calcfc,nomicro,maxcycle=1000)
```

`nomicro` is kept because optimization is driven through Gaussian's external
calculator interface.

Replace the charge, multiplicity, and coordinates with the system of interest.
For the neutral closed-shell calculations used by the Sella example, the
corresponding line is `0 1`.

The template also contains a Link1 frequency calculation that reuses the same
checkpoint and external MACE interface.

## 4. Run Gaussian

For Gaussian 16, a typical shell command is:

```bash
g16 < ts_opt.gjf > ts_opt.log
```

The exact Gaussian launcher may differ between HPC systems.

## 5. Stop the model server

After the Gaussian calculations finish:

```bash
python server.py exit
```

## Notes

- This repository does not duplicate `server.py` or `mlpint_local.py`; use
  the upstream project directly.
- Pass the final model as an explicit path rather than relying on an upstream
  built-in model alias.
- The `numeric` Hessian mode is used in the example because the external
  interface supports numerical Hessian evaluation through ASE vibrations.
- Gaussian job scheduling, memory, CPU allocation, checkpoint paths, and
  convergence keywords should be adapted to the local HPC environment.
