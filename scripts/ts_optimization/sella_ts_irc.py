#!/usr/bin/env python3
"""Transition-state optimization and IRC analysis with Sella + MACE.

This script is adapted from the notebook workflow used in the study.  The
public version uses only the final MACEPre-DeePEST-OS model; the previous
MACE + xTB SumCalculator/delta-learning calculator is intentionally removed.

Workflow for each input XYZ:
    1. Sella transition-state optimization
    2. Vibrational frequency check
    3. Forward and reverse IRC with Sella
    4. BFGS optimization of both IRC endpoints
    5. Save trajectories, structures, plots, and a concise summary log

The default model path is:
    <repository-root>/pretrained_models/MACEpre-DeePEST-OS.model
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import time
import traceback
from pathlib import Path

# Keep the same conservative CPU-thread policy as the original notebook.
for _name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

# JAX is not used for the MACE calculator here, but Sella may import JAX.
# Keeping JAX on CPU avoids unnecessary GPU-memory allocation.
os.environ.setdefault("JAX_PLATFORMS", "cpu")

import matplotlib.pyplot as plt
import numpy as np
from ase.io import read, write, animation
from ase.io.trajectory import TrajectoryReader
from ase.optimize.bfgs import BFGS
from ase.utils.forcecurve import fit_images
from ase.vibrations import Vibrations
from mace.calculators import MACECalculator
from natsort import natsorted, ns
from sella import IRC, Sella


def parse_args():
    repository_root = Path(__file__).resolve().parents[2]
    default_model = repository_root / "pretrained_models" / "MACEpre-DeePEST-OS.model"

    parser = argparse.ArgumentParser(
        description="Batch Sella TS optimization and IRC calculations with MACEPre-DeePEST-OS."
    )
    parser.add_argument("--input-dir", default="inputs", help="Directory containing input *.xyz files.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for per-reaction results.")
    parser.add_argument(
        "--model",
        default=str(default_model),
        help="Path to MACEpre-DeePEST-OS.model.",
    )
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument(
        "--spin",
        type=int,
        default=1,
        help="Spin/multiplicity value stored in atoms.info for the MACE model.",
    )
    parser.add_argument("--ts-fmax", type=float, default=0.0025)
    parser.add_argument("--irc-fmax", type=float, default=0.005)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--retry", type=int, default=2)
    parser.add_argument(
        "--max-imaginary-modes",
        type=int,
        default=6,
        help="Retry when the optimized TS has more imaginary modes than this value.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Re-run reactions with existing output directories.")
    return parser.parse_args()


def make_logger(log_path: Path, logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


def set_model_metadata(atoms, charge: int, spin: int):
    atoms.info["charge"] = int(charge)
    atoms.info["spin"] = int(spin)


def ts_irc_pipeline(
    input_xyz: Path,
    output_root: Path,
    reaction_output: Path,
    calculator,
    charge: int = 0,
    spin: int = 1,
    ts_fmax: float = 0.0025,
    irc_fmax: float = 0.005,
    steps: int = 1000,
    retry: int = 2,
    max_imaginary_modes: int = 6,
):
    reaction_name = input_xyz.stem
    logger = make_logger(reaction_output / f"{reaction_name}.log", f"tsopt.{reaction_name}")

    all_log = output_root / "all_log.txt"
    if not all_log.exists():
        with all_log.open("w", encoding="utf-8") as handle:
            handle.write("name\tref_time\trefine_steps\tirc_time\tirc_steps\tEf\tEr\tflag\n")

    for attempt in range(1, retry + 1):
        try:
            # Step 1: TS optimization.
            logger.info("[Step 1] TS optimization for %s", reaction_name)
            atoms = read(input_xyz)
            set_model_metadata(atoms, charge, spin)
            atoms.calc = calculator

            ts_traj_path = reaction_output / f"{reaction_name}_ts.traj"
            ts_final_xyz = reaction_output / f"{reaction_name}_ts.xyz"

            start = time.time()
            optimizer = Sella(
                atoms,
                trajectory=str(ts_traj_path),
                eta=2e-2,
                gamma=0.0001,
                delta0=0.02,
            )
            optimizer.run(fmax=ts_fmax, steps=steps)
            ref_time = round(time.time() - start, 2)

            ts_traj = TrajectoryReader(str(ts_traj_path))
            refine_steps = len(ts_traj) - 1
            ts_final = ts_traj[-1]
            set_model_metadata(ts_final, charge, spin)
            ts_final.calc = calculator
            write(ts_final_xyz, ts_final)
            logger.info("TS optimization finished in %.2f s; steps=%d", ref_time, refine_steps)

            # Step 2: Frequency check.
            logger.info("[Step 2] Frequency check")
            vib_dir = reaction_output / "vib"
            if vib_dir.exists():
                shutil.rmtree(vib_dir)

            vibrations = Vibrations(ts_final, name=str(vib_dir))
            vibrations.run()
            frequencies = vibrations.get_frequencies()
            imaginary_count = int(np.sum(np.imag(frequencies) != 0))
            vibrations.summary(log=str(reaction_output / f"{reaction_name}_vibration.log"))
            logger.info("Imaginary frequencies: %d", imaginary_count)

            if imaginary_count > max_imaginary_modes:
                logger.warning(
                    "Too many imaginary modes (%d > %d); retrying.",
                    imaginary_count,
                    max_imaginary_modes,
                )
                continue

            # Step 3: IRC.
            logger.info("[Step 3] IRC")
            irc_traj_path = reaction_output / f"{reaction_name}_irc.traj"
            irc = IRC(
                ts_final,
                trajectory=str(irc_traj_path),
                dx=0.1,
                eta=1e-4,
                gamma=0.1,
            )
            start = time.time()
            irc.run(fmax=irc_fmax, steps=steps, direction="forward")
            split = len(TrajectoryReader(str(irc_traj_path)))
            irc.run(fmax=irc_fmax, steps=steps, direction="reverse")
            irc_time = round(time.time() - start, 2)

            irc_traj = TrajectoryReader(str(irc_traj_path))
            irc_steps = len(irc_traj)
            irc_all = [irc_traj[i] for i in range(split - 1, -1, -1)]
            irc_all.extend(irc_traj[split:])
            for image in irc_all:
                set_model_metadata(image, charge, spin)
                image.calc = calculator

            logger.info("IRC finished in %.2f s; split=%d; frames=%d", irc_time, split, irc_steps)

            # Step 4: IRC visualization.
            try:
                fit = fit_images(irc_all)
                fit.plot()
                plt.savefig(reaction_output / f"{reaction_name}_irc.png", dpi=300)
                animation.write_animation(
                    reaction_output / f"{reaction_name}_irc.gif",
                    images=irc_all,
                    writer="pillow",
                    interval=50,
                )
                plt.close()
            except Exception:
                logger.warning("IRC visualization failed.", exc_info=True)

            # Step 5: Optimize both IRC endpoints.
            endpoint_atoms = [irc_all[0].copy(), irc_all[-1].copy()]
            endpoint_energies = []
            for index, endpoint in enumerate(endpoint_atoms, 1):
                set_model_metadata(endpoint, charge, spin)
                endpoint.calc = calculator
                traj_path = reaction_output / f"{reaction_name}_opt{index}.traj"
                endpoint_opt = BFGS(endpoint, trajectory=str(traj_path))
                endpoint_opt.run(fmax=0.01, steps=steps)

                optimized = TrajectoryReader(str(traj_path))[-1]
                set_model_metadata(optimized, charge, spin)
                optimized.calc = calculator
                endpoint_atoms[index - 1] = optimized
                endpoint_energies.append(float(optimized.get_potential_energy()))
                write(reaction_output / f"{reaction_name}_endpoint{index}.xyz", optimized)

            e1, e2 = endpoint_energies
            irc_energies = [float(image.get_potential_energy()) for image in irc_all]
            peak_energy = max(irc_energies)

            # Preserve the barrier definitions used in the original notebook.
            Ef = peak_energy - max(e1, e2)
            Er = peak_energy - min(e1, e2)

            # Preserve the original energy-based R/P convention while ensuring
            # both branches write structures.
            if e1 > e2:
                reactant, product = endpoint_atoms[0], endpoint_atoms[1]
            else:
                reactant, product = endpoint_atoms[1], endpoint_atoms[0]
            write(reaction_output / f"{reaction_name}_r.xyz", reactant)
            write(reaction_output / f"{reaction_name}_p.xyz", product)

            # Step 6: concise logs.
            with (reaction_output / "run.log").open("w", encoding="utf-8") as handle:
                handle.write(f"ref_time: {ref_time}\n")
                handle.write(f"refine_steps: {refine_steps}\n")
                handle.write(f"irc_time: {irc_time}\n")
                handle.write(f"irc_steps: {irc_steps}\n")
                handle.write(f"Ef: {Ef:.6f} eV\n")
                handle.write(f"Er: {Er:.6f} eV\n")
                handle.write(f"irc_split_flag: {split}\n")
                handle.write(f"imaginary_modes: {imaginary_count}\n")

            with all_log.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"{reaction_name}\t{ref_time}\t{refine_steps}\t{irc_time}\t"
                    f"{irc_steps}\t{Ef:.6f}\t{Er:.6f}\t{split}\n"
                )

            logger.info("%s successfully finished.", reaction_name)
            print(f"[done] {reaction_name}")
            return True

        except Exception as exc:
            logger.error(
                "Exception during attempt %d/%d for %s: %s",
                attempt,
                retry,
                reaction_name,
                exc,
            )
            traceback.print_exc()
            if attempt < retry:
                logger.warning("Retrying after 2 seconds.")
                time.sleep(2)
            else:
                logger.error("%s failed after %d attempts.", reaction_name, retry)
                return False

    return False


def main():
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    model_path = Path(args.model).resolve()

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")
    if not model_path.is_file():
        raise SystemExit(
            f"Model file not found: {model_path}\n"
            "Place MACEpre-DeePEST-OS.model under models/ or pass --model."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    input_files = natsorted(
        [path for path in input_dir.iterdir() if path.suffix.lower() == ".xyz"],
        alg=ns.PATH,
    )
    print(f"Number of jobs: {len(input_files)}")
    print(f"MACE model: {model_path}")
    print(f"Device: {args.device}")

    # Pure MACE calculator: no xTB and no SumCalculator.
    calculator = MACECalculator(model_paths=str(model_path), device=args.device)

    failed = []
    for input_xyz in input_files:
        reaction_output = output_dir / input_xyz.stem
        if reaction_output.exists() and not args.overwrite:
            print(f"[skip] {input_xyz.stem}: output directory already exists")
            continue
        reaction_output.mkdir(parents=True, exist_ok=True)

        ok = ts_irc_pipeline(
            input_xyz=input_xyz,
            output_root=output_dir,
            reaction_output=reaction_output,
            calculator=calculator,
            charge=args.charge,
            spin=args.spin,
            ts_fmax=args.ts_fmax,
            irc_fmax=args.irc_fmax,
            steps=args.steps,
            retry=max(1, args.retry),
            max_imaginary_modes=args.max_imaginary_modes,
        )
        if not ok:
            failed.append(input_xyz.name)

    if failed:
        print("Failed reactions:")
        for name in failed:
            print(f"  {name}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
