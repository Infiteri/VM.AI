"""
    The VM.AI parser module responsible for training and parsing user input into neat code-defined structure

    Module: parser
    Main dev: Vanea
    Written by: Vanea @ 10-03-2026
"""

# parser, todo: ENSURE MODEL GETS LOADED ONCE WHEN BACKEND IS STARTED
class TaskPlannerPredictor:
    def __init__(self, model_path="./models/my_finetuned_task_planner"):
        print("Loading model...")
        label_mapping_path = os.path.join(model_path, "label_mapping.json")
        if os.path.exists(label_mapping_path):

            with open(label_mapping_path, "r") as f:
                mapping = json.load(f)

            self.label_list = mapping["label_list"]
            self.label2id = mapping["label2id"]
            self.id2label = {int(k): v for k, v in mapping["id2label"].items()}

        else:
            raise RuntimeError("label_mapping.json missing")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path,
            num_labels=len(self.label_list),
            id2label=self.id2label,
            label2id=self.label2id
        )

        self.model.to(self.device)
        self.model.eval()

    def normalize(self, text: str):
        text = text.lower().strip()
        text = re.sub(r'(\d)(am|pm)', r'\1 \2', text)
        return text


    def predict(self, sentence: str) -> Dict:
        sentence = self.normalize(sentence)
        tokens = sentence.split()
        encoding = self.tokenizer(
            tokens,
            is_split_into_words=True,
            truncation=True,
            return_tensors="pt",
            padding="max_length",
            max_length=128
        )

        word_ids = encoding.word_ids()
        inputs = {k: v.to(self.device) for k, v in encoding.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().numpy()
        entities = []
        current_entity = None
        current_tokens = []

        seen_words = set()

        for i, word_idx in enumerate(word_ids):
            if word_idx is None:
                continue

            if word_idx in seen_words:
                continue

            seen_words.add(word_idx)
            label = self.id2label[predictions[i]]
            word = tokens[word_idx]

            if label.startswith("B-"):
                if current_entity:
                    entities.append((current_entity, " ".join(current_tokens)))
                current_entity = label[2:]
                current_tokens = [word]

            elif label.startswith("I-") and current_entity == label[2:]:
                current_tokens.append(word)
            else:
                if current_entity:
                    entities.append((current_entity, " ".join(current_tokens)))
                current_entity = None
                current_tokens = []

        if current_entity:
            entities.append((current_entity, " ".join(current_tokens)))

        output = {
            "task": [],
            "duration": [],
            "deadline": [],
            "date": [],
            "time": [],
            "person": [],
            "location": [],
            "priority": [],
            "project": [],
            "meeting": [],
            "cost": [],
            "quantity": [],
            "contact": [],
            "email": [],
            "phone": [],
            "recurrence": [],
            "other": []
        }

        type_mapping = {
            "TASK": "task",
            "DURATION": "duration",
            "DEADLINE": "deadline",
            "DATE": "date",
            "TIME": "time",
            "PERSON": "person",
            "LOCATION": "location",
            "PRIORITY": "priority",
            "PROJECT": "project",
            "MEETING": "meeting",
            "COST": "cost",
            "QUANTITY": "quantity",
            "CONTACT": "contact",
            "EMAIL": "email",
            "PHONE": "phone",
            "RECURRENCE": "recurrence"
        }

        for ent_type, text in entities:
            ent_type = ent_type.upper()
            if ent_type in type_mapping:
                category = type_mapping[ent_type]
                if text not in output[category]:
                    output[category].append(text)
            else:
                entry = f"{ent_type.lower()}:{text}"
                if entry not in output["other"]:
                    output["other"].append(entry)

        return output

# todo: TEST
def parse_input_to_json(input):
    pr = TaskPlannerPredictor()
    return pr.predict(input)