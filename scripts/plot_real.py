"""
    VM.AI - Difficulty vs Importance Scatter Plot for Real Dataset
    Run: python scripts/plot_real.py
"""

import sys
import os
import yaml

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
    # Only add examples (have name + difficulty + importance)
    adds = [
        ex for ex in examples
        if "name" in ex.get("output", {}) and ex["output"].get("difficulty") is not None
    ]

    diffs = [float(ex["output"]["difficulty"]) for ex in adds]
    imps = [float(ex["output"]["importance"]) for ex in adds]
    cats = [str(ex["output"].get("category", "unknown")).lower() for ex in adds]

    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
        "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
        "text.color": "#c9d1d9", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    })

    fig, ax = plt.subplots(figsize=(10, 7))
    unique_cats = sorted(set(cats))
    for cat in unique_cats:
        mask = [c == cat for c in cats]
        ax.scatter(
            [d for d, m in zip(diffs, mask) if m],
            [i for i, m in zip(imps, mask) if m],
            label=cat, s=60, alpha=0.7, edgecolors="#30363d",
        )

    ax.set_title("Difficulty vs Importance (Real Data)", color="#f0f6fc", fontweight="bold")
    ax.set_xlabel("Difficulty", color="#8b949e")
    ax.set_ylabel("Importance", color="#8b949e")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9, framealpha=0.3)
    ax.grid(True, alpha=0.2)

    out = os.path.join(ROOT, "scripts", "output", "real_scatter.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
