#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
import yaml


def load_config(path):
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise ValueError("Configuration must be a YAML mapping.")
    return cfg


def section(cfg, name):
    value = cfg.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section {name!r} must be a mapping.")
    return value


def infer_next_generation(current_gen):
    m = re.fullmatch(r"gen(\d+)", current_gen)
    if not m:
        return current_gen + "_next"
    width = len(m.group(1))
    return f"gen{int(m.group(1)) + 1:0{width}d}"


def csv_items(text):
    return [x.strip() for x in str(text).split(",") if x.strip()]
