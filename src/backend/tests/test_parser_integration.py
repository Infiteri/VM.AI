"""
Parser Integration Test Script - Raw Output Version
10 tests for add mode, 10 tests for modify mode.
Logs RAW input and output (no conversion, no processing).
Logs to logs/parser_raw_{test_type}_{YYYYMMDD_HHMMSS}.log

Run from src/backend directory:
    python tests/test_parser_integration.py
"""

import sys
import os
import json
from datetime import datetime

# Add parser directory to path (goes up to src/backend, then to src/parser)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parser_dir = os.path.join(os.path.dirname(backend_dir), "parser")
sys.path.insert(0, parser_dir)

from chat import TaskPlannerPredictor


LOG_DIR = os.path.join(backend_dir, "logs")


class TestLogger:
    """File-based logger for parser tests."""

    def __init__(self, test_type: str):
        self.test_type = test_type
        self.log_file = None
        self._open_log()

    def _open_log(self):
        """Open log file for this test type."""
        os.makedirs(LOG_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parser_raw_{self.test_type}_{date_str}.log"
        filepath = os.path.join(LOG_DIR, filename)
        self.log_file = open(filepath, "w", encoding="utf-8")
        print(f"Logging to: {filepath}")

    def write(self, content: str):
        """Write to log file."""
        self.log_file.write(content)
        print(content, end="")

    def close(self):
        """Close log file."""
        if self.log_file:
            self.log_file.close()


def test_add_mode():
    """Test add mode with 10 test cases - RAW output."""
    logger = TestLogger("add_mode")
    logger.write("=" * 70 + "\n")
    logger.write("TEST ADD MODE - RAW OUTPUT (10 test cases)\n")
    logger.write("=" * 70 + "\n\n")

    test_cases = [
        "gym session",
        "workout at gym for 1 hour",
        "I need to make my math homework at home before Friday, it is very difficult. I also need to start at 13:00",
        "doctor appointment tomorrow",
        "easy yoga every monday",
        "urgent meeting at office",
        "buy groceries at supermarket",
        "pay rent on Friday",
        "code presentation for monday",
        "pick up kids from school",
    ]

    # Initialize parser
    logger.write("Loading TaskPlannerPredictor...\n")
    predictor = TaskPlannerPredictor()
    logger.write("Predictor loaded!\n\n")

    results = []

    for i, test_input in enumerate(test_cases, 1):
        logger.write("=" * 60 + "\n")
        logger.write(f"TEST {i}: ADD MODE\n")
        logger.write("=" * 60 + "\n")
        
        # RAW INPUT - exactly as passed to parser
        logger.write(f"INPUT (raw string): {repr(test_input)}\n")
        logger.write(f"INPUT (display): {test_input}\n")
        
        try:
            # Get RAW output from parser
            output = predictor.predict_add(test_input)
            
            # RAW OUTPUT - directly from parser
            logger.write(f"\nOUTPUT (raw dict):\n")
            logger.write(f"  type: {type(output)}\n")
            logger.write(f"  keys: {list(output.keys())}\n\n")
            
            # Field-by-field breakdown
            logger.write("FIELD BREAKDOWN:\n")
            for field, entry in output.items():
                logger.write(f"  {field}:\n")
                logger.write(f"    - value: {repr(entry.get('value'))} (type: {type(entry.get('value')).__name__})\n")
                logger.write(f"    - predicted: {repr(entry.get('predicted'))} (type: {type(entry.get('predicted')).__name__})\n")
            
            logger.write("\n")
            
            results.append({
                "test_num": i,
                "input": test_input,
                "output": output,
                "success": True,
            })
        except Exception as e:
            logger.write(f"ERROR: {str(e)}\n")
            results.append({
                "test_num": i,
                "input": test_input,
                "output": None,
                "error": str(e),
                "success": False,
            })

    logger.write("\n" + "=" * 70 + "\n")
    logger.write("SUMMARY\n")
    logger.write("=" * 70 + "\n")
    for r in results:
        status = "OK" if r["success"] else "ERROR"
        logger.write(f"Test {r['test_num']}: {r['input'][:30]}... - {status}\n")

    logger.close()
    return results


def test_modify_mode():
    """Test modify mode with 10 test cases - RAW output."""
    logger = TestLogger("modify_mode")
    logger.write("=" * 70 + "\n")
    logger.write("TEST MODIFY MODE - RAW OUTPUT (10 test cases)\n")
    logger.write("=" * 70 + "\n\n")

    # Sample existing task for modify tests
    existing_task = {
        "name": {"value": "gym session", "predicted": False},
        "start": {"value": None, "predicted": True},
        "deadline": {"value": None, "predicted": True},
        "difficulty": {"value": "0.5", "predicted": True},
        "duration": {"value": "60", "predicted": False},
        "category": {"value": "fitness", "predicted": False},
        "location": {"value": "gym", "predicted": False},
        "importance": {"value": "0.5", "predicted": False},
        "fixed_time": {"value": False, "predicted": False},
        "fixed_start": {"value": None, "predicted": False},
    }

    test_cases = [
        ("make it urgent", "make it urgent"),
        ("make it harder", "make it harder"),
        ("change deadline to monday", "change deadline to monday"),
        ("set time to 3pm", "set time to 3pm"),
        ("make it optional", "make it optional"),
        ("push deadline to friday", "push deadline to friday"),
        ("change location to gym", "change location to gym"),
        ("increase duration to 2 hours", "increase duration to 2 hours"),
        ("make it easier", "make it easier"),
        ("cancel recurrence", "cancel recurrence"),
    ]

    # Initialize parser
    logger.write("Loading TaskPlannerPredictor...\n")
    predictor = TaskPlannerPredictor()
    logger.write("Predictor loaded!\n\n")

    results = []

    for i, (change_desc, change_prompt) in enumerate(test_cases, 1):
        logger.write("=" * 60 + "\n")
        logger.write(f"TEST {i}: MODIFY MODE\n")
        logger.write("=" * 60 + "\n")
        
        # RAW INPUT
        logger.write(f"Change description: {repr(change_desc)}\n")
        logger.write(f"Change prompt (raw): {repr(change_prompt)}\n")
        
        logger.write(f"\nExisting task (raw dict):\n")
        logger.write(f"  type: {type(existing_task)}\n")
        logger.write(f"  keys: {list(existing_task.keys())}\n")
        
        try:
            # Get RAW output from parser
            output = predictor.predict_modify(existing_task, change_prompt)
            
            # RAW OUTPUT
            logger.write(f"\nOUTPUT (raw dict):\n")
            logger.write(f"  type: {type(output)}\n")
            logger.write(f"  keys: {list(output.keys())}\n\n")
            
            # Field-by-field breakdown
            logger.write("FIELD BREAKDOWN:\n")
            for field, entry in output.items():
                logger.write(f"  {field}:\n")
                logger.write(f"    - value: {repr(entry.get('value'))} (type: {type(entry.get('value')).__name__})\n")
                logger.write(f"    - predicted: {repr(entry.get('predicted'))} (type: {type(entry.get('predicted')).__name__})\n")
            
            logger.write("\n")
            
            results.append({
                "test_num": i,
                "change_desc": change_desc,
                "change_prompt": change_prompt,
                "output": output,
                "success": True,
            })
        except Exception as e:
            logger.write(f"ERROR: {str(e)}\n")
            results.append({
                "test_num": i,
                "change_desc": change_desc,
                "change_prompt": change_prompt,
                "output": None,
                "error": str(e),
                "success": False,
            })

    logger.write("\n" + "=" * 70 + "\n")
    logger.write("SUMMARY\n")
    logger.write("=" * 70 + "\n")
    for r in results:
        status = "OK" if r["success"] else "ERROR"
        logger.write(f"Test {r['test_num']}: {r['change_desc'][:30]}... - {status}\n")

    logger.close()
    return results


def main():
    print("\n" + "=" * 60)
    print("   PARSER INTEGRATION TESTS - RAW OUTPUT")
    print("=" * 60)

    print("\n--- Test 1: ADD MODE ---")
    add_results = test_add_mode()
    print(f"Add mode completed: {len([r for r in add_results if r['success']])} / {len(add_results)} passed")

    print("\n--- Test 2: MODIFY MODE ---")
    modify_results = test_modify_mode()
    print(f"Modify mode completed: {len([r for r in modify_results if r['success']])} / {len(modify_results)} passed")

    print("\n" + "=" * 60)
    print("   TESTS COMPLETE")
    print("=" * 60)
    print(f"\nLogs saved to: {LOG_DIR}/parser_raw_*.log")


if __name__ == "__main__":
    main()