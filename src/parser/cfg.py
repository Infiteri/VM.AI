# parser/cfg.py

import os
import torch
import vars

class EnvConfig:

    # Total number of training examples to generate (add + modify combined)
    # Higher = better model, slower generation and training
    max_limit: int

    # How many full passes over the training data
    # More epochs = more learning, but risks overfitting
    num_train_epochs: int

    # How many examples the GPU processes at once during training
    # Lower if you get CUDA out-of-memory errors
    per_device_train_batch_size: int

    # Same as train batch size but during evaluation
    per_device_eval_batch_size: int

    # Simulates a larger batch by accumulating gradients before updating weights
    # Effective batch = per_device_train_batch_size * gradient_accumulation_steps
    # e.g. 8 * 16 = 128 effective batch size
    gradient_accumulation_steps: int

    # Use 16-bit floating point instead of 32-bit
    # Halves VRAM usage and speeds up training on supported GPUs
    # Automatically disabled if no CUDA is available
    fp16: bool

    # How many CPU threads load data in parallel
    # 0 = main thread only, required on CPU-only machines
    # 4 = good for local GPU, 2 = safer for Colab (limited shared CPU)
    dataloader_num_workers: int

    # Pins data in CPU RAM for faster transfer to GPU
    # True locally, False on Colab — shared RAM makes pinning cause OOM crashes
    dataloader_pin_memory: bool

    # Print a training loss update every N steps
    logging_steps: int

    # Learning rate when training from base T5 for the first time
    # 2e-5 is the standard starting point for T5 fine-tuning
    learning_rate_fresh: float

    # Learning rate when continuing training on an already fine-tuned model
    # Lower than fresh to avoid overwriting what the model already learned
    learning_rate_resume: float

    # Root directory everything is relative to
    # "." for local, "/content/drive/MyDrive" for Colab
    base_dir: str

    # Where the base T5-small weights are stored
    # Downloaded once from HuggingFace and reused across runs
    model_cache: str

    # Where the fine-tuned model is saved after training
    # Also used to resume training if a checkpoint already exists there
    output_dir: str

    # Path to the synthetic YAML training data file
    data_path: str

    # Path to the real labeled examples YAML file
    # Optional — training skips it gracefully if the file does not exist
    real_data_path: str

    def __init__(self, env: str):
        self.env = env
        if env == "local":
            self.setup_local()
        elif env == "colab":
            self.setup_colab()
        else:
            raise ValueError(f"Unknown env '{env}', must be 'local' or 'colab'")

        if not torch.cuda.is_available():
            self.fp16 = False
            self.dataloader_num_workers = 0
            self.dataloader_pin_memory = False

    def setup_local(self):
        self.max_limit                   = 10
        self.num_train_epochs            = 3
        self.per_device_train_batch_size = 8
        self.per_device_eval_batch_size  = 8
        self.gradient_accumulation_steps = 16
        self.fp16                        = True
        self.dataloader_num_workers      = 4
        self.dataloader_pin_memory       = True
        self.logging_steps               = 10
        self.learning_rate_fresh         = 2e-5
        self.learning_rate_resume        = 5e-6

        self.base_dir       = "."
        self.model_cache    = f"./models/google-t5/t5-small"
        self.output_dir     = f"./models/{vars.PARSER_MODEL_NAME}"
        self.data_path      = f"./data/{vars.SYNTHETIC_DATASET_PATH}"
        self.real_data_path = f"./data/{vars.REAL_DATASET_PATH}"

    def setup_colab(self):
        self.max_limit                   = 20000
        self.num_train_epochs            = 3
        self.per_device_train_batch_size = 8
        self.per_device_eval_batch_size  = 8
        self.gradient_accumulation_steps = 16
        self.fp16                        = True
        self.dataloader_num_workers      = 2
        self.dataloader_pin_memory       = False
        self.logging_steps               = 10
        self.learning_rate_fresh         = 2e-5
        self.learning_rate_resume        = 5e-6

        self.base_dir       = "/content/drive/MyDrive"
        self.model_cache    = f"{self.base_dir}/models/google-t5/t5-small"
        self.output_dir     = f"{self.base_dir}/models/{vars.PARSER_MODEL_NAME}"
        self.data_path      = f"{self.base_dir}/data/{vars.SYNTHETIC_DATASET_PATH}"
        self.real_data_path = f"{self.base_dir}/data/{vars.REAL_DATASET_PATH}"