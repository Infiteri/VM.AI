"""
    VM.AI — Plot Real Data
    Visualizes VMAI_REAL_Data.yaml specifically.
    Run: python scripts/plot_real.py
"""
import sys, os, yaml
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "scripts", "output")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="darkgrid")
plt.style.use("dark_background")
plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117"})

def load_data():
    path = os.path.join(ROOT, "data", "VMAI_REAL_Data.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    records = []
    for ex in data.get("examples", []):
        out = ex.get("output", {})
        try:
            records.append({
                "category": out.get("category", "unknown").lower(),
                "difficulty": float(out.get("difficulty", 0)),
                "importance": float(out.get("importance", 0)),
                "duration": float(out.get("duration", 0)),
            })
        except: pass
    return records

def plot_scatter(df, ax):
    sns.scatterplot(data=df, x="difficulty", y="importance", hue="category", ax=ax, palette="Set2", alpha=0.7, edgecolor="#30363d")
    ax.set_title("Difficulty vs Importance (Real Data)", color="#f0f6fc", fontweight="bold")

def plot_box(df, ax):
    sns.boxplot(data=df, x="category", y="duration", ax=ax, palette="Set2", showfliers=False)
    ax.set_title("Duration Distribution by Category (Real Data)", color="#f0f6fc", fontweight="bold")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", color="#8b949e")
    ax.set_ylabel("Duration (minutes)", color="#8b949e")

def plot_pie(df, ax):
    counts = df["category"].value_counts()
    ax.pie(counts, labels=counts.index, autopct="%1.1f%%", textprops={"color": "#c9d1d9"}, startangle=90)
    ax.set_title("Category Distribution (Real Data)", color="#f0f6fc", fontweight="bold")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    records = load_data()
    import pandas as pd
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} records.")

    fig, axes = plt.subplots(1, 3, figsize=(22, 6))
    plot_scatter(df, axes[0])
    plot_box(df, axes[1])
    plot_pie(df, axes[2])
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "real_overview.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved: real_overview.png")
