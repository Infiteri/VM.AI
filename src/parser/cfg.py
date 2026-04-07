import os
import torch
import yaml

class Config:
    def __init__(self, mode="both", config_path="config.yaml"):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        yaml_path = os.path.join(root, config_path)
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            
        self.model_cache        = os.path.join(root, cfg["paths"]["model_cache"])
        self.output_dir         = os.path.join(root, cfg["paths"]["output_dir"])
        self.data_path          = os.path.join(root, cfg["paths"]["synthetic_data"])
        self.real_data_path     = os.path.join(root, cfg["paths"]["real_data"])
        self.specific_data_path = os.path.join(root, cfg["paths"]["specific_data"])
        
        self.fp16                   = torch.cuda.is_available()
        self.dataloader_num_workers = 4 if torch.cuda.is_available() else 0
        self.dataloader_pin_memory  = torch.cuda.is_available()
        self.logging_steps          = 50
        self.per_device_eval_batch_size = 8
        
        mode_data = cfg.get("modes", {}).get(mode, cfg["modes"]["default"])
        for key, val in mode_data.items():
            # Force learning rates to be floats to prevent YAML string errors
            if "learning_rate" in key:
                val = float(val)
            setattr(self, key, val)
            
        print(f"Config loaded for mode: {mode}")
        print(f"  Epochs: {self.num_train_epochs}")
        print(f"  LR: {self.learning_rate_resume}")
        print(f"  Batch: {self.per_device_train_batch_size}")
        print(f"  Grad Acc: {self.gradient_accumulation_steps}")
        
    def get_effective_batch_size(self):
        return self.per_device_train_batch_size * self.gradient_accumulation_steps

if __name__ == "__main__":
    import yaml, os
    cfg = Config("both")
    print(f"\nState Check")
    for k, v in vars(cfg).items():
        print(f"  {k}: {v}")
    print(f"Effective Batch Size: {cfg.get_effective_batch_size()}")
