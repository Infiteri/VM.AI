from datasets import load_dataset

dataset = load_dataset("conll2003")
dataset.push_to_hub("your-username/conll2003-local")