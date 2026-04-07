"""
    VM.AI — Scatter Plot: Difficulty vs Importance by Category
    Run: python scripts/plot_scatter.py
"""

import sys
import os
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

plt.style.use("dark_background")
plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
})

def load_examples(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("examples", [])

examples = load_examples(os.path.join(DATA, "VMAI_REAL_Data.yaml"))

cats = {}
for ex in examples:
    out = ex.get("output", {})
    try:
        d = float(out.get("difficulty", 0))
        i = float(out.get("importance", 0))
    except: continue
    cat = out.get("category", "unknown").lower()
    cats.setdefault(cat, {"d": [], "i": []})
    cats[cat]["d"].append(d)
    cats[cat]["i"].append(i)

fig, ax = plt.subplots(figsize=(14, 9))
colors = plt.cm.tab10(range(len(cats)))
for idx, (cat, vals) in enumerate(cats.items()):
    ax.scatter(vals["d"], vals["i"], label=cat, color=colors[idx], alpha=0.7, s=60, edgecolors="#30363d")

ax.set_title("Difficulty vs Importance by Category (Real Data)", color="#f0f6fc", fontsize=14, fontweight="bold")
ax.set_xlabel("Difficulty", color="#8b949e", fontsize=12)
ax.set_ylabel("Importance", color="#8b949e", fontsize=12)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.legend(loc="upper right", fontsize=8, framealpha=0.3)
ax.grid(True, alpha=0.15)

out = os.path.join(ROOT, "scripts", "output", "scatter_diff_imp.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.tight_layout()
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
print(f"Categories plotted: {len(cats)}")
for cat, vals in sorted(cats.items()):
    print(f"  {cat:15s}: {len(vals['d'])} points")
