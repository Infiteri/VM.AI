"""
    The VM.AI Data Generator from YAML
    This class is responsible for generating training data

    Written for testing purposes but also to be used in the main training code
    Written by: Vanea @ 06-03-2026
"""

import vars
import random
import argparse
from datasets import Dataset

print_sentences = False

class VMAI_DataGenerator:
    def __init__(self, training_data):
        self.training_data = training_data

    def generate(self, max_examples=100000):
        templates = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()

        data = {"input_text": [], "target_text": []}

        for _ in range(max_examples):
            template = random.choice(templates)
            sentence = template
            placeholder_map = {}

            for ph, options in all_placeholders.items():
                tag = f"[{ph}]"
                if tag in sentence:
                    value = str(random.choice(options))
                    sentence = sentence.replace(tag, value)
                    placeholder_map[value] = ph

            input_text = f"extract: {sentence.lower().strip()}"
            target_parts = [f"{etype}: {val}" for val, etype in placeholder_map.items()]
            target_text = " | ".join(target_parts)

            data["input_text"].append(input_text)
            data["target_text"].append(target_text)

            if print_sentences:
                print("IN: " + input_text)
                print("TARGET: " + target_text)

        return Dataset.from_dict(data)

if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser
    print_sentences = True

    parser_arg = argparse.ArgumentParser(description="VM.AI Data Generator")
    parser_arg.add_argument('--sentences', type=int, default=1000, help='Number of sentences to generate (default: 1000)')
    args = parser_arg.parse_args()

    yaml_parser = VMAI_YamlParser(f'./data/{vars.SYNTHETIC_DATASET_PATH}')
    yaml_parser.load_yaml()
    training_data = yaml_parser.parse()

    print("VM.AI Sentence Generation Test:")
    print(f"Generating {args.sentences} sentences...")
    print("-" * 30)

    dataset = VMAI_DataGenerator(training_data).generate(max_examples=args.sentences)

    print("-" * 30)
    print(f"Successfully generated {len(dataset)} examples.")