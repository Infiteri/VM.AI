"""
    VM.AI - Category Distribution Plot for Real Dataset
    Run: python scripts/plot_categories.py
"""

import sys
import os
import yaml
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install matplotlib")
    sys.exit(1)

def main():
    data_path = os.path.join(ROOT, "data", "VMAI_REAL_Data.yaml")
    with open(data_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    examples = data.get("examples", [])
    categories = [str(ex.get("output", {}).get("category", "unknown")).lower() for ex in examples]
    counts = Counter(categories)

    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
        "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
        "text.color": "#c9d1d9", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    })

    fig, ax = plt.subplots(figsize=(10, 6))
    labels, values = zip(*counts.most_common())
    ax.barh(labels, values, color="#58a6ff", edgecolor="#30363d")
    ax.set_title("Category Distribution (Real Data)", color="#f0f6fc", fontweight="bold")
    ax.set_xlabel("Count", color="#8b949e")
    ax.grid(True, alpha=0.15, axis="x")

    for i, v in enumerate(values):
        ax.text(v + 0.2, i, str(v), color="#c9d1d9", va="center")

    out = os.path.join(ROOT, "scripts", "output", "categories.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
