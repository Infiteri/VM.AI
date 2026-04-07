"""
    VM.AI — Data Visualization Scripts (Individual Plots)
    Run: python scripts/plot_categories.py
    Outputs individual images for each metric in scripts/output/
"""

import sys
import os
import yaml
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "scripts", "output")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install matplotlib")
    sys.exit(1)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_examples(path):
    data = load_yaml(path)
    return data.get("examples", [])

def get_synthetic_examples(path):
    sys.path.insert(0, os.path.join(ROOT, "src", "parser"))
    from yaml_parser import VMAI_YamlParser
    from data_generator import DataGenerator
    
    yp = VMAI_YamlParser(path)
    yp.load_yaml()
    training_data = yp.parse()
    
    gen = DataGenerator(training_data)
    examples = []
    for _ in range(200):
        sentence, pm = gen._fill_template()
        schema = gen._build_schema(pm, sentence)
        out = {k: v["value"] for k, v in schema.items() if v["value"] is not None}
        out["category"] = out.get("category", "work")
        out["difficulty"] = out.get("difficulty", 0.5)
        out["importance"] = out.get("importance", 0.5)
        out["duration"] = out.get("duration", 30)
        examples.append({"output": out})
    return examples

def style():
    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": "#0d1117",
        "axes.facecolor": "#0d1117",
        "axes.edgecolor": "#30363d",
        "axes.labelcolor": "#c9d1d9",
        "text.color": "#c9d1d9",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
        "grid.color": "#21262d",
        "font.size": 11,
    })

CATEGORIES = [
    "work", "study", "fitness", "health", "finance", "home",
    "family", "social", "errands", "travel", "creative",
    "learning", "shopping", "admin", "personal"
]

def plot_and_save(data, title, filename, plot_func):
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_func(ax, data, title)
    plt.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")

def plot_categories(ax, data, title):
    cats = [ex.get("output", {}).get("category", "unknown").lower() for ex in data]
    counts = Counter(cats)
    labels, values = [], []
    for c in CATEGORIES:
        if c in counts:
            labels.append(c)
            values.append(counts[c])
    ax.barh(labels[::-1], values[::-1], color="#58a6ff", edgecolor="#30363d")
    ax.set_title(title, color="#f0f6fc", fontsize=14, fontweight="bold")
    ax.set_xlabel("Count", color="#8b949e")
    for i, v in enumerate(values[::-1]):
        ax.text(v + 0.5, i, str(v), color="#c9d1d9", va="center")
    ax.set_xlim(right=max(max(values) * 1.15, 10))

def plot_histogram(ax, data, key, title, color):
    vals = []
    for ex in data:
        try: vals.append(float(ex.get("output", {}).get(key, 0)))
        except: pass
    if not vals: return
    ax.hist(vals, bins=20, color=color, edgecolor="#30363d", alpha=0.85)
    ax.set_title(title, color="#f0f6fc", fontsize=14, fontweight="bold")
    ax.set_xlabel(key.capitalize(), color="#8b949e")
    ax.set_ylabel("Count", color="#8b949e")
    ax.axvline(x=0.5, color="#f85149", linestyle="--", alpha=0.4, label="0.5")
    ax.legend(fontsize=9)

# ─── Main ────────────────────────────────────────────────────────────────────

style()
os.makedirs(OUT_DIR, exist_ok=True)

synth = get_synthetic_examples(os.path.join(DATA, "VMAI_SYNTHETIC_Data.yaml"))
real = get_examples(os.path.join(DATA, "VMAI_REAL_Data.yaml"))
combined = synth + real

print(f"Synthetic: {len(synth)}, Real: {len(real)}, Combined: {len(combined)}")

# Individual plots
plot_and_save(synth, "Synthetic — Categories", "synth_categories.png", plot_categories)
plot_and_save(real, "Real — Categories", "real_categories.png", plot_categories)
plot_and_save(combined, "Combined — Categories", "combined_categories.png", plot_categories)

plot_and_save(combined, "Combined — Difficulty", "combined_difficulty.png", 
              lambda ax, d, t: plot_histogram(ax, d, "difficulty", t, "#3fb950"))

plot_and_save(combined, "Combined — Importance", "combined_importance.png", 
              lambda ax, d, t: plot_histogram(ax, d, "importance", t, "#d29922"))

plot_and_save(combined, "Combined — Duration", "combined_duration.png", 
              lambda ax, d, t: plot_histogram(ax, d, "duration", t, "#bc8cff"))

print("Done.")
