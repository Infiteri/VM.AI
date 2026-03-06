# download_model.py
import os
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

def download_model(model_name="distilbert-base-uncased", save_dir="./models"):
    """
    Pre-downloads a HuggingFace model and tokenizer locally.
    """
    local_model_path = os.path.join(save_dir, model_name)
    os.makedirs(local_model_path, exist_ok=True)
    
    if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
        print(f"Downloading {model_name} to {local_model_path} ...")
        snapshot_download(repo_id=model_name, local_dir=local_model_path)
    else:
        print(f"Model already downloaded at {local_model_path}")

    print("Downloading tokenizer ...")
    tokenizer = AutoTokenizer.from_pretrained(local_model_path)
    tokenizer.save_pretrained(local_model_path)

    print("Download complete!")

if __name__ == "__main__":
    download_model()