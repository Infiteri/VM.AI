# interactive_task_planner.py (fixed duplicate detection)
import torch
import json
import os
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification
from typing import Dict, List

class TaskPlannerPredictor:
    def __init__(self, model_path="./models/my_finetuned_task_planner"):
        """Initialize the predictor with a fine-tuned model"""
        print(f"Loading model...")
        
        # Load label mapping
        label_mapping_path = os.path.join(model_path, "label_mapping.json")
        if os.path.exists(label_mapping_path):
            with open(label_mapping_path, "r") as f:
                mapping = json.load(f)
                self.label_list = mapping["label_list"]
                self.label2id = mapping["label2id"]
                self.id2label = {int(k): v for k, v in mapping["id2label"].items()}
        else:
            self.label_list = ["O", "B-TASK", "I-TASK", "B-DURATION", "I-DURATION", 
                              "B-DEADLINE", "I-DEADLINE", "B-PERSON", "I-PERSON", 
                              "B-TIME", "I-TIME", "B-DATE", "I-DATE"]
            self.label2id = {label: i for i, label in enumerate(self.label_list)}
            self.id2label = {i: label for label, i in self.label2id.items()}
        
        # Load model and tokenizer
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
        print("✓ Model ready")
    
    def predict(self, sentence: str) -> Dict:
        """Predict entities in a sentence and return structured output"""
        tokens = sentence.split()
        
        # Prepare input
        inputs = self.tokenizer(
            tokens,
            truncation=True,
            is_split_into_words=True,
            return_tensors="pt",
            padding="max_length",
            max_length=128
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().numpy()
        
        # First pass: collect all entity spans
        raw_entities = []
        current_entity = None
        current_text = []
        current_start = -1
        current_end = -1
        
        word_ids = self.tokenizer(sentence.split(), is_split_into_words=True).word_ids()
        
        for i, word_idx in enumerate(word_ids):
            if word_idx is not None:
                label = self.id2label[predictions[i]]
                
                if label != "O":
                    if label.startswith("B-"):
                        # Save previous entity if exists
                        if current_entity and current_text:
                            raw_entities.append({
                                "entity": current_entity,
                                "text": " ".join(current_text),
                                "start": current_start,
                                "end": current_end,
                                "length": current_end - current_start + 1
                            })
                        # Start new entity
                        current_entity = label[2:]
                        current_text = [tokens[word_idx]]
                        current_start = word_idx
                        current_end = word_idx
                    elif label.startswith("I-") and current_entity == label[2:]:
                        # Continue current entity
                        current_text.append(tokens[word_idx])
                        current_end = word_idx
                else:
                    # Save current entity if exists
                    if current_entity and current_text:
                        raw_entities.append({
                            "entity": current_entity,
                            "text": " ".join(current_text),
                            "start": current_start,
                            "end": current_end,
                            "length": current_end - current_start + 1
                        })
                        current_entity = None
                        current_text = []
                        current_start = -1
                        current_end = -1
        
        # Don't forget the last entity
        if current_entity and current_text:
            raw_entities.append({
                "entity": current_entity,
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end,
                "length": current_end - current_start + 1
            })
        
        # Second pass: resolve overlaps (keep the longest entity for overlapping spans)
        # Sort by start position, then by length (descending)
        raw_entities.sort(key=lambda x: (x['start'], -x['length']))
        
        merged_entities = []
        used_indices = set()
        
        for i, entity in enumerate(raw_entities):
            if i in used_indices:
                continue
            
            # Check if this entity overlaps with any longer entity that starts at same position
            overlapping = False
            for j, other in enumerate(raw_entities):
                if j != i and j not in used_indices:
                    # Check if other entity completely contains this one
                    if (other['start'] <= entity['start'] and 
                        other['end'] >= entity['end'] and
                        other['length'] > entity['length']):
                        overlapping = True
                        break
                    # Check if this is a subspan of a longer entity
                    if (entity['start'] >= other['start'] and 
                        entity['end'] <= other['end'] and
                        other['length'] > entity['length']):
                        overlapping = True
                        break
            
            if not overlapping:
                merged_entities.append(entity)
                # Mark any entities that are fully contained within this one as used
                for j, other in enumerate(raw_entities):
                    if j != i and entity['start'] <= other['start'] and entity['end'] >= other['end']:
                        used_indices.add(j)
        
        # Third pass: group by entity type and clean up
        output = {"task": [], "duration": [], "deadline": [], "date": [], "time": [], "person": [], "other": []}
        
        # Define entity type mappings
        type_mapping = {
            "TASK": "task",
            "DURATION": "duration", 
            "DEADLINE": "deadline",
            "DATE": "date",
            "TIME": "time",
            "PERSON": "person"
        }
        
        for entity in merged_entities:
            entity_type = entity["entity"].upper()
            text = entity["text"]
            
            # Map to output category
            if entity_type in type_mapping:
                category = type_mapping[entity_type]
                # Avoid duplicates within the same category
                if text not in output[category]:
                    output[category].append(text)
            else:
                # Handle unknown entity types
                other_entry = f"{entity_type.lower()}:{text}"
                if other_entry not in output["other"]:
                    output["other"].append(other_entry)
        
        # Special handling: if deadline contains time, don't also extract time separately
        if output["deadline"] and output["time"]:
            # Check if any time is part of a deadline
            times_to_remove = []
            for time_val in output["time"]:
                for deadline_val in output["deadline"]:
                    if time_val in deadline_val:
                        times_to_remove.append(time_val)
                        break
            
            for time_val in times_to_remove:
                output["time"].remove(time_val)
        
        # Special handling: if deadline contains date, don't also extract date separately
        if output["deadline"] and output["date"]:
            dates_to_remove = []
            for date_val in output["date"]:
                for deadline_val in output["deadline"]:
                    if date_val in deadline_val:
                        dates_to_remove.append(date_val)
                        break
            
            for date_val in dates_to_remove:
                output["date"].remove(date_val)
        
        return output

def format_compact_output(results: Dict) -> str:
    """Format results in a compact, readable way"""
    output_parts = []
    
    # Tasks
    if results["task"]:
        tasks = ",".join(results["task"])
        output_parts.append(f"📋{tasks}")
    
    # Duration (simplify)
    if results["duration"]:
        durations = []
        for d in results["duration"]:
            # Try to simplify duration (e.g., "2 hours" -> "2h")
            nums = re.findall(r'\d+', d)
            if nums and ("hour" in d or "hr" in d):
                durations.append(f"{nums[0]}h")
            elif nums and ("min" in d):
                durations.append(f"{nums[0]}m")
            else:
                durations.append(d)
        output_parts.append(f"⏱️{','.join(durations)}")
    
    # Deadline
    if results["deadline"]:
        output_parts.append(f"📅{','.join(results['deadline'])}")
    
    # Date (if not in deadline)
    if results["date"]:
        output_parts.append(f"📆{','.join(results['date'])}")
    
    # Time (if not in deadline)
    if results["time"]:
        # Clean up time format
        times = []
        for t in results["time"]:
            # Remove "at" if present
            t = re.sub(r'^at\s+', '', t)
            times.append(t)
        output_parts.append(f"⏰{','.join(times)}")
    
    # Person
    if results["person"]:
        output_parts.append(f"👤{','.join(results['person'])}")
    
    # Other
    if results["other"]:
        output_parts.append(f"🔍{','.join(results['other'])}")
    
    return " → " + " | ".join(output_parts) if output_parts else " → ❌ None"

def main():
    print("\n" + "=" * 50)
    print("🗓️  TASK PLANNER")
    print("=" * 50)
    
    try:
        predictor = TaskPlannerPredictor()
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print("\nCommands: [type 'end' to exit]")
    print("-" * 50)
    
    count = 0
    while True:
        user_input = input(f"\n{count+1:2d} > ").strip()
        
        if user_input.upper() == "END":
            print("\n" + "=" * 50)
            print(f"Goodbye! Processed {count} sentences")
            print("=" * 50)
            break
        
        if not user_input:
            continue
        
        try:
            results = predictor.predict(user_input)
            print(format_compact_output(results))
            count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    main()