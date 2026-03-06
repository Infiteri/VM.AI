# yaml_parser.py
import yaml
from dataclasses import dataclass, asdict, field
from typing import List, Dict
import pprint

@dataclass
class VMAI_YamlTrainingParsedData:
    label_list: List[str]
    templates: List[str]
    tasks: List[str]
    durations: List[str]
    deadlines: List[str]

    # Extra fields
    persons: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    times: List[str] = field(default_factory=list)
    priorities: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    meetings: List[str] = field(default_factory=list)
    costs: List[str] = field(default_factory=list)
    quantities: List[str] = field(default_factory=list)
    contacts: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    recurrences: List[str] = field(default_factory=list)

    # AUTOGEN
    label2id: Dict[str, int] = field(init=False)
    id2label: Dict[int, str] = field(init=False)

    def __post_init__(self):
        self.label2id = {label: i for i, label in enumerate(self.label_list)}
        self.id2label = {i: label for label, i in self.label2id.items()}

    def print_nice(self):
        print("\n" + "="*60)
        print("VMAI TRAINING CONFIGURATION")
        print("="*60)
        print(f"\n📋 LABELS ({len(self.label_list)}):")
        for i, label in enumerate(self.label_list, 1):
            print(f"  {i}. {label}")

        for field_name in ['templates', 'tasks', 'durations', 'deadlines', 
                           'persons', 'locations', 'dates', 'times', 'priorities',
                           'projects', 'meetings', 'costs', 'quantities', 'contacts',
                           'emails', 'phones', 'recurrences']:
            values = getattr(self, field_name)
            if values:
                icon = "📝" if field_name == "templates" else "✅"
                print(f"\n{icon} {field_name.upper()} ({len(values)} items):")
                for i, v in enumerate(values, 1):
                    print(f"  {i}. {v}")
        print("\n" + "="*60)

    def print_json_like(self):
        print("\n" + "="*60)
        print("VMAI TRAINING CONFIGURATION (JSON-like)")
        print("="*60)
        data_dict = asdict(self)
        pp = pprint.PrettyPrinter(indent=2, width=80)
        pp.pprint(data_dict)
        print("="*60)

class VMAI_YamlParser:
    def __init__(self, yaml_file: str):
        self.yaml_file = yaml_file
        self.data = None

    def load_yaml(self):
        """Load the YAML file into memory"""
        with open(self.yaml_file, 'r', encoding='utf-8') as file:
            self.data = yaml.safe_load(file)

    def parse(self) -> VMAI_YamlTrainingParsedData:
        """Parse YAML data into the dataclass"""
        if not self.data:
            raise ValueError("YAML data not loaded")

        return VMAI_YamlTrainingParsedData(
            label_list=self.data.get("labels", []),
            templates=self.data.get("templates", []),
            tasks=self.data.get("tasks", []),
            durations=self.data.get("durations", []),
            deadlines=self.data.get("deadlines", []),
            persons=self.data.get("persons", []),
            locations=self.data.get("locations", []),
            dates=self.data.get("dates", []),
            times=self.data.get("times", []),
            priorities=self.data.get("priorities", []),
            projects=self.data.get("projects", []),
            meetings=self.data.get("meetings", []),
            costs=self.data.get("costs", []),
            quantities=self.data.get("quantities", []),
            contacts=self.data.get("contacts", []),
            emails=self.data.get("emails", []),
            phones=self.data.get("phones", []),
            recurrences=self.data.get("recurrences", [])
        )

if __name__ == "__main__":
    parser = VMAI_YamlParser('data/VMAI_DataMain.yaml')
    parser.load_yaml()
    parsed_data = parser.parse()
    parsed_data.print_nice()