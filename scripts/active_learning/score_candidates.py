#!/usr/bin/env python3
"""Evaluate candidate shards with a MACE committee and cache QBC force scores."""

from __future__ import annotations

import argparse
import gc
import logging
import os
import re
import sys
from pathlib import Path

from common import csv_items, load_config, section


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/active_learning.yaml")
    p.add_argument("--generation-dir", required=True)
    p.add_argument("--shard-dirs", nargs="+", default=None)
    p.add_argument("--device-ids", default=None)
    p.add_argument("--resume", action="store_true")
    return p.parse_args()


def discover_models(generation_dir, keywords):
    model_dir = generation_dir / "models"
    models = {}
    for path in model_dir.glob("*.model"):
        low = path.name.lower()
        if "compiled" in low:
            continue
        m = re.search(r"c(\d+)", path.name)
        if not m:
            continue
        num = int(m.group(1))
        final = any(k.lower() in low for k in keywords)
        if final or num not in models:
            models[num] = (path, final)
    ordered = [models[k][0] for k in sorted(models)]
    return ordered


def discover_shards(dirs, pattern):
    files = []
    for directory in dirs:
        root = Path(directory)
        if not root.is_dir():
            raise FileNotFoundError(root)
        files.extend(sorted(root.glob(pattern)))
    return [p for p in files if p.is_file()]


def cache_path(cache_dir, prefix, shard_id):
    return cache_dir / f"{prefix}_shard{shard_id:05d}.npz"


def load_models(model_paths, device_id, dtype, enable_cueq, require_cueq):
    os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    import numpy as np
    import torch
    from mace.tools import torch_tools

    torch_tools.set_default_dtype(dtype)
    device = torch_tools.init_device(device_id)
    models = []
    for model_path in model_paths:
        model = torch.load(model_path, map_location=device)
        model = model.float() if dtype == "float32" else model.double()
        if enable_cueq:
            try:
                from mace.cli.convert_e3nn_cueq import run as convert
                model = convert(model, device=device)
            except Exception:
                if require_cueq:
                    raise
                logging.warning("CuEq conversion failed for %s; using standard model.", model_path)
        model = model.to(device)
        model.eval()
        for parameter in model.parameters():
            parameter.requires_grad = False
        models.append(model)

    rmax = np.asarray([float(m.r_max) for m in models])
    if not np.allclose(rmax, rmax[0]):
        raise ValueError("Committee r_max values differ.")
    atomic_numbers = [tuple(int(z) for z in m.atomic_numbers) for m in models]
    if any(x != atomic_numbers[0] for x in atomic_numbers):
        raise ValueError("Committee atomic-number tables differ.")
    return models


def model_head(model):
    heads = list(getattr(model, "heads", ["Default"]))
    if len(heads) == 1:
        return heads[0], heads
    defaults = [h for h in heads if str(h).lower() == "default"]
    if not defaults:
        raise ValueError(f"Multiple model heads and no Default head: {heads}")
    return defaults[0], heads


def make_atomic_data(atoms, mace_data, z_table, cutoff, heads, head):
    try:
        config = mace_data.config_from_atoms(atoms, head_name=head)
    except TypeError:
        atoms.info["head"] = head
        config = mace_data.config_from_atoms(atoms)
    try:
        return mace_data.AtomicData.from_config(config, z_table=z_table, cutoff=cutoff, heads=heads)
    except TypeError:
        return mace_data.AtomicData.from_config(config, z_table=z_table, cutoff=cutoff)


def evaluate_chunk(models, atoms_list, device_id, batch_size, head, heads):
    import numpy as np
    import torch
    from mace import data as mace_data
    from mace.tools import torch_geometric, utils

    first = models[0]
    z_table = utils.AtomicNumberTable([int(z) for z in first.atomic_numbers])
    dataset = [
        make_atomic_data(atoms, mace_data, z_table, float(first.r_max), heads, head)
        for atoms in atoms_list
    ]
    loader = torch_geometric.dataloader.DataLoader(
        dataset=dataset, batch_size=batch_size, shuffle=False, drop_last=False
    )
    scores, rms_values, p95_values = [], [], []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device_id)
            ptr = batch.ptr.detach().cpu().numpy().astype(np.int64)
            force_predictions = []
            for model in models:
                output = model(batch.to_dict(), compute_stress=False)
                force_predictions.append(output["forces"].detach())
            stack = torch.stack(force_predictions, dim=0)
            mean = stack.mean(dim=0)
            delta = stack - mean.unsqueeze(0)
            atom_sigma = torch.sqrt(torch.mean(torch.sum(delta * delta, dim=2), dim=0))
            for i in range(len(ptr) - 1):
                sigma = atom_sigma[int(ptr[i]):int(ptr[i + 1])]
                force_rms = torch.sqrt(torch.mean(sigma * sigma))
                force_p95 = sigma[0] if sigma.numel() == 1 else torch.quantile(sigma, 0.95)
                score = 0.5 * force_rms + 0.5 * force_p95
                scores.append(float(score.cpu()))
                rms_values.append(float(force_rms.cpu()))
                p95_values.append(float(force_p95.cpu()))
    return (
        np.asarray(scores, dtype=np.float32),
        np.asarray(rms_values, dtype=np.float32),
        np.asarray(p95_values, dtype=np.float32),
    )


