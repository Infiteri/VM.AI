# VM.AI Parser — environment configuration

import os
import torch
import vars

class Config:
    def __init__(self):
        # Root of the project (3 levels up from src/parser/cfg.py)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Paths
        self.model_cache        = os.path.join(root, "models", "google-t5", "t5-base")
        self.output_dir         = os.path.join(root, "models", vars.PARSER_MODEL_NAME)
        self.data_path          = os.path.join(root, "data", vars.SYNTHETIC_DATASET)
        self.real_data_path     = os.path.join(root, "data", vars.REAL_DATASET)
        self.specific_data_path = os.path.join(root, "data", vars.SPECIFIC_DATASET)

        # Training
        self.max_limit                   = 9000
        self.num_train_epochs            = 5
        self.per_device_train_batch_size = 16
        self.per_device_eval_batch_size  = 16
        self.gradient_accumulation_steps = 8
        self.logging_steps               = 50
        self.learning_rate_fresh         = 2e-5
        self.learning_rate_resume        = 5e-6

        # VRAM SAKE
        self.per_device_train_batch_size = 4   
        self.per_device_eval_batch_size  = 8   
        self.gradient_accumulation_steps = 32  

        # Hardware
        self.fp16                   = torch.cuda.is_available()
        self.dataloader_num_workers = 4 if torch.cuda.is_available() else 0
        self.dataloader_pin_memory  = torch.cuda.is_available()