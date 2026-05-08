"""
    VM-AI - HuggingFace Model Uploader
    Uploads trained model to Hugging Face Hub.
    Usage: python upload_to_hf.py [--message "commit msg"]

    Written by: Vanea
"""

import os
import sys
import shutil
import argparse
from getpass import getpass
from huggingface_hub import HfApi, login

HF_USERNAME = "vaneaa"
REPO_NAME = "vmai-parser"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "finetuned_parser")
DATA_SOURCE = os.path.join(PROJECT_ROOT, "data")
DATA_COLAB = os.path.join(SCRIPT_DIR, "colab", "data")

def copy_data_to_colab():
    """Copy data files from root to colab folder"""
    print("Copying data to colab folder...")

    if not os.path.exists(DATA_SOURCE):
        print(f"  Source not found: {DATA_SOURCE}")
        return

    os.makedirs(DATA_COLAB, exist_ok=True)

    copied = 0
    for filename in os.listdir(DATA_SOURCE):
        if filename.endswith(".yaml"):
            src = os.path.join(DATA_SOURCE, filename)
            dst = os.path.join(DATA_COLAB, filename)
            shutil.copy2(src, dst)
            print(f"  Copied: {filename}")
            copied += 1

    print(f"  Done: {copied} files copied")
    print()

def main():
    argp = argparse.ArgumentParser(description="Upload VM.AI parser to HuggingFace Hub")
    argp.add_argument("--message", default="Upload VM.AI parser model", help="Commit message")
    args = argp.parse_args()

    print("=" * 60)
    print("VM.AI Parser - Hugging Face Upload")
    print("=" * 60)
    print()

    token = getpass("Enter HuggingFace token (hidden): ").strip()
    if not token:
        print("Error: No token provided")
        print("Get one at: https://huggingface.co/settings/tokens")
        return

    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return

    file_count = 0
    for root, dirs, filenames in os.walk(MODEL_PATH):
        dirs[:] = [d for d in dirs if not d.startswith("checkpoint-") and d != ".cache"]
        file_count += len(filenames)

    if file_count == 0:
        print(f"Error: Model folder is empty")
        return

    print()
    print(f"Model: {MODEL_PATH}")
    print(f"Files to upload: {file_count} (excluding checkpoints)")
    print(f"Repo: https://huggingface.co/{HF_USERNAME}/{REPO_NAME}")
    print(f"Commit message: {args.message}")
    print()

    print("Logging in...")
    try:
        login(token=token)
        print("Login OK")
    except Exception as e:
        print(f"Login failed: {e}")
        print("Check your token at: https://huggingface.co/settings/tokens")
        return

    api = HfApi()
    repo_id = f"{HF_USERNAME}/{REPO_NAME}"

    try:
        api.model_info(repo_id=repo_id)
        print("Repository exists")
    except:
        print("Creating repository...")
        try:
            api.create_repo(repo_id=repo_id, repo_type="model", private=False)
            print(f"Created: {repo_id}")
        except Exception as e:
            print(f"Failed to create repo: {e}")
            return

    print()
    print("Uploading files...")
    try:
        api.upload_folder(
            folder_path=MODEL_PATH,
            repo_id=repo_id,
            repo_type="model",
            commit_message=args.message,
            token=token,
            ignore_patterns=["checkpoint-*", ".cache/*"],
        )
        print()
        print("=" * 60)
        print("SUCCESS")
        print("=" * 60)
        print()
        print(f"Model: https://huggingface.co/{repo_id}")
        print()
        print("Download with:")
        print(f"  snapshot_download('{repo_id}', local_dir='models/finetuned_parser')")
    except Exception as e:
        print()
        print(f"Upload failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check token has WRITE permission")
        print("  2. Make sure repo exists on huggingface.co")
        print("  3. Check internet connection")

if __name__ == "__main__":
    main()
