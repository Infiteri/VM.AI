"""
    VM.AI — Plot Specific Fixes
    Visualizes VMAI_SPECIFIC_Data.yaml to prove targeted fixes.
    Run: python scripts/plot_specific.py
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
    path = os.path.join(ROOT, "data", "VMAI_SPECIFIC_Data.yaml")
    if not os.path.exists(path):
        print("VMAI_SPECIFIC_Data.yaml not found. Creating empty.")
        return []
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

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    records = load_data()
    if not records:
        print("No specific examples found.")
        sys.exit(0)
        
    import pandas as pd
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} specific records.")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Scatter: Importance vs Difficulty
    sns.scatterplot(data=df, x="difficulty", y="importance", hue="category", ax=axes[0], palette="Set2", alpha=0.8, edgecolor="#30363d")
    axes[0].set_title("Specific Fixes: Difficulty vs Importance", color="#f0f6fc", fontweight="bold")
    axes[0].axhline(0.5, color="#f85149", linestyle="--", alpha=0.5)
    axes[0].axvline(0.5, color="#f85149", linestyle="--", alpha=0.5)

    # Histogram: Importance Focus (Show the fill of the gap)
    sns.histplot(data=df, x="importance", bins=20, color="#d29922", ax=axes[1])
    axes[1].set_title("Specific Fixes: Importance Distribution", color="#f0f6fc", fontweight="bold")
    axes[1].set_xlabel("Importance", color="#8b949e")
    axes[1].axvline(0.3, color="#3fb950", linestyle="--", alpha=0.5, label="Target 0.3")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "specific_fixes.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved: specific_fixes.png")
