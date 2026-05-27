"""
VM.AI — 5-fold stratified cross-validation for EfficientNet-B4.

Runs 5 folds on the full dataset (train+val+test combined), reports mean ± std accuracy.
Generates per-fold charts and aggregate comparison plots.

Usage:
  uv run python src/image_to_prompt/training/cross_validation.py
  uv run python src/image_to_prompt/training/cross_validation.py --fold 1
"""

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from torch.cuda.amp import GradScaler
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).parent.parent / "evaluation"))
sys.path.insert(0, str(Path(__file__).parent))
from evaluate_classifier import (
    compute_topk_accuracy,
    get_all_predictions,
    plot_confusion_matrix,
    plot_per_class_metrics,
    setup_style,
)
from train_classifier import (
    DATA_ROOT,
    IMAGENET_MEAN,
    IMAGENET_STD,
    ImageDataset,
    build_model,
    train_epoch,
    val_epoch,
)

CV_CONFIG = {
    "n_splits": 5,
    "seed": 42,
    "num_classes": 14,
    "batch_size": 32,
    "epochs_frozen": 5,
    "epochs_unfrozen": 25,
    "lr_head": 1e-3,
    "lr_backbone": 1e-5,
    "weight_decay": 1e-4,
    "label_smoothing": 0.1,
    "early_stopping_patience": 7,
    "early_stopping_min_delta": 0.001,
}

CV_MODEL_DIR = Path("models/cross_validation")
CV_ASSETS_DIR = Path("assets/image_classifier/cross_validation")

