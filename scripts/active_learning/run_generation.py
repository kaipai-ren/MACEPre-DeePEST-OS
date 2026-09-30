#!/usr/bin/env python3
"""Run one active-learning generation up to the external QC-labeling checkpoint."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import infer_next_generation, load_config, section


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/active_learning.yaml")
    p.add_argument("--generation-dir", required=True)
    p.add_argument(
        "--skip-training",
        action="store_true",
        help="Use existing committee models.",
    )
    p.add_argument(
        "--skip-scoring",
        action="store_true",
        help="Use existing QBC score caches.",
    )
    p.add_argument("--selection-random-seed", type=int, default=None)
    return p.parse_args()


def run(cmd):
    print("\n$ " + " ".join(str(x) for x in cmd))
    subprocess.run([str(x) for x in cmd], check=True)


def main():
    args = parse_args()
    config_path = Path(args.config).resolve()
    cfg = load_config(config_path)
    run_cfg = section(cfg, "run")

    generation_dir = Path(args.generation_dir).resolve()
    generation = generation_dir.name
    next_generation = infer_next_generation(generation)
    next_dir = generation_dir.parent / next_generation

    script_dir = Path(__file__).resolve().parent

    if not args.skip_training:
        run(
            [
                sys.executable,
                script_dir / "train_committee.py",
                "--config",
                config_path,
                "--generation-dir",
                generation_dir,
            ]
        )

    if not args.skip_scoring:
        run(
            [
                sys.executable,
                script_dir / "score_candidates.py",
                "--config",
                config_path,
                "--generation-dir",
                generation_dir,
            ]
        )

    select_cmd = [
        sys.executable,
        script_dir / "select_candidates.py",
        "--config",
        config_path,
        "--generation-dir",
        generation_dir,
        "--next-generation-dir",
        next_dir,
    ]
    if args.selection_random_seed is not None:
        select_cmd.extend(["--random-seed", str(args.selection_random_seed)])
    run(select_cmd)

    root = generation_dir.parent
    run(
        [
            sys.executable,
            script_dir / "check_convergence.py",
            "--config",
            config_path,
            "--root",
            root,
        ]
    )

    candidate_dir = next_dir / "candidate_xyzdata"
    print("\n" + "=" * 72)
    print(f"Active-learning generation {generation} completed.")
    print()
    print("The automated workflow stops here at the quantum-chemistry labeling checkpoint.")
    print(f"Selected structures for the next round: {candidate_dir}")
    print()
    print("If convergence has NOT been reached:")
    print("  1. Perform the high-level DFT energy/force calculations for these structures.")
    print("  2. Add the newly labeled structures to the cumulative training set.")
    print(f"  3. Save that cumulative labeled extxyz as: {next_dir / (next_generation + '.xyz')}")
    print(f"  4. Run this workflow again with --generation-dir {next_dir}")
    print()
    print("QC labeling is intentionally not automated because the quantum-chemistry")
    print("submission/parsing workflow is external to these active-learning scripts.")
    print("=" * 72)


if __name__ == "__main__":
    main()
