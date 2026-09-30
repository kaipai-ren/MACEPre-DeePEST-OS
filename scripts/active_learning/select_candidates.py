#!/usr/bin/env python3
"""Select active-learning candidates from cached QBC scores.

Selection rule used in the manuscript:
  1. P75 <= force_score <= P99: select the 50,000 largest scores.
  2. force_score > P99: randomly sample 500 structures.

The two quotas are independent, so a generation can contain up to 50,500
selected structures. No lower-score fallback is used to fill a shortfall.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
from ase.io import iread, write

from common import infer_next_generation, load_config, section


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/active_learning.yaml")
    p.add_argument("--generation-dir", required=True)
    p.add_argument("--next-generation-dir", default=None)
    p.add_argument("--random-seed", type=int, default=None)
    p.add_argument("--resume-from-cache", action="store_true")
    return p.parse_args()


def score_files(generation_dir, qbc_cfg):
    cache_dir = generation_dir / qbc_cfg.get("prediction_subdir", "qbc_eval_scores")
    prefix = qbc_cfg.get("prediction_file_prefix", "full")
    files = sorted(cache_dir.glob(f"{prefix}_shard*.npz"))
    if not files:
        raise FileNotFoundError(f"No QBC score caches found under {cache_dir}")
    return files


def iter_records(files):
    for path in files:
        data = np.load(path, allow_pickle=True)
        labels = data["labels"]
        source_paths = data["source_paths"]
        shard_paths = data["shard_paths"]
        frame_indices = data["frame_indices"]
        scores = data["force_scores"]
        rms = data["force_rms"]
        p95 = data["force_p95"]
        for i in range(len(labels)):
            score = float(scores[i])
            if math.isnan(score):
                continue
            yield {
                "label": str(labels[i]),
                "source_path": str(source_paths[i]),
                "shard_path": str(shard_paths[i]),
                "frame_index": int(frame_indices[i]),
                "force_score": score,
                "force_rms": float(rms[i]),
                "force_p95": float(p95[i]),
            }


def record_key(record):
    if record["source_path"]:
        return record["source_path"]
    return f"{record['shard_path']}:{record['frame_index']}:{record['label']}"


def history_path(generation_dir):
    return generation_dir.parent / "qbc_selected_history.tsv"


def load_history(path):
    if not path.exists():
        return set()
    seen = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            key = row.get("key", "")
            if key:
                seen.add(key)
    return seen


def append_history(path, records, current_gen, next_gen):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        fields = ["key", "current_gen", "next_gen", "label", "force_score"]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        if write_header:
            w.writeheader()
        for record in records:
            w.writerow(
                {
                    "key": record_key(record),
                    "current_gen": current_gen,
                    "next_gen": next_gen,
                    "label": record["label"],
                    "force_score": f"{record['force_score']:.8f}",
                }
            )


def write_tsv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "rank", "selection_source", "label", "force_score", "force_rms",
            "force_p95", "shard_path", "frame_index", "source_path",
        ]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for rank, record in enumerate(records, 1):
            out = dict(record)
            out["rank"] = rank
            out["force_score"] = f"{record['force_score']:.8f}"
            out["force_rms"] = f"{record['force_rms']:.8f}"
            out["force_p95"] = f"{record['force_p95']:.8f}"
            w.writerow({key: out.get(key, "") for key in fields})


def safe_percentile(records, p):
    if not records:
        return math.nan
    return float(np.percentile([r["force_score"] for r in records], p))


def destination(output_dir, label, used):
    name = Path(label).name
    if not name.endswith(".xyz"):
        name += ".xyz"
    candidate = name
    stem = Path(name).stem
    suffix = Path(name).suffix
    index = 1
    while candidate in used or (output_dir / candidate).exists():
        candidate = f"{stem}_{index}{suffix}"
        index += 1
    used.add(candidate)
    return output_dir / candidate


def write_selected_frames(records, output_dir, copy_original=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    used = set()
    by_shard = defaultdict(dict)
    written = 0
    for record in records:
        source = Path(record["source_path"]) if record["source_path"] else None
        if copy_original and source and source.is_file():
            shutil.copy2(source, destination(output_dir, record["label"], used))
            written += 1
        else:
            by_shard[record["shard_path"]][record["frame_index"]] = record

    for shard_path, targets in by_shard.items():
        remaining = set(targets)
        for frame_index, atoms in enumerate(iread(shard_path, index=":")):
            if frame_index not in remaining:
                continue
            record = targets[frame_index]
            write(destination(output_dir, record["label"], used), atoms, format="extxyz")
            written += 1
            remaining.remove(frame_index)
            if not remaining:
                break
        if remaining:
            raise RuntimeError(
                f"Could not recover {len(remaining)} selected frame(s) from {shard_path}"
            )
    return written


def main():
    args = parse_args()
    cfg = load_config(args.config)
    qbc_cfg = section(cfg, "qbc")
    selection_cfg = section(cfg, "selection")

    generation_dir = Path(args.generation_dir).resolve()
    current_gen = generation_dir.name
    next_gen = infer_next_generation(current_gen)
    next_dir = (
        Path(args.next_generation_dir).resolve()
        if args.next_generation_dir
        else generation_dir.parent / next_gen
    )

    files = score_files(generation_dir, qbc_cfg)
    records = list(iter_records(files))
    if not records:
        raise SystemExit("No valid QBC scores found.")

    all_scores = np.asarray([r["force_score"] for r in records], dtype=np.float64)
    low_pct = float(selection_cfg.get("low_percentile", 75.0))
    high_pct = float(selection_cfg.get("high_percentile", 99.0))
    p_low = float(np.percentile(all_scores, low_pct))
    p_high = float(np.percentile(all_scores, high_pct))

    if bool(qbc_cfg.get("exclude_selected_history", True)):
        seen = load_history(history_path(generation_dir))
        records = [r for r in records if record_key(r) not in seen]
    else:
        seen = set()

    middle = [r for r in records if p_low <= r["force_score"] <= p_high]
    extreme = [r for r in records if r["force_score"] > p_high]

    middle.sort(key=lambda r: r["force_score"], reverse=True)
    top_count = int(selection_cfg.get("top_count", 50000))
    extreme_count = int(selection_cfg.get("extreme_random_count", 500))

    selected_middle = middle[:top_count]
    configured_seed = args.random_seed
    if configured_seed is None:
        configured_seed = selection_cfg.get("random_seed")
    if configured_seed is None:
        configured_seed = random.SystemRandom().randrange(1, 2**31)
        seed_source = "generated_for_this_selection"
    else:
        configured_seed = int(configured_seed)
        seed_source = "configured"

    rng = random.Random(configured_seed)
    selected_extreme = (
        rng.sample(extreme, min(extreme_count, len(extreme))) if extreme else []
    )
    for record in selected_middle:
        record["selection_source"] = f"top_P{low_pct:g}-P{high_pct:g}"
    for record in selected_extreme:
        record["selection_source"] = f"random_above_P{high_pct:g}"

    selected = selected_middle + selected_extreme
    log_dir = generation_dir / qbc_cfg.get("log_dir", "qbc_eval_log")
    log_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(log_dir / "selected_qbc_candidates.tsv", selected)

    candidate_dir = next_dir / "candidate_xyzdata"
    written = write_selected_frames(
        selected,
        candidate_dir,
        copy_original=bool(qbc_cfg.get("copy_original_if_available", False)),
    )

    if bool(qbc_cfg.get("exclude_selected_history", True)):
        append_history(history_path(generation_dir), selected, current_gen, next_gen)

    summary = {
        "current_gen": current_gen,
        "next_gen": next_gen,
        "valid_scores": len(all_scores),
        "history_excluded": len(seen),
        "selection_window_low_percentile": low_pct,
        "selection_window_high_percentile": high_pct,
        "selection_window_low": f"{p_low:.8f}",
        "selection_window_high": f"{p_high:.8f}",
        "middle_pool_count": len(middle),
        "extreme_pool_count": len(extreme),
        "selected_middle": len(selected_middle),
        "selected_extreme": len(selected_extreme),
        "selected_count": len(selected),
        "selected_written": written,
        "selection_random_seed": configured_seed,
        "selection_random_seed_source": seed_source,
        "selected_force_score_p50": f"{safe_percentile(selected, 50):.8f}",
        "selected_force_score_p75": f"{safe_percentile(selected, 75):.8f}",
        "selected_force_score_p90": f"{safe_percentile(selected, 90):.8f}",
        "selected_force_score_p95": f"{safe_percentile(selected, 95):.8f}",
        "all_force_score_p50": f"{np.percentile(all_scores, 50):.8f}",
        "all_force_score_p75": f"{np.percentile(all_scores, 75):.8f}",
        "all_force_score_p90": f"{np.percentile(all_scores, 90):.8f}",
        "all_force_score_p99": f"{np.percentile(all_scores, 99):.8f}",
    }
    with (log_dir / "selected_qbc_summary.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(summary), delimiter="\t")
        w.writeheader()
        w.writerow(summary)

    print(f"P{low_pct:g} = {p_low:.8f}; P{high_pct:g} = {p_high:.8f}")
    print(
        f"Selected {len(selected_middle)} highest-score structures from P75-P99 "
        f"and {len(selected_extreme)} random structures from >P99."
    )
    print(f"Random-selection seed: {configured_seed} ({seed_source})")
    print(f"Selected structures written to: {candidate_dir}")


if __name__ == "__main__":
    main()
