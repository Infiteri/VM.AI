"""
    VM-AI - Data Normalizer
    Normalizes VMAI_REAL_Data.yaml and VMAI_SPECIFIC_Data.yaml to consistent formats.
    Run: python src/parser/normalize_data.py

    Written by: Vanea
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
import re
from data_generator import (
    _normalize_duration_to_minutes,
    _normalize_deadline,
    _normalize_time_standalone,
    DAYS,
)

_VALID_CATEGORIES = {
    "work", "study", "fitness", "health", "personal",
    "finance", "home", "family", "social", "errands",
    "travel", "creative", "learning", "admin", "shopping",
}


def clamp_category(cat):
    if cat is None:
        return None
    cat = str(cat).lower().strip()
    if cat in _VALID_CATEGORIES:
        return cat
    return "personal"


def normalize_example(ex):
    """Normalize a single example's output dict."""
    out = ex.get("output", {})

    # Duration -> integer minutes
    dur = out.get("duration")
    if dur is not None:
        dur = _normalize_duration_to_minutes(dur)
        if dur is not None:
            out["duration"] = int(dur)
        else:
            del out["duration"]

    # Difficulty -> float rounded to 2
    diff = out.get("difficulty")
    if diff is not None:
        try:
            out["difficulty"] = round(float(diff), 2)
        except (ValueError, TypeError):
            del out["difficulty"]

    # Importance -> float rounded to 2
    imp = out.get("importance")
    if imp is not None:
        try:
            out["importance"] = round(float(imp), 2)
        except (ValueError, TypeError):
            del out["importance"]

    # Category -> clamped to enum
    cat = out.get("category")
    if cat is not None:
        out["category"] = clamp_category(cat)

    # Start -> normalized vocab
    start = out.get("start")
    if start is not None:
        start = _normalize_deadline(start)
        out["start"] = start if start else None

    # Deadline -> normalized vocab
    dl = out.get("deadline")
    if dl is not None:
        dl = _normalize_deadline(dl)
        out["deadline"] = dl if dl else None

    # fixed_start -> HH:MM
    fs = out.get("fixed_start")
    if fs is not None:
        fs = _normalize_time_standalone(str(fs))
        out["fixed_start"] = fs if fs else None

    # Booleans
    for key in ("fixed_time", "recurrent"):
        if key in out:
            out[key] = bool(out[key])

    # recurrence_days -> list of valid day names
    rd = out.get("recurrence_days")
    if rd is not None:
        if isinstance(rd, str):
            rd = [d.strip() for d in rd.split(",")]
        rd = [d for d in rd if d in DAYS]
        out["recurrence_days"] = rd if rd else None

    # Remove None values
    ex["output"] = {k: v for k, v in out.items() if v is not None}
    return ex


def normalize_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    examples = data.get("examples", [])
    fixed = 0
    for i, ex in enumerate(examples):
        original = yaml.dump(ex, allow_unicode=True, sort_keys=True)
        examples[i] = normalize_example(ex)
        after = yaml.dump(examples[i], allow_unicode=True, sort_keys=True)
        if original != after:
            fixed += 1

    data["examples"] = examples

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"{path}: {fixed}/{len(examples)} examples normalized")
    return fixed, len(examples)


if __name__ == "__main__":
    files = [
        "D:/Users/user/Desktop/VM.AI/data/VMAI_REAL_Data.yaml",
        "D:/Users/user/Desktop/VM.AI/data/VMAI_SPECIFIC_Data.yaml",
    ]

    total_fixed = 0
    total_examples = 0
    for f in files:
        if os.path.exists(f):
            fixed, count = normalize_file(f)
            total_fixed += fixed
            total_examples += count

    print(f"\nTotal: {total_fixed}/{total_examples} examples normalized")
