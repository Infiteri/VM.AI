"""
    VM-AI - Training Loss Plot from HuggingFace trainer logs
    Run after training: python scripts/plot_training.py

    Written by: Vanea
"""

import sys
import os
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models", "finetuned_parser")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install matplotlib")
    sys.exit(1)

plt.style.use("dark_background")
plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
})

losses, eval_losses, steps = [], [], []

log_file = os.path.join(MODEL_DIR, "trainer_log.jsonl")
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                step = entry.get("step", 0)
                if "loss" in entry:
                    losses.append((step, entry["loss"]))
                if "eval_loss" in entry:
                    eval_losses.append((step, entry["eval_loss"]))
                    steps.append(step)
            except: pass

if not losses:
    print("No training logs found. Run training first.")
    sys.exit(0)

fig, ax = plt.subplots(figsize=(14, 7))

if losses:
    x, y = zip(*losses)
    ax.plot(x, y, color="#58a6ff", alpha=0.4, label="Train Loss", linewidth=1)

if eval_losses:
    x, y = zip(*eval_losses)
    ax.plot(x, y, color="#3fb950", alpha=0.9, label="Eval Loss", linewidth=2, marker="o", markersize=4)

ax.set_title("Training Loss Over Time", color="#f0f6fc", fontsize=14, fontweight="bold")
ax.set_xlabel("Step", color="#8b949e", fontsize=12)
ax.set_ylabel("Loss", color="#8b949e", fontsize=12)
ax.legend(fontsize=10, framealpha=0.3)
ax.grid(True, alpha=0.15)

out = os.path.join(ROOT, "scripts", "output", "training_loss.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.tight_layout()
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
print(f"Train steps: {len(losses)}, Eval points: {len(eval_losses)}")
