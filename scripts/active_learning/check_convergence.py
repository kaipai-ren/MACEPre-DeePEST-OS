#!/usr/bin/env python3
"""Evaluate generation-to-generation QBC convergence.

Convergence is recommended when the absolute relative changes of both P50 and
P90 are below their configured thresholds for the configured number of
consecutive generations.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

from common import load_config, section


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/active_learning.yaml")
    p.add_argument("--root", default="./active_learning_runs")
    p.add_argument("--output", default="qbc_selected_force_score_trend.tsv")
    return p.parse_args()


def safe_float(value):
    try:
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except Exception:
        return None


def generation_number(name):
    m = re.search(r"gen(\d+)", str(name))
    return int(m.group(1)) if m else 10**12


def read_summaries(root):
    paths = sorted(
        root.glob("gen*/qbc_eval_log/selected_qbc_summary.tsv"),
        key=lambda p: generation_number(p.parent.parent.name),
    )
    rows = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as f:
            data = list(csv.DictReader(f, delimiter="\t"))
        if not data:
            continue
        row = data[0]
        rows.append(
            {
                "generation": row.get("current_gen") or path.parent.parent.name,
                "summary_path": str(path),
                "p50": safe_float(row.get("selected_force_score_p50")),
                "p90": safe_float(row.get("selected_force_score_p90")),
                "selected_count": row.get("selected_count", ""),
            }
        )
    return rows


def relative_change(previous, current):
    if previous is None or current is None or previous == 0:
        return None
    return (previous - current) / previous


def main():
    args = parse_args()
    cfg = load_config(args.config)
    conv = section(cfg, "convergence")
    p50_limit = float(conv.get("p50_plateau_frac", 0.05))
    p90_limit = float(conv.get("p90_plateau_frac", 0.05))
    patience = max(1, int(conv.get("patience", 3)))

    root = Path(args.root).resolve()
    summaries = read_summaries(root)
    if not summaries:
        raise SystemExit(f"No generation summaries found under {root}")

    output_rows = []
    streak = 0
    previous = None
    for row in summaries:
        p50_change = p90_change = None
        p50_stable = p90_stable = False
        if previous is not None:
            p50_change = relative_change(previous["p50"], row["p50"])
            p90_change = relative_change(previous["p90"], row["p90"])
            p50_stable = p50_change is not None and abs(p50_change) < p50_limit
            p90_stable = p90_change is not None and abs(p90_change) < p90_limit
            streak = streak + 1 if (p50_stable and p90_stable) else 0

        output_rows.append(
            {
                "generation": row["generation"],
                "previous_generation": "" if previous is None else previous["generation"],
                "selected_count": row["selected_count"],
                "selected_force_score_p50": "" if row["p50"] is None else f"{row['p50']:.8f}",
                "selected_force_score_p90": "" if row["p90"] is None else f"{row['p90']:.8f}",
                "p50_relative_change": "" if p50_change is None else f"{p50_change:.8f}",
                "p90_relative_change": "" if p90_change is None else f"{p90_change:.8f}",
                "p50_stable": str(p50_stable).lower(),
                "p90_stable": str(p90_stable).lower(),
                "stable_streak": streak,
                "stop_recommended": str(streak >= patience).lower(),
                "summary_path": row["summary_path"],
            }
        )
        previous = row

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path
    with output_path.open("w", encoding="utf-8", newline="") as f:
        fields = list(output_rows[0])
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(output_rows)

    last = output_rows[-1]
    converged = last["stop_recommended"] == "true"
    print(f"Wrote convergence table: {output_path}")
    print(
        f"Latest generation: {last['generation']}; stable streak={last['stable_streak']}/{patience}"
    )
    print("ACTIVE LEARNING STATUS: " + ("CONVERGED" if converged else "CONTINUE"))


if __name__ == "__main__":
    main()
