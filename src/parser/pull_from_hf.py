"""
    VM-AI - HuggingFace Model Downloader
    Downloads model from Hugging Face.
    Usage: python pull_from_hf.py [token]
    ALWAYS backs up existing model to finetuned_parser_backup before downloading

    Written by: Vanea
"""

import os
import sys
import shutil
from huggingface_hub import snapshot_download

# Configuration
HF_USERNAME = "vaneaa"
REPO_NAME = "vmai-parser"

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "finetuned_parser")
BACKUP_PATH = os.path.join(PROJECT_ROOT, "models", "finetuned_parser_backup")

def backup_existing_model():
    """Always backup existing model before downloading"""
    print("Backing up existing model...")
    
    if not os.path.exists(MODEL_PATH):
        print("  No existing model to backup")
        print()
        return False
    
    # Remove old backup if exists
    if os.path.exists(BACKUP_PATH):
        print(f"  Removing old backup...")
        shutil.rmtree(BACKUP_PATH)
    
    # Move current model to backup
    shutil.move(MODEL_PATH, BACKUP_PATH)
    print(f"  Backed up to: finetuned_parser_backup")
    print()
    return True

def main():
    print("=" * 60)
    print("VM.AI Parser - Download from Hugging Face")
    print("=" * 60)
    print()
    
    # Get token from command line (optional for public repos)
    token = sys.argv[1].strip() if len(sys.argv) > 1 else None
    
    if token:
        print("Using provided token")
    else:
        print("No token provided - will attempt public repo download")
    print()
    
    # Always backup first
    backup_existing_model()
    
    # Create models directory
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    repo_id = f"{HF_USERNAME}/{REPO_NAME}"
    
    print(f"Repository: https://huggingface.co/{repo_id}")
    print(f"Download to: {MODEL_PATH}")
    print()
    
    # Download
    print("Downloading model...")
    try:
        download_kwargs = {"repo_id": repo_id, "local_dir": MODEL_PATH}
        if token:
            download_kwargs["token"] = token
        
        snapshot_download(**download_kwargs)
        
        # Verify download
        files = os.listdir(MODEL_PATH)
        if not files:
            print()
            print("Error: Download completed but folder is empty")
            print("Restoring backup...")
            if os.path.exists(BACKUP_PATH):
                shutil.move(BACKUP_PATH, MODEL_PATH)
                print("Backup restored")
            return
        
        print()
        print("=" * 60)
        print("SUCCESS")
        print("=" * 60)
        print()
        print(f"Model downloaded to: {MODEL_PATH}")
        print(f"Files: {len(files)}")
        print(f"Backup saved at: {BACKUP_PATH}")
        print()
        print("To restore backup if needed:")
        print(f"  Move {BACKUP_PATH} to {MODEL_PATH}")
        
    except Exception as e:
        print()
        print(f"Download failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check token is valid")
        print("  2. Check repo exists: https://huggingface.co/vaneaa/vmai-parser")
        print("  3. Check internet connection")
        print()
        print("Restoring backup...")
        if os.path.exists(BACKUP_PATH):
            shutil.move(BACKUP_PATH, MODEL_PATH)
            print("Backup restored to finetuned_parser")

if __name__ == "__main__":
    main()
