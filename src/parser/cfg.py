# VM.AI Parser — environment configuration

import os
import torch
import vars

class Config:
    def __init__(self, mode="both"):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.model_cache        = os.path.join(root, "models", "google-t5", "t5-base")
        self.output_dir         = os.path.join(root, "models", vars.PARSER_MODEL_NAME)
        self.data_path          = os.path.join(root, "data", vars.SYNTHETIC_DATASET)
        self.real_data_path     = os.path.join(root, "data", vars.REAL_DATASET)
        self.specific_data_path = os.path.join(root, "data", vars.SPECIFIC_DATASET)

        self.max_limit                   = 9000
        self.num_train_epochs            = 10
        self.per_device_train_batch_size = 4
        self.per_device_eval_batch_size  = 8
        self.gradient_accumulation_steps = 32
        self.logging_steps               = 50
        self.learning_rate_fresh         = 2e-5
        self.learning_rate_resume        = 5e-6

        self._configure_for_mode(mode)

        self.fp16                   = torch.cuda.is_available()
        self.dataloader_num_workers = 4 if torch.cuda.is_available() else 0
        self.dataloader_pin_memory  = torch.cuda.is_available()

        print(f"Config loaded for mode: {mode}")
        print(f"  Epochs: {self.num_train_epochs}")
        print(f"  Learning rate: {self.learning_rate_fresh if mode in ('synthetic', 'modify_only') else self.learning_rate_resume}")
        print(f"  Batch size: {self.per_device_train_batch_size}")
        print(f"  Gradient accumulation: {self.gradient_accumulation_steps}")

    def _configure_for_mode(self, mode):

        if mode == "synthetic":
            self.num_train_epochs            = 10
            self.per_device_train_batch_size = 8
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 16
            self.max_limit                   = 10000
            self.learning_rate_fresh         = 2e-5
            self.learning_rate_resume        = 2e-5

        elif mode == "real":
            self.num_train_epochs            = 5
            self.per_device_train_batch_size = 4
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 32
            self.max_limit                   = 5000
            self.learning_rate_fresh         = 1e-5
            self.learning_rate_resume        = 5e-6

        elif mode == "specific":
            self.num_train_epochs            = 10
            self.per_device_train_batch_size = 4
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 32
            self.max_limit                   = 2000
            self.learning_rate_fresh         = 1e-5
            self.learning_rate_resume        = 5e-6

        elif mode == "both":
            self.num_train_epochs            = 7
            self.per_device_train_batch_size = 6
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 24
            self.max_limit                   = 20000
            self.learning_rate_fresh         = 2e-5
            self.learning_rate_resume        = 5e-6

        elif mode == "modify_only":
            self.num_train_epochs            = 10
            self.per_device_train_batch_size = 4
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 16
            self.max_limit                   = 3000
            self.learning_rate_fresh         = 5e-6
            self.learning_rate_resume        = 5e-6

        else:
            print(f"Warning: Unknown mode '{mode}', using default settings")
            self.num_train_epochs            = 5
            self.per_device_train_batch_size = 4
            self.per_device_eval_batch_size  = 8
            self.gradient_accumulation_steps = 32
            self.max_limit                   = 9000
            self.learning_rate_fresh         = 2e-5
            self.learning_rate_resume        = 5e-6

    def get_effective_batch_size(self):
        """Calculate effective batch size after gradient accumulation"""
        return self.per_device_train_batch_size * self.gradient_accumulation_steps