# VM.AI Parser - Google Colab (uv)

## Quick Start

1. **Open Colab**: Upload `VM_AI_Colab_Training.ipynb` to Google Colab
2. **Enable GPU**: Runtime → Change runtime type → GPU (T4)
3. **Run cells** in order

**Uses uv** for fast package installation (~10x faster than pip).

---

## Files

| File | Purpose |
|------|---------|
| `VM_AI_Colab_Training.ipynb` | Main notebook |
| `pyproject.toml` | uv dependencies |
| `upload_to_hf.py` | Upload to Hugging Face |
| `data/` | Training data (YAML) |
| `*.py` | Training scripts |

---

## Training Commands

```python
# Full training (recommended)
!python train.py --mode both

# Fine-tune modify
!python train.py --mode modify_only

# Real data only
!python train.py --mode real
```

---

## Upload to Hugging Face

```python
!python upload_to_hf.py
```

Model URL: **https://huggingface.co/VMAI/vmai-parser**

---

## Download at School/Home

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="VMAI/vmai-parser",
    local_dir="models/finetuned_parser"
)
```

---

## Sync Workflow

```
HOME:
1. Train: !python train.py --mode both
2. Upload: !python upload_to_hf.py
3. Push to GitHub

SCHOOL:
1. Download from HF
2. Continue training: --mode modify_only
3. Upload back to HF

HOME:
1. Pull from HF
2. Test & deploy
```
