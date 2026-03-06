"""
    The VM.AI Data Generator from YAML
    This class is responsible for generating training data

    Written for testing purposes but also to be used in the main training code
    Written by: Vanea @ 06-03-2026
"""

import random
import argparse
from datasets import Dataset

class VMAI_DataGenerator:
    def __init__(self, training_data):
        self.training_data = training_data

    def generate(self, max_examples=100000):
        templates = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()

        data = {"tokens": [], "labels": []}
        num_to_gen = max_examples

        for _ in range(num_to_gen):
            template = random.choice(templates)
            sentence = template
            placeholder_map = {}

            for ph, options in all_placeholders.items():
                tag = f"[{ph}]"
                if tag in sentence:
                    value = str(random.choice(options))
                    sentence = sentence.replace(tag, value)
                    placeholder_map[value] = ph

            tokens = sentence.split()
            labels = ["O"] * len(tokens)

            for entity_text, entity_type in placeholder_map.items():
                entity_tokens = entity_text.split()
                for j in range(len(tokens) - len(entity_tokens) + 1):
                    if tokens[j:j + len(entity_tokens)] == entity_tokens:
                        labels[j] = f"B-{entity_type}"
                        for k in range(1, len(entity_tokens)):
                            labels[j + k] = f"I-{entity_type}"
                        break

            data["tokens"].append(tokens)
            data["labels"].append([self.training_data.label2id.get(l, 0) for l in labels])

        return Dataset.from_dict(data)

if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser

    # 1. Setup Argument Parser
    parser_arg = argparse.ArgumentParser(description="VM.AI Data Generator")
    
    # Add the sentences argument with a default value
    parser_arg.add_argument(
        '--sentences', 
        type=int, 
        default=1000, 
        help='Number of sentences to generate (default: 1000)'
    )
    
    args = parser_arg.parse_args()

    yaml_parser = VMAI_YamlParser('data/VMAI_DataMain.yaml')
    yaml_parser.load_yaml()
    training_data = yaml_parser.parse()

    print("VM.AI Sentence Generation Test:")
    print(f"Generating {args.sentences} sentences...")
    print("-" * 30)

    dataset = VMAI_DataGenerator(training_data).generate(max_examples=args.sentences)
    
    print("-" * 30)
    print(f"Successfully generated {len(dataset)} examples.")