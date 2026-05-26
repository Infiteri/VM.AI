"""
VM.AI — Push the final/ dataset to Hugging Face Hub.

Reads train/val/test CSVs, loads images, builds a DatasetDict,
and pushes to the configured HF repo.

Environment variables (from src/image_to_prompt/.env):
  HF_TOKEN          — Hugging Face API token
  HF_REPO_ID        — Repository ID (e.g. username/vmai-image-classifier)
  HF_REPO_PRIVATE   — Set to "false" for public repo (default: "true")
"""

import os
from pathlib import Path

from datasets import ClassLabel, Dataset, DatasetDict, Image, Split
from dotenv import load_dotenv
from PIL import Image as PILImage

load_dotenv(Path(__file__).parent.parent.parent / ".env")

HF_TOKEN = os.environ["HF_TOKEN"]
HF_REPO_ID = os.environ["HF_REPO_ID"]
HF_REPO_PRIVATE = os.environ.get("HF_REPO_PRIVATE", "true").lower() == "true"

FINAL = Path("data/image_to_prompt/final")


def _load_split(split_name: str) -> Dataset:
    csv_path = FINAL / f"{split_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}")

    images = []
    labels = []
    with open(csv_path) as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            path_str, label = line.split(",", 1)
            img_path = FINAL / path_str
            if not img_path.exists():
                continue
            pil_img = PILImage.open(img_path).convert("RGB")
            images.append(pil_img)
            labels.append(label.strip())

    class_names = sorted(set(labels))
    label_to_id = {n: i for i, n in enumerate(class_names)}
    label_ids = [label_to_id[l] for l in labels]

    ds = Dataset.from_dict({"image": images, "label": label_ids})
    ds = ds.cast_column("image", Image())
    ds = ds.cast_column("label", ClassLabel(names=class_names))
    return ds


def main():
    print(f"Loading splits from {FINAL} ...")

    train_ds = _load_split("train")
    val_ds = _load_split("val")
    test_ds = _load_split("test")

    dataset = DatasetDict({
        Split.TRAIN: train_ds,
        Split.VALIDATION: val_ds,
        Split.TEST: test_ds,
    })

    print(f"  Train: {len(train_ds)}")
    print(f"  Val:   {len(val_ds)}")
    print(f"  Test:  {len(test_ds)}")

    print(f"\nPushing to {HF_REPO_ID} (private={HF_REPO_PRIVATE}) ...")
    dataset.push_to_hub(
        HF_REPO_ID,
        token=HF_TOKEN,
        private=HF_REPO_PRIVATE,
    )
    print("Done.")


if __name__ == "__main__":
    main()
