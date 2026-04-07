"""
    VM-AI - HuggingFace Model Uploader
    Uploads trained model to Hugging Face Hub.
    Usage: python upload_to_hf.py [token]

    Written by: Vanea
"""

import os
import sys
import shutil
from huggingface_hub import HfApi, login

# Configuration
HF_USERNAME = "vaneaa"
REPO_NAME = "vmai-parser"

# Paths
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
    # First, sync data to colab folder
    copy_data_to_colab()
    
    print("=" * 60)
    print("VM.AI Parser - Hugging Face Upload")
    print("=" * 60)
    print()
    
    # Get token from command line or prompt
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        print("Enter your Hugging Face token:")
        print("Get one at: https://huggingface.co/settings/tokens")
        print("(Role must be 'Write')")
        print()
        token = input("Token: ").strip()
    
    if not token:
        print("Error: No token provided")
        print("Usage: python upload_to_hf.py [your_token]")
        return
    
    # Check model exists
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return
    
    files = os.listdir(MODEL_PATH)
    if not files:
        print(f"Error: Model folder is empty")
        return
    
    print()
    print(f"Model: {MODEL_PATH}")
    print(f"Files: {len(files)}")
    print()
    
    # Login
    print("Logging in...")
    try:
        login(token=token)
        print("Login OK")
    except Exception as e:
        print(f"Login failed: {e}")
        print("Check your token at: https://huggingface.co/settings/tokens")
        return
    
    # Create API
    api = HfApi()
    repo_id = f"{HF_USERNAME}/{REPO_NAME}"
    
    print()
    print(f"Repository: https://huggingface.co/{repo_id}")
    print()
    
    # Check/create repo
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
    
    # Upload
    print()
    print("Uploading files...")
    try:
        api.upload_folder(
            folder_path=MODEL_PATH,
            repo_id=repo_id,
            repo_type="model",
            commit_message="Upload VM.AI parser model"
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
