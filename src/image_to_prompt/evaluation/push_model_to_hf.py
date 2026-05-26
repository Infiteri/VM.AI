"""
VM.AI — Push trained model to Hugging Face Hub.

Uploads the .pth file to the configured model repo.

Environment variables (from src/image_to_prompt/.env):
  HF_TOKEN               — Hugging Face API token
  HF_MODEL_REPO_ID       — Model repository ID
  HF_MODEL_REPO_PRIVATE  — Set to "false" for public repo (default: "true")
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv(Path(__file__).parent.parent / ".env")

HF_TOKEN = os.environ["HF_TOKEN"]
HF_MODEL_REPO_ID = os.environ["HF_MODEL_REPO_ID"]
HF_MODEL_REPO_PRIVATE = os.environ.get("HF_MODEL_REPO_PRIVATE", "true").lower() == "true"

MODEL_PATH = Path("models") / "efficientnet_b4_classifier" / "efficientnet_b4_classifier.pth"


def main():
    if not MODEL_PATH.exists():
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    api = HfApi()
    api.create_repo(
        HF_MODEL_REPO_ID,
        private=HF_MODEL_REPO_PRIVATE,
        repo_type="model",
        exist_ok=True,
    )
    api.upload_file(
        path_or_fileobj=str(MODEL_PATH),
        path_in_repo="efficientnet_b4_classifier.pth",
        repo_id=HF_MODEL_REPO_ID,
        token=HF_TOKEN,
    )
    print(f"Model pushed to {HF_MODEL_REPO_ID}")
    print("Done.")


if __name__ == "__main__":
    main()
