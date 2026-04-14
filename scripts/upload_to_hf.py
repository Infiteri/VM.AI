#!/usr/bin/env python
"""
    VM-AI - Upload finetuned model to HuggingFace Hub.
    Run: python scripts/upload_to_hf.py --repo <repo-id> [--message "commit msg"]

    Example:
        python scripts/upload_to_hf.py --repo myorg/vmai-parser-v1 --message "Phase 2 model with EXP/PRD tags"

    Requires: huggingface_hub package, HF_TOKEN env var or login.
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Upload finetuned T5 parser to HuggingFace Hub")
    parser.add_argument("--repo", required=True, help="HuggingFace repo ID (e.g. myorg/vmai-parser-v1)")
    parser.add_argument("--message", default="Upload finetuned parser model", help="Commit message")
    parser.add_argument("--model", default=None, help="Path to model directory (default: models/finetuned_parser)")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("Install: pip install huggingface_hub")
        sys.exit(1)

    model_dir = args.model or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models", "finetuned_parser",
    )

    if not os.path.exists(os.path.join(model_dir, "config.json")):
        print(f"Error: No model found at {model_dir}")
        sys.exit(1)

    # List files to upload
    files = []
    for root, dirs, filenames in os.walk(model_dir):
        # Skip cache and checkpoint dirs
        dirs[:] = [d for d in dirs if not d.startswith("checkpoint-") and d != ".cache"]
        for f in filenames:
            if not f.startswith(".") or f == ".gitattributes":
                files.append(os.path.join(root, f))

    print(f"Uploading {len(files)} files to {args.repo}")
    print(f"Commit message: {args.message}")
    print(f"Model dir: {model_dir}")

    # Filter out checkpoint dirs for upload
    upload_files = [f for f in files if "checkpoint-" not in f]
    print(f"Files to upload (excluding checkpoints): {len(upload_files)}")

    api = HfApi()
    try:
        api.upload_folder(
            folder_path=model_dir,
            repo_id=args.repo,
            repo_type="model",
            commit_message=args.message,
            ignore_patterns=["checkpoint-*", ".cache/*"],
        )
        print(f"\n✓ Uploaded to https://huggingface.co/{args.repo}")
    except Exception as e:
        print(f"\n✗ Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
