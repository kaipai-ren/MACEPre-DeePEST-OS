# Example

`DORTS-rxn-1.xyz` is an initial transition-state guess copied from
`benchmarks/DORTS-100/initial-guess-ts/`.

To run the Sella workflow with the released MACEPre-DeePEST-OS model:

```bash
mkdir -p inputs
cp examples/DORTS-rxn-1.xyz inputs/

python scripts/ts_optimization/sella_ts_irc.py \
  --input-dir inputs \
  --output-dir outputs \
  --model pretrained_models/MACEpre-DeePEST-OS.model \
  --device cuda
```

The default charge and spin values used by the script are 0 and 1. Change them
with `--charge` and `--spin` when required for another system.

For the Gaussian route, use
`scripts/ts_optimization/gaussian_external/ts_opt_template.gjf` and replace
its coordinates, charge, and multiplicity with the system of interest.