train_transforms = transforms.Compose([
    transforms.Resize((420, 420)),
    transforms.RandomCrop((380, 380)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

val_transforms = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def load_full_dataset():
    dfs = []
    for split in ["train", "val", "test"]:
        df = pd.read_csv(DATA_ROOT / f"{split}.csv", quoting=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


class FullImageDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.classes = sorted(df["label"].unique())
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
        self.labels = [self.class_to_idx[l] for l in df["label"]]

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(DATA_ROOT / row["path"]).convert("RGB")
        label = self.class_to_idx[row["label"]]
        if self.transform:
            img = self.transform(img)
        return img, label


class EarlyStopping:
    def __init__(self, patience: int = 7, min_delta: float = 0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_acc = 0.0
        self.should_stop = False

    def step(self, val_acc: float) -> bool:
        if val_acc > self.best_acc + self.min_delta:
            self.best_acc = val_acc
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        return self.should_stop


def compute_class_weights(dataset: FullImageDataset, device: torch.device):
    counts = np.bincount(dataset.labels, minlength=CV_CONFIG["num_classes"])
    total = counts.sum()
    weights = total / (CV_CONFIG["num_classes"] * counts.astype(float))
    return torch.tensor(weights, dtype=torch.float).to(device)


def train_fold(fold: int, train_idx: list, val_idx: list, dataset: FullImageDataset, device: torch.device) -> dict:
    print(f"\n{'=' * 60}")
    print(f"Fold {fold}/{CV_CONFIG['n_splits']}")
    print(f"  Train: {len(train_idx)} | Val: {len(val_idx)}")
    print(f"{'=' * 60}\n")

    fold_dir = CV_MODEL_DIR / f"fold_{fold}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = str(fold_dir / "checkpoint.pth")

    train_dataset = FullImageDataset(dataset.df.iloc[train_idx], transform=train_transforms)
    val_dataset = FullImageDataset(dataset.df.iloc[val_idx], transform=val_transforms)

    train_loader = DataLoader(
        train_dataset, batch_size=CV_CONFIG["batch_size"],
        shuffle=True, num_workers=2, pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=CV_CONFIG["batch_size"],
        shuffle=False, num_workers=2, pin_memory=True,
    )

    class_weights = compute_class_weights(train_dataset, device)
    criterion = nn.CrossEntropyLoss(
        weight=class_weights,
        label_smoothing=CV_CONFIG["label_smoothing"],
    )

    model = build_model(CV_CONFIG["num_classes"]).to(device)
    scaler = GradScaler()
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_val_acc = 0.0
    early_stopping = EarlyStopping(
        patience=CV_CONFIG["early_stopping_patience"],
        min_delta=CV_CONFIG["early_stopping_min_delta"],
    )

    # ── Phase A: Frozen backbone ──
    print("Phase A: Frozen backbone")
    for param in model.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True

    optimizer_A = torch.optim.AdamW(
        model.classifier.parameters(),
        lr=CV_CONFIG["lr_head"],
        weight_decay=CV_CONFIG["weight_decay"],
    )

    for epoch in range(CV_CONFIG["epochs_frozen"]):
        t0 = time.time()
        tl, ta = train_epoch(model, train_loader, optimizer_A, criterion, device, scaler)
        vl, va = val_epoch(model, val_loader, criterion, device)
        elapsed = time.time() - t0
        history["train_loss"].append(tl)
        history["val_loss"].append(vl)
        history["train_acc"].append(ta)
        history["val_acc"].append(va)
        print(f"  [A {epoch+1}/{CV_CONFIG['epochs_frozen']}] "
              f"train_acc={ta:.3f} val_acc={va:.3f} ({elapsed:.0f}s)")
        if va > best_val_acc:
            best_val_acc = va
            torch.save({
                "model_state_dict": model.state_dict(),
                "best_val_acc": best_val_acc,
                "history": history,
            }, checkpoint_path)

    # ── Phase B: Partial unfreeze ──
    print("Phase B: Partial unfreeze")
    for param in model.blocks[-2:].parameters():
        param.requires_grad = True

    optimizer_B = torch.optim.AdamW([
        {"params": model.classifier.parameters(), "lr": CV_CONFIG["lr_head"] / 10},
        {"params": model.blocks[-2:].parameters(), "lr": CV_CONFIG["lr_backbone"]},
    ], weight_decay=CV_CONFIG["weight_decay"])

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer_B, T_max=CV_CONFIG["epochs_unfrozen"], eta_min=1e-6,
    )

    stopped_epoch = CV_CONFIG["epochs_unfrozen"]
    for i in range(CV_CONFIG["epochs_unfrozen"]):
        t0 = time.time()
        tl, ta = train_epoch(model, train_loader, optimizer_B, criterion, device, scaler)
        vl, va = val_epoch(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0
        history["train_loss"].append(tl)
        history["val_loss"].append(vl)
        history["train_acc"].append(ta)
        history["val_acc"].append(va)
        epoch_num = CV_CONFIG["epochs_frozen"] + i + 1
        total = CV_CONFIG["epochs_frozen"] + CV_CONFIG["epochs_unfrozen"]
        print(f"  [B {epoch_num}/{total}] "
              f"train_acc={ta:.3f} val_acc={va:.3f} ({elapsed:.0f}s)")
        if va > best_val_acc:
            best_val_acc = va
            torch.save({
                "model_state_dict": model.state_dict(),
                "best_val_acc": best_val_acc,
                "history": history,
            }, checkpoint_path)
            print(f"  * Best saved (val_acc={va:.3f})")
        if early_stopping.step(va):
            print(f"  Early stopping at epoch {epoch_num}")
            stopped_epoch = epoch_num
            break

    history["stopped_epoch"] = stopped_epoch
    with open(fold_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)

    return {
        "fold": fold,
        "best_val_acc": best_val_acc,
        "stopped_epoch": stopped_epoch,
        "history": history,
        "checkpoint_path": checkpoint_path,
        "val_loader": val_loader,
        "model": model,
        "device": device,
    }


def evaluate_fold(result: dict, class_names: list):
    fold = result["fold"]
    assets_dir = CV_ASSETS_DIR / f"fold_{fold}"
    assets_dir.mkdir(parents=True, exist_ok=True)

    model = result["model"]
    device = result["device"]

    ckpt = torch.load(result["checkpoint_path"], map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])

    y_true, y_pred, y_scores = get_all_predictions(model, result["val_loader"], device, len(class_names))

    cm = confusion_matrix(y_true, y_pred)
    plot_confusion_matrix(cm, class_names, assets_dir / "confusion_matrix.png")

    report = classification_report(y_true, y_pred, target_names=class_names, output_dict=True, zero_division=0)
    per_class = {
        c: {
            "precision": report[c]["precision"],
            "recall": report[c]["recall"],
            "f1": report[c]["f1-score"],
        }
        for c in class_names
    }
    plot_per_class_metrics(per_class, class_names, assets_dir / "per_class_metrics.png")

    top1 = compute_topk_accuracy(y_scores, y_true, max_k=1)[0]
    return top1, per_class


def plot_cv_boxplot(fold_accs: list, save_path: Path):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot(fold_accs, patch_artist=True, boxprops=dict(facecolor="steelblue", alpha=0.7))
    for i, acc in enumerate(fold_accs):
        ax.scatter(1, acc, color="white", zorder=5)
        ax.annotate(f"Fold {i+1}: {acc:.3f}", xy=(1, acc), xytext=(1.15, acc), fontsize=9, color="#c9d1d9")
    mean_acc = np.mean(fold_accs)
    std_acc = np.std(fold_accs)
    ax.axhline(mean_acc, color="orange", linestyle="--", label=f"Mean: {mean_acc:.3f} ± {std_acc:.3f}")
    ax.set_ylabel("Accuracy")
    ax.set_title("Cross-Validation Accuracy Distribution")
    ax.set_xticks([])
    ax.set_ylim(min(fold_accs) - 0.02, 1.02)
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_cv_per_class_f1(all_per_class: list, class_names: list, save_path: Path):
    mean_f1 = []
    std_f1 = []
    for c in class_names:
        f1s = [fold[c]["f1"] for fold in all_per_class]
        mean_f1.append(np.mean(f1s))
        std_f1.append(np.std(f1s))

    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(class_names))
    ax.bar(x, mean_f1, yerr=std_f1, capsize=5, color="steelblue", alpha=0.85, error_kw={"color": "white"})
    ax.set_xticks(x)
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_ylabel("F1 Score")
    ax.set_title("Mean Per-Class F1 ± Std (5-Fold CV)")
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_cv_results(fold_results: list, fold_accs: list, all_per_class: list, class_names: list):
    mean_acc = float(np.mean(fold_accs))
    std_acc = float(np.std(fold_accs))

    summary = {
        "n_splits": CV_CONFIG["n_splits"],
        "mean_accuracy": round(mean_acc, 4),
        "std_accuracy": round(std_acc, 4),
        "per_fold": [
            {
                "fold": r["fold"],
                "val_acc": round(r["best_val_acc"], 4),
                "stopped_epoch": r["stopped_epoch"],
            }
            for r in fold_results
        ],
        "per_class_mean_f1": {
            c: round(float(np.mean([f[c]["f1"] for f in all_per_class])), 4)
            for c in class_names
        },
    }

    path = CV_MODEL_DIR / "cv_results.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 50)
    print("CROSS-VALIDATION RESULTS")
    print("=" * 50)
    for r in fold_results:
        print(f"  Fold {r['fold']}: val_acc={r['best_val_acc']:.4f} (stopped epoch {r['stopped_epoch']})")
    print("-" * 50)
    print(f"  Mean: {mean_acc:.4f} ± {std_acc:.4f}")
    print("=" * 50)
    print(f"\nResults saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="5-fold cross-validation")
    parser.add_argument("--fold", type=int, default=None, help="Run specific fold only (1-5). Default: run all.")
    args = parser.parse_args()

    setup_style()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    CV_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    CV_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    full_df = load_full_dataset()
    dataset = FullImageDataset(full_df, transform=None)
    class_names = dataset.classes
    labels = np.array(dataset.labels)

    print(f"Full dataset: {len(dataset)} images, {len(class_names)} classes")

    skf = StratifiedKFold(n_splits=CV_CONFIG["n_splits"], shuffle=True, random_state=CV_CONFIG["seed"])
    folds = list(skf.split(np.zeros(len(labels)), labels))

    if args.fold:
        folds_to_run = [(args.fold - 1, folds[args.fold - 1])]
    else:
        folds_to_run = list(enumerate(folds))

    fold_results = []
    fold_accs = []
    all_per_class = []

    for fold_idx, (train_idx, val_idx) in folds_to_run:
        fold_num = fold_idx + 1
        result = train_fold(fold_num, train_idx.tolist(), val_idx.tolist(), dataset, device)
        top1, per_class = evaluate_fold(result, class_names)
        fold_accs.append(top1)
        all_per_class.append(per_class)
        fold_results.append(result)
        print(f"  Fold {fold_num} complete — val_acc={top1:.4f}")

    if len(fold_results) == CV_CONFIG["n_splits"]:
        print("\nGenerating CV charts...")
        plot_cv_boxplot(fold_accs, CV_ASSETS_DIR / "cv_accuracy_boxplot.png")
        plot_cv_per_class_f1(all_per_class, class_names, CV_ASSETS_DIR / "cv_per_class_f1_mean.png")

    save_cv_results(fold_results, fold_accs, all_per_class, class_names)
    print("\nCross-validation complete.")


if __name__ == "__main__":
    main()
