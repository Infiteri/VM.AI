"""
    VM-AI - Training Data Validator and Fixer
    Checks and corrects issues in training data YAML files.
    Run: python src/parser/validate_dataset.py

    Written by: Vanea
"""

import yaml
import re
import os
import json
import shutil
import glob
from datetime import datetime
from typing import Dict, List, Any, Tuple
import argparse
import sys

def validate_and_fix_training_data(file_path: str) -> Dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    stats = {
        "file": file_path,
        "total": len(data.get("examples", [])),
        "fixed": 0,
        "issues": []
    }
    
    fixed_examples = []
    
    for idx, example in enumerate(data.get("examples", [])):
        original = example.copy()
        fixed = fix_example(example.copy(), idx)
        
        if fixed != original:
            stats["fixed"] += 1
            stats["issues"].append({
                "index": idx,
                "original_input": original.get("input", "")[:100],
                "fix": get_fix_description(original, fixed)
            })
        
        fixed_examples.append(fixed)
    
    if stats["fixed"] > 0:
        backup_path = file_path.replace(".yaml", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        shutil.copy2(file_path, backup_path)
        stats["backup"] = backup_path
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump({"examples": fixed_examples}, f, allow_unicode=True, sort_keys=False)
    
    return stats

def fix_example(example: Dict, idx: int) -> Dict:
    input_text = example.get("input", "")
    output = example.get("output", {})
    
    for key, value in list(output.items()):
        if isinstance(value, str):
            if value.lower() == "true":
                output[key] = True
            elif value.lower() == "false":
                output[key] = False
    
    if "fixed_start" in output:
        fixed_start = output["fixed_start"]
        if isinstance(fixed_start, (int, float)):
            output["fixed_start"] = f"{int(fixed_start):02d}:00"
        elif isinstance(fixed_start, str):
            if fixed_start.isdigit() and len(fixed_start) <= 2:
                output["fixed_start"] = f"{int(fixed_start):02d}:00"
            elif "am" in fixed_start.lower() or "pm" in fixed_start.lower():
                match = re.search(r'(\d{1,2})(?:am|pm)', fixed_start.lower())
                if match:
                    hour = int(match.group(1))
                    if "pm" in fixed_start.lower() and hour != 12:
                        hour += 12
                    elif "am" in fixed_start.lower() and hour == 12:
                        hour = 0
                    output["fixed_start"] = f"{hour:02d}:00"
    
    if "recurrence_days" in output:
        days = output["recurrence_days"]
        if isinstance(days, str):
            output["recurrence_days"] = [d.strip() for d in days.split(",")]
        elif isinstance(days, list):
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            output["recurrence_days"] = [d.capitalize() for d in days if d.capitalize() in day_names]
            if not output["recurrence_days"]:
                del output["recurrence_days"]
        elif days is None:
            del output["recurrence_days"]
    
    for key in list(output.keys()):
        if output[key] is None:
            del output[key]
    
    if input_text.startswith("modify:"):
        fixed_input = fix_modify_input(input_text)
        if fixed_input != input_text:
            example["input"] = fixed_input
    
    if "fixed_start" in output:
        time_str = output["fixed_start"]
        if isinstance(time_str, str):
            if ":" in time_str:
                parts = time_str.split(":")
                if len(parts) == 2 and parts[0].isdigit():
                    hour = int(parts[0])
                    if 0 <= hour <= 23:
                        output["fixed_start"] = f"{hour:02d}:00"
    
    for key in ["fixed_time", "recurrent"]:
        if key in output:
            if isinstance(output[key], str):
                output[key] = output[key].lower() == "true"
    
    return example

def fix_modify_input(input_text: str) -> str:
    try:
        parts = input_text.split("│")
        if len(parts) != 2:
            return input_text
        
        json_part = parts[0].replace("modify:", "").strip()
        change_part = parts[1].strip()
        
        data = json.loads(json_part)
        
        fixed_json = json.dumps(data, ensure_ascii=False)
        return f"modify: {fixed_json} │ {change_part}"
    
    except:
        return input_text

def get_fix_description(original: Dict, fixed: Dict) -> str:
    changes = []
    
    orig_out = original.get("output", {})
    fixed_out = fixed.get("output", {})
    
    for key in orig_out:
        if key in fixed_out and orig_out[key] != fixed_out[key]:
            changes.append(f"{key}: {orig_out[key]} -> {fixed_out[key]}")
    
    for key in orig_out:
        if key not in fixed_out:
            changes.append(f"removed {key} (was None)")
    
    for key in fixed_out:
        if key not in orig_out:
            changes.append(f"added {key}")
    
    return "; ".join(changes) if changes else "format fix"

def validate_schema(data: Dict, file_name: str = "") -> List[str]:
    errors = []
    valid_fields = {
        "fixed_start", "fixed_time", "recurrent", "recurrence_days",
        "deadline", "duration", "location", "difficulty", "importance",
        "start", "name", "category"
    }
    
    prefix = f"[{file_name}] " if file_name else ""
    
    for idx, example in enumerate(data.get("examples", [])):
        output = example.get("output", {})
        
        for field in output:
            if field not in valid_fields:
                errors.append(f"{prefix}Example {idx}: Invalid field '{field}'")
        
        if output.get("recurrent") is True:
            if "recurrence_days" in output and not output["recurrence_days"]:
                errors.append(f"{prefix}Example {idx}: Empty recurrence_days")
        
        if output.get("fixed_time") is True:
            if "fixed_start" not in output:
                errors.append(f"{prefix}Example {idx}: fixed_time=true but no fixed_start")
        elif output.get("fixed_start") and output.get("fixed_time") is False:
            errors.append(f"{prefix}Example {idx}: fixed_start without fixed_time")
    
    return errors

def generate_stats(data: Dict, file_name: str = "") -> Dict:
    stats = {
        "file": file_name,
        "total_modify": 0,
        "total_add": 0,
        "recurrence_examples": 0,
        "fixed_time_examples": 0,
        "duration_examples": 0,
        "location_examples": 0,
        "deadline_examples": 0,
        "difficulty_examples": 0,
        "importance_examples": 0,
        "category_examples": 0,
        "unique_modify": 0,
        "unique_add": 0,
    }
    
    seen_modify = set()
    seen_add = set()
    
    for example in data.get("examples", []):
        input_text = example.get("input", "")
        output = example.get("output", {})
        
        fingerprint = f"{input_text}|{sorted(output.items())}"
        
        if input_text.startswith("modify:"):
            stats["total_modify"] += 1
            seen_modify.add(fingerprint)
        else:
            stats["total_add"] += 1
            seen_add.add(fingerprint)
        
        if output.get("recurrent"):
            stats["recurrence_examples"] += 1
        if output.get("fixed_time"):
            stats["fixed_time_examples"] += 1
        if output.get("duration"):
            stats["duration_examples"] += 1
        if output.get("location"):
            stats["location_examples"] += 1
        if output.get("deadline"):
            stats["deadline_examples"] += 1
        if output.get("difficulty"):
            stats["difficulty_examples"] += 1
        if output.get("importance"):
            stats["importance_examples"] += 1
        if output.get("category"):
            stats["category_examples"] += 1
    
    stats["unique_modify"] = len(seen_modify)
    stats["unique_add"] = len(seen_add)
    
    return stats

def check_duplicates(data: Dict, file_name: str = "") -> List[int]:
    seen = {}
    duplicates = []
    
    def make_hashable(obj):
        if isinstance(obj, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(make_hashable(item) for item in obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    for idx, example in enumerate(data.get("examples", [])):
        input_text = example.get("input", "")
        output = example.get("output", {})
        
        key = (input_text, make_hashable(output))
        
        if key in seen:
            duplicates.append(idx)
        else:
            seen[key] = idx
    
    return duplicates

def process_file(file_path: str, auto_fix: bool = False) -> Dict:
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "file": file_path}
    
    result = {
        "file": file_path,
        "exists": True,
        "stats": {},
        "errors": [],
        "duplicates": [],
        "fixed": False
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    file_name = os.path.basename(file_path)
    
    result["duplicates"] = check_duplicates(data, file_name)
    result["errors"] = validate_schema(data, file_name)
    result["stats"] = generate_stats(data, file_name)
    
    if (result["duplicates"] or result["errors"]) and auto_fix:
        fix_stats = validate_and_fix_training_data(file_path)
        result["fixed"] = True
        result["fix_stats"] = fix_stats
        
        with open(file_path, 'r', encoding='utf-8') as f:
            fixed_data = yaml.safe_load(f)
        result["stats_after"] = generate_stats(fixed_data, file_name)
        result["errors_after"] = validate_schema(fixed_data, file_name)
        result["duplicates_after"] = check_duplicates(fixed_data, file_name)
    
    return result

def print_report(results: List[Dict]):
    print("\n" + "-" * 80)
    print("VM.AI TRAINING DATA VALIDATION REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    total_modify = 0
    total_add = 0
    total_unique_modify = 0
    total_unique_add = 0
    total_recurrence = 0
    total_fixed_time = 0
    total_duration = 0
    total_location = 0
    total_deadline = 0
    total_difficulty = 0
    total_importance = 0
    total_category = 0
    total_errors = 0
    total_duplicates = 0
    files_fixed = 0
    
    for result in results:
        if "error" in result:
            print(f"\n[ERROR] {result['file']}: {result['error']}")
            continue
        
        file_name = os.path.basename(result["file"])
        stats = result["stats"]
        
        print(f"\nFILE: {file_name}")
        print(f"  Total examples: {stats['total_modify'] + stats['total_add']}")
        print(f"  Modify examples: {stats['total_modify']} ({stats['unique_modify']} unique)")
        print(f"  Add examples: {stats['total_add']} ({stats['unique_add']} unique)")
        print(f"  Recurrence examples: {stats['recurrence_examples']}")
        print(f"  Fixed time examples: {stats['fixed_time_examples']}")
        print(f"  Duration examples: {stats['duration_examples']}")
        print(f"  Location examples: {stats['location_examples']}")
        print(f"  Deadline examples: {stats['deadline_examples']}")
        print(f"  Difficulty examples: {stats['difficulty_examples']}")
        print(f"  Importance examples: {stats['importance_examples']}")
        print(f"  Category examples: {stats['category_examples']}")
        
        if result["duplicates"]:
            print(f"  DUPLICATES: {len(result['duplicates'])} found")
            if len(result["duplicates"]) <= 10:
                print(f"    Indices: {result['duplicates']}")
        
        if result["errors"]:
            print(f"  SCHEMA ERRORS: {len(result['errors'])} found")
            for error in result["errors"][:5]:
                print(f"    - {error}")
            if len(result["errors"]) > 5:
                print(f"    ... and {len(result['errors']) - 5} more")
        
        if result.get("fixed"):
            print(f"  FIXED: Yes")
            files_fixed += 1
            if "fix_stats" in result:
                print(f"    Examples fixed: {result['fix_stats']['fixed']}")
                if result.get("stats_after"):
                    after = result["stats_after"]
                    print(f"    After fix - Modify: {after['total_modify']} ({after['unique_modify']} unique)")
                    print(f"                Add: {after['total_add']} ({after['unique_add']} unique)")
        
        total_modify += stats['total_modify']
        total_add += stats['total_add']
        total_unique_modify += stats['unique_modify']
        total_unique_add += stats['unique_add']
        total_recurrence += stats['recurrence_examples']
        total_fixed_time += stats['fixed_time_examples']
        total_duration += stats['duration_examples']
        total_location += stats['location_examples']
        total_deadline += stats['deadline_examples']
        total_difficulty += stats['difficulty_examples']
        total_importance += stats['importance_examples']
        total_category += stats['category_examples']
        total_errors += len(result["errors"])
        total_duplicates += len(result["duplicates"])
    
    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Files processed: {len(results)}")
    print(f"Files with fixes applied: {files_fixed}")
    print(f"Total examples: {total_modify + total_add}")
    print(f"  - Modify examples: {total_modify} ({total_unique_modify} unique)")
    print(f"  - Add examples: {total_add} ({total_unique_add} unique)")
    print(f"Total recurrence examples: {total_recurrence}")
    print(f"Total fixed time examples: {total_fixed_time}")
    print(f"Total duration examples: {total_duration}")
    print(f"Total location examples: {total_location}")
    print(f"Total deadline examples: {total_deadline}")
    print(f"Total difficulty examples: {total_difficulty}")
    print(f"Total importance examples: {total_importance}")
    print(f"Total category examples: {total_category}")
    print(f"Total schema errors found: {total_errors}")
    print(f"Total duplicates found: {total_duplicates}")
    
    if total_errors > 0 or total_duplicates > 0:
        print("\nWARNING: Issues detected. Run with --fix to automatically fix them.")
    print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="VM.AI Training Data Validator")
    parser.add_argument("files", nargs="+", help="YAML files to validate (supports wildcards)")
    parser.add_argument("--fix", action="store_true", help="Automatically fix issues")
    
    args = parser.parse_args()
    
    all_files = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        if matched:
            all_files.extend(matched)
        else:
            all_files.append(pattern)
    
    if not all_files:
        print("No files found to validate.")
        sys.exit(1)
    
    results = []
    
    for file_path in all_files:
        if not os.path.exists(file_path):
            print(f"Skipping: {file_path} (file not found)")
            continue
        print(f"Processing: {file_path}")
        result = process_file(file_path, auto_fix=args.fix)
        results.append(result)
    
    if results:
        print_report(results)

if __name__ == "__main__":
    main()