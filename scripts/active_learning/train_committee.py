#!/usr/bin/env python3
"""Train the four MACE committee models for one active-learning generation.

Training settings are read from configs/active_learning.yaml. Historical YAML
files from the original calculations are not read here; only their recorded
random seeds are retained in the public configuration for reproducibility.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from common import csv_items, load_config, section


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/active_learning.yaml")
    p.add_argument("--generation-dir", required=True)
    p.add_argument("--mace-run-train", default=None)
    p.add_argument("--devices", default=None)
    p.add_argument("--seeds", default=None, help="Comma-separated seed override.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite-configs", action="store_true")
    return p.parse_args()


def resolve_mace_run_train(value):
    if value:
        if Path(value).is_file():
            return str(Path(value).resolve())
        found = shutil.which(value)
        if found:
            return found
        raise FileNotFoundError(value)
    found = shutil.which("mace_run_train")
    if not found:
        raise FileNotFoundError(
            "mace_run_train was not found on PATH. Activate the conda environment "
            "from environment.yml or pass --mace-run-train."
        )
    return found


def paper_or_random_seeds(cfg, generation, n, override=None):
    if override:
        seeds = [int(x) for x in csv_items(override)]
        source = "command_line"
    else:
        stored = section(cfg, "reproducibility").get("paper_committee_seeds", {})
        seeds = list(stored.get(generation, []))
        if seeds:
            source = "paper_reproducibility"
        else:
            seeds = random.SystemRandom().sample(range(1, 10000), n)
            source = "random_generated"
    if len(seeds) != n or len(set(seeds)) != n:
        raise ValueError(f"Expected {n} distinct seeds, got {seeds}")
    return seeds, source


def record_seeds(path, generation, seeds, source):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["generation", "committee_member", "seed", "seed_source"])
        for i, seed in enumerate(seeds, 1):
            w.writerow([generation, f"c{i}", seed, source])


def parse_mol_name(comment):
    m = re.search(r'(?:^|\s)mol_name=("[^"]+"|\S+)', comment)
    return m.group(1).strip('"') if m else ""


def clean_extxyz(src, dst, exclude_patterns):
    total = written = excluded = invalid = 0
    with Path(src).open("r", encoding="utf-8", errors="replace") as inp, Path(dst).open(
        "w", encoding="utf-8"
    ) as out:
        while True:
            header = inp.readline()
            if not header:
                break
            if not header.strip():
                continue
            try:
                natoms = int(header.strip())
            except ValueError:
                invalid += 1
                continue
            comment = inp.readline()
            if not comment:
                invalid += 1
                break
            atom_lines = [inp.readline() for _ in range(natoms)]
            total += 1
            if len(atom_lines) != natoms or any(not line for line in atom_lines):
                invalid += 1
                break
            name = parse_mol_name(comment)
            if name and any(re.search(p, name) for p in exclude_patterns):
                excluded += 1
                continue
            out.write(f"{natoms}\n")
            out.write(comment)
            out.writelines(atom_lines)
            written += 1
    return {"total": total, "written": written, "excluded": excluded, "invalid": invalid}


def prepare_training_file(generation_dir, generation, training_cfg):
    src = generation_dir / f"{generation}.xyz"
    if not src.is_file() or src.stat().st_size == 0:
        raise FileNotFoundError(f"Missing labeled training set: {src}")
    if not training_cfg.get("clean_train_xyz", True):
        return src
    suffix = training_cfg.get("clean_suffix", "_clean")
    dst = generation_dir / f"{generation}{suffix}.xyz"
    stats = clean_extxyz(src, dst, training_cfg.get("exclude_mol_name_regexes", [r"_atom\d+$"]))
    print(
        f"Training extxyz: total={stats['total']} written={stats['written']} "
        f"excluded={stats['excluded']} invalid={stats['invalid']}"
    )
    if stats["written"] == 0:
        raise RuntimeError(f"No valid structures written to {dst}")
    return dst


def generate_configs(generation_dir, generation, train_file, seeds, training_cfg, overwrite):
    model_cfg = dict(section(training_cfg, "model"))
    models_dir = generation_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    runtime = {
        "num_workers": int(training_cfg.get("num_workers", 4)),
        "enable_cueq": bool(training_cfg.get("enable_cueq", True)),
        "batch_size": int(training_cfg.get("batch_size", 256)),
        "valid_batch_size": int(training_cfg.get("valid_batch_size", 512)),
        "eval_interval": int(training_cfg.get("eval_interval", 5)),
    }
    prefix = training_cfg.get("train_name_prefix", "DORTS-9k")
    paths = []
    for i, seed in enumerate(seeds, 1):
        path = generation_dir / f"{generation}_c{i}.yaml"
        paths.append(path)
        if path.exists() and not overwrite:
            continue
        cfg = dict(model_cfg)
        cfg.update(runtime)
        cfg.update(
            checkpoints_dir=str(models_dir),
            log_dir=str(models_dir),
            model_dir=str(models_dir),
            results_dir=str(models_dir),
            name=f"{prefix}_{generation}_c{i}",
            train_file=str(train_file),
            seed=int(seed),
        )
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
    return paths


def final_tags(generation_dir, keywords):
    tags = set()
    model_dir = generation_dir / "models"
    if not model_dir.exists():
        return tags
    for path in model_dir.glob("*.model"):
        low = path.name.lower()
        if "compiled" in low or not any(k.lower() in low for k in keywords):
            continue
        m = re.search(r"c(\d+)", path.name)
        if m:
            tags.add(f"c{m.group(1)}")
    return tags


def assign_devices(job_idx, devices, per_model, strict, committee_size):
    if strict and len(devices) < committee_size * per_model:
        raise ValueError("Not enough GPUs for strict one-committee-member-per-device assignment.")
    start = job_idx * per_model
    return [devices[(start + j) % len(devices)] for j in range(per_model)]


def run_training(tag, config_path, visible_devices, executable, log_path):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ",".join(visible_devices)
    cmd = [executable, f"--config={config_path}"]
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command=" + " ".join(cmd) + "\n")
        log.write("CUDA_VISIBLE_DEVICES=" + env["CUDA_VISIBLE_DEVICES"] + "\n\n")
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, env=env)
    return tag, result.returncode, log_path


def main():
    args = parse_args()
    cfg = load_config(args.config)
    committee_cfg = section(cfg, "committee")
    training_cfg = section(cfg, "training")

    generation_dir = Path(args.generation_dir).resolve()
    generation = generation_dir.name
    n = int(committee_cfg.get("size", 4))
    seeds, seed_source = paper_or_random_seeds(cfg, generation, n, args.seeds)
    record_seeds(generation_dir / "committee_seeds.tsv", generation, seeds, seed_source)

    if seed_source == "paper_reproducibility":
        print(
            "Using the original-study committee seeds. These seeds were randomly "
            "generated during the study, were not optimized, and are fixed here only "
            "to facilitate reproduction of the reported runs."
        )

    train_file = prepare_training_file(generation_dir, generation, training_cfg)
    configs = generate_configs(
        generation_dir, generation, train_file, seeds, training_cfg, args.overwrite_configs
    )

    executable = resolve_mace_run_train(args.mace_run_train)
    device_text = args.devices or committee_cfg.get("devices", "0,1,2,3")
    devices = [x.replace("cuda:", "") for x in csv_items(device_text)]
    per_model = int(committee_cfg.get("gpus_per_model", 1))
    strict = bool(committee_cfg.get("strict_device_split", True))
    max_workers = int(committee_cfg.get("max_workers", 4))
    keywords = list(training_cfg.get("final_model_keywords", ["stagetwo", "swa"]))

    existing = final_tags(generation_dir, keywords)
    jobs = []
    for i, config_path in enumerate(configs, 1):
        tag = f"c{i}"
        if tag in existing:
            print(f"[skip] {tag}: final model already present")
            continue
        visible = assign_devices(len(jobs), devices, per_model, strict, n)
        log_path = generation_dir / "models" / f"train_{tag}.log"
        jobs.append((tag, config_path, visible, executable, log_path))
        print(f"[launch] {tag} devices={','.join(visible)} config={config_path.name}")

    if args.dry_run:
        print("Dry run: no training launched.")
        return
    if not jobs:
        print("All committee models already exist.")
        return

    failures = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(run_training, *job) for job in jobs]
        for f in as_completed(futures):
            tag, code, log = f.result()
            print(f"[done] {tag} exit={code} log={log}")
            if code != 0:
                failures.append(tag)
    if failures:
        raise SystemExit("Committee training failed for: " + ", ".join(failures))

    missing = [f"c{i}" for i in range(1, n + 1) if f"c{i}" not in final_tags(generation_dir, keywords)]
    if missing:
        raise SystemExit("Final model files not found for: " + ", ".join(missing))
    print("Committee training finished.")


if __name__ == "__main__":
    main()
