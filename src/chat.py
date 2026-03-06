# interactive_task_planner.py
import torch
import json
import os
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification
from typing import Dict, List, Tuple, Optional

class TaskPlannerPredictor:
    def __init__(self, model_path="./models/my_finetuned_task_planner"):
        """
        Initialize the predictor with a fine-tuned model
        """
        print(f"Loading model from {model_path}...")
        
        # Load label mapping
        label_mapping_path = os.path.join(model_path, "label_mapping.json")
        if os.path.exists(label_mapping_path):
            with open(label_mapping_path, "r") as f:
                mapping = json.load(f)
                self.label_list = mapping["label_list"]
                self.label2id = mapping["label2id"]
                self.id2label = {int(k): v for k, v in mapping["id2label"].items()}
        else:
            # Default labels if mapping file doesn't exist
            self.label_list = ["O", "B-TASK", "I-TASK", "B-DURATION", "I-DURATION", 
                              "B-DEADLINE", "I-DEADLINE"]
            self.label2id = {label: i for i, label in enumerate(self.label_list)}
            self.id2label = {i: label for label, i in self.label2id.items()}
        
        # Load model and tokenizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path,
            num_labels=len(self.label_list),
            id2label=self.id2label,
            label2id=self.label2id
        )
        self.model.to(self.device)
        self.model.eval()
        
        print("Model loaded successfully!")
        print("-" * 50)
    
    def predict(self, sentence: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Predict entities in a sentence and return structured output
        """
        # Tokenize the sentence
        tokens = sentence.split()
        
        # Prepare input for the model
        inputs = self.tokenizer(
            tokens,
            truncation=True,
            is_split_into_words=True,
            return_tensors="pt",
            padding="max_length",
            max_length=128
        )
        
        # Move inputs to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)
        
        # Convert predictions to labels
        predicted_label_ids = predictions[0].cpu().numpy()
        
        # Align predictions with original tokens
        word_ids = inputs['input_ids'][0].cpu().numpy()
        
        # Map predictions back to original tokens
        results = []
        current_entity = None
        current_text = []
        
        # Get the actual tokens (excluding special tokens)
        for i, word_idx in enumerate(self.tokenizer(sentence.split(), is_split_into_words=True).word_ids()):
            if word_idx is not None:
                label_id = predicted_label_ids[i]
                label = self.id2label[label_id]
                
                if label != "O":
                    if label.startswith("B-"):
                        # Save previous entity if exists
                        if current_entity and current_text:
                            results.append({
                                "entity": current_entity,
                                "text": " ".join(current_text)
                            })
                        # Start new entity
                        current_entity = label[2:]  # Remove "B-"
                        current_text = [tokens[word_idx]]
                    elif label.startswith("I-") and current_entity == label[2:]:
                        # Continue current entity
                        current_text.append(tokens[word_idx])
                else:
                    # Save current entity if exists
                    if current_entity and current_text:
                        results.append({
                            "entity": current_entity,
                            "text": " ".join(current_text)
                        })
                        current_entity = None
                        current_text = []
        
        # Don't forget the last entity
        if current_entity and current_text:
            results.append({
                "entity": current_entity,
                "text": " ".join(current_text)
            })
        
        # Organize by entity type
        structured_output = {
            "task": [],
            "duration": [],
            "deadline": [],
            "other": []
        }
        
        for item in results:
            entity_type = item["entity"].lower()
            if entity_type in structured_output:
                structured_output[entity_type].append(item["text"])
            else:
                structured_output["other"].append({
                    "type": entity_type,
                    "value": item["text"]
                })
        
        return structured_output
    
    def format_output(self, structured_output: Dict) -> str:
        """
        Format the structured output in a readable way
        """
        output_lines = []
        output_lines.append("=" * 50)
        output_lines.append("EXTRACTED INFORMATION:")
        output_lines.append("=" * 50)
        
        if structured_output["task"]:
            output_lines.append("\n📋 TASK:")
            for task in structured_output["task"]:
                output_lines.append(f"  • {task}")
        
        if structured_output["duration"]:
            output_lines.append("\n⏱️ DURATION:")
            for duration in structured_output["duration"]:
                output_lines.append(f"  • {duration}")
        
        if structured_output["deadline"]:
            output_lines.append("\n📅 DEADLINE:")
            for deadline in structured_output["deadline"]:
                output_lines.append(f"  • {deadline}")
        
        if structured_output["other"]:
            output_lines.append("\n🔍 OTHER FIELDS:")
            for other in structured_output["other"]:
                output_lines.append(f"  • {other['type']}: {other['value']}")
        
        if not any(structured_output.values()):
            output_lines.append("\n❌ No structured information found in the sentence.")
        
        output_lines.append("\n" + "=" * 50)
        return "\n".join(output_lines)

def main():
    print("\n" + "=" * 60)
    print("TASK PLANNER - Interactive Entity Extraction")
    print("=" * 60)
    print("\nThis tool extracts task, duration, and deadline information from your sentences.")
    print("Type 'END' at any time to exit the program.")
    print("-" * 60)
    
    # Initialize the predictor
    try:
        predictor = TaskPlannerPredictor()
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Make sure you've trained the model first using train_lazy.py")
        return
    
    print("\n" + "✨ Ready to process your sentences! ✨")
    print("Enter your sentences below (or type 'END' to exit):\n")
    
    sentence_count = 0
    
    while True:
        # Get user input
        user_input = input(f"\n[{sentence_count + 1}] Enter sentence: ").strip()
        
        # Check for exit condition
        if user_input.upper() == "END":
            print("\n" + "=" * 60)
            print(f"Exiting program. Processed {sentence_count} sentences.")
            print("=" * 60)
            break
        
        # Skip empty inputs
        if not user_input:
            print("⚠️  Please enter a valid sentence (or 'END' to exit)")
            continue
        
        # Process the input
        try:
            # Get predictions
            results = predictor.predict(user_input)
            
            # Display formatted output
            print(predictor.format_output(results))
            
            # Show raw JSON output as well (optional)
            show_json = input("\nShow raw JSON output? (y/n): ").strip().lower()
            if show_json == 'y':
                print("\n📊 RAW JSON OUTPUT:")
                print(json.dumps(results, indent=2))
            
            sentence_count += 1
            
        except Exception as e:
            print(f"❌ Error processing sentence: {e}")
            print("Please try again with a different sentence.")
        
        print("\n" + "-" * 60)

if __name__ == "__main__":
    main()