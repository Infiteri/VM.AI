import yaml
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Union
import pprint

@dataclass
class VMAI_YamlTrainingParsedData:
    label_list: List[str]
    templates: List[str]
    tasks: List[str]
    durations: List[str]
    deadlines: List[str]

    # AUTOGEN
    label2id: Dict[str, int] = field(init=False) 
    id2label: Dict[int, str] = field(init=False)  

    def __post_init__(self):
        self.label2id = {label: i for i, label in enumerate(self.label_list)}
        self.id2label = {i: label for label, i in self.label2id.items()}

    def print_nice(self):
        """Print the parsed data in a nicely formatted way"""
        print("\n" + "="*60)
        print("VMAI TRAINING CONFIGURATION")
        print("="*60)
        
        print(f"\n📋 LABELS ({len(self.label_list)}):")
        for i, label in enumerate(self.label_list, 1):
            print(f"  {i}. {label}")
        
        print(f"\n📝 TEMPLATES ({len(self.templates)}):")
        for i, template in enumerate(self.templates, 1):
            print(f"  {i}. \"{template}\"")
        
        print(f"\n✅ TASKS ({len(self.tasks)}):")
        for i, task in enumerate(self.tasks, 1):
            print(f"  {i}. {task}")
        
        print(f"\n⏱️  DURATIONS ({len(self.durations)}):")
        for i, duration in enumerate(self.durations, 1):
            print(f"  {i}. {duration}")
        
        print(f"\n📅 DEADLINES ({len(self.deadlines)}):")
        for i, deadline in enumerate(self.deadlines, 1):
            print(f"  {i}. {deadline}")
        
        print("\n" + "="*60)
    
    def print_json_like(self):
        """Print in a JSON-like format with proper indentation"""
        print("\n" + "="*60)
        print("VMAI TRAINING CONFIGURATION (JSON-like)")
        print("="*60)
        
        data_dict = asdict(self)
        pp = pprint.PrettyPrinter(indent=2, width=80)
        pp.pprint(data_dict)
        
        print("="*60)
    
    def print_summary(self):
        """Print a brief summary"""
        print("\n" + "="*60)
        print("VMAI CONFIGURATION SUMMARY")
        print("="*60)
        print(f"📋 Labels:     {len(self.label_list)} items")
        print(f"📝 Templates:  {len(self.templates)} items")
        print(f"✅ Tasks:      {len(self.tasks)} items")
        print(f"⏱️  Durations:  {len(self.durations)} items")
        print(f"📅 Deadlines:  {len(self.deadlines)} items")
        print("="*60)

class VMAI_YamlParser:
    def __init__(self, yaml_file):
        self.yaml_file = yaml_file
        self.data = None

    def load_yaml(self):
        with open(self.yaml_file, 'r') as file:
            self.data = yaml.safe_load(file)

    def parse(self) -> VMAI_YamlTrainingParsedData:
        if not self.data:
            raise ValueError("YAML data not loaded")

        label_list = self.data.get("labels", [])
        templates = self.data.get("templates", [])
        tasks = self.data.get("tasks", [])
        durations = self.data.get("durations", [])
        deadlines = self.data.get("deadlines", [])

        return VMAI_YamlTrainingParsedData(
            label_list=label_list,
            templates=templates,
            tasks=tasks,
            durations=durations,
            deadlines=deadlines
        )

if __name__ == "__main__":
    yaml_parser = VMAI_YamlParser('data/VMAI_DataMain.yaml')
    yaml_parser.load_yaml()
    parsed_data = yaml_parser.parse()
    parsed_data.print_nice()