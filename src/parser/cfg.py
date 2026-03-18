# parser/cfg.py

import os
import torch
import vars

class EnvConfig:
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
        self.max_limit                  = 100
        self.num_train_epochs           = 3
        self.per_device_train_batch_size= 8
        self.per_device_eval_batch_size = 8
        self.gradient_accumulation_steps= 16
        
        self.fp16                       = True
        self.dataloader_num_workers     = 4
        self.dataloader_pin_memory      = True
        self.logging_steps              = 10

        self.base_dir                   = "."
        self.model_cache                = f"./models/google-t5/t5-small"
        self.output_dir                 = f"./models/{vars.PARSER_MODEL_NAME}"
        self.data_path                  = f"./data/{vars.SYNTHETIC_DATASET_PATH}"

    def setup_colab(self):
        self.max_limit                  = 10000
        self.num_train_epochs           = 3
        self.per_device_train_batch_size= 8
        self.per_device_eval_batch_size = 8
        self.gradient_accumulation_steps= 16
        self.fp16                       = True
        self.dataloader_num_workers     = 2
        self.dataloader_pin_memory      = False 
        self.logging_steps              = 10

        self.base_dir                   = "/content/drive/MyDrive"
        self.model_cache                = f"{self.base_dir}/models/google-t5/t5-small"
        self.output_dir                 = f"{self.base_dir}/models/{vars.PARSER_MODEL_NAME}"
        self.data_path                  = f"{self.base_dir}/data/{vars.SYNTHETIC_DATASET_PATH}"