def label_from_atoms(atoms, shard_path, frame_idx):
    source_file = str(atoms.info.get("source_file") or "")
    mol_name = str(atoms.info.get("mol_name") or "")
    label = source_file or mol_name or f"{Path(shard_path).stem}_frame{frame_idx}.xyz"
    if not label.endswith(".xyz"):
        label += ".xyz"
    return label, str(atoms.info.get("source_path") or "")


def worker(worker_id, device_id, assignments, model_paths, cache_dir, prefix, qbc_cfg):
    import numpy as np
    import torch
    from ase.io import iread

    torch.set_num_threads(1)
    models = load_models(
        model_paths,
        device_id,
        qbc_cfg.get("default_dtype", "float32"),
        bool(qbc_cfg.get("enable_cueq", False)),
        bool(qbc_cfg.get("require_cueq", False)),
    )
    head, heads = model_head(models[0])
    batch_size = int(qbc_cfg.get("batch_size", 128))
    chunk_size = int(qbc_cfg.get("chunk_size", 1024))
    compress = bool(qbc_cfg.get("compress_score_cache", False))
    save_fn = np.savez_compressed if compress else np.savez

    for shard_id, shard_path in assignments:
        out = cache_path(cache_dir, prefix, shard_id)
        if out.exists():
            print(f"[worker {worker_id}] cache exists: {out.name}")
            continue

        labels, source_paths, shard_paths, frame_indices = [], [], [], []
        score_parts, rms_parts, p95_parts = [], [], []
        atoms_chunk, meta_chunk = [], []

        def flush():
            nonlocal atoms_chunk, meta_chunk
            if not atoms_chunk:
                return
            scores, rms, p95 = evaluate_chunk(
                models, atoms_chunk, device_id, batch_size, head, heads
            )
            score_parts.append(scores)
            rms_parts.append(rms)
            p95_parts.append(p95)
            for label, source_path, frame_idx in meta_chunk:
                labels.append(label)
                source_paths.append(source_path)
                shard_paths.append(str(shard_path))
                frame_indices.append(frame_idx)
            atoms_chunk, meta_chunk = [], []

        for frame_idx, atoms in enumerate(iread(str(shard_path), index=":")):
            label, source_path = label_from_atoms(atoms, shard_path, frame_idx)
            atoms_chunk.append(atoms)
            meta_chunk.append((label, source_path, frame_idx))
            if len(atoms_chunk) >= chunk_size:
                flush()
        flush()

        scores = np.concatenate(score_parts) if score_parts else np.array([], dtype=np.float32)
        rms = np.concatenate(rms_parts) if rms_parts else np.array([], dtype=np.float32)
        p95 = np.concatenate(p95_parts) if p95_parts else np.array([], dtype=np.float32)
        save_fn(
            out,
            labels=np.asarray(labels, dtype=object),
            source_paths=np.asarray(source_paths, dtype=object),
            shard_paths=np.asarray(shard_paths, dtype=object),
            frame_indices=np.asarray(frame_indices, dtype=np.int64),
            force_scores=scores,
            force_rms=rms,
            force_p95=p95,
        )
        print(f"[worker {worker_id}] wrote {out.name}: {len(labels)} structures")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    qbc_cfg = section(cfg, "qbc")
    training_cfg = section(cfg, "training")
    generation_dir = Path(args.generation_dir).resolve()
    generation = generation_dir.name

    keywords = training_cfg.get("final_model_keywords", ["stagetwo", "swa"])
    model_paths = discover_models(generation_dir, keywords)
    if len(model_paths) != 4:
        raise SystemExit(f"Expected four committee models, found {len(model_paths)}.")

    shard_dirs = args.shard_dirs or qbc_cfg.get("shard_dirs", ["./xyz_shards"])
    shards = discover_shards(shard_dirs, qbc_cfg.get("shard_pattern", "candidate_*.xyz"))
    if not shards:
        raise SystemExit("No candidate shard files found.")

    device_ids = csv_items(args.device_ids or qbc_cfg.get("device_ids", "cuda:0,cuda:1,cuda:2,cuda:3"))
    cache_dir = generation_dir / qbc_cfg.get("prediction_subdir", "qbc_eval_scores")
    cache_dir.mkdir(parents=True, exist_ok=True)
    prefix = qbc_cfg.get("prediction_file_prefix", "full")

    import torch.multiprocessing as mp
    mp.set_start_method("spawn", force=True)
    assignments = [[] for _ in device_ids]
    for shard_id, shard_path in enumerate(shards):
        assignments[shard_id % len(device_ids)].append((shard_id, shard_path))

    processes = []
    for worker_id, (device_id, assigned) in enumerate(zip(device_ids, assignments)):
        if not assigned:
            continue
        p = mp.Process(
            target=worker,
            args=(worker_id, device_id, assigned, model_paths, cache_dir, prefix, qbc_cfg),
        )
        p.start()
        processes.append(p)

    failures = []
    for p in processes:
        p.join()
        if p.exitcode != 0:
            failures.append(p.exitcode)
    if failures:
        raise SystemExit(f"QBC scoring failed; worker exit codes: {failures}")
    print(f"QBC scoring completed for {generation}. Cache directory: {cache_dir}")


if __name__ == "__main__":
    main()
