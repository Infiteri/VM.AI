import sys
sys.path.insert(0, 'D:/Users/user/Desktop/VM.AI/src/parser')
from chat import TaskPlannerPredictor

p = TaskPlannerPredictor()

tests = [
    ({"name": "gym", "fixed_time": True, "fixed_start": "06:00", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "recurrent": False}, "move to 7am"),
    ({"name": "meeting", "fixed_time": True, "fixed_start": "14:00", "duration": 30, "category": "work", "difficulty": 0.2, "importance": 0.6, "recurrent": False}, "make it 1 hour"),
    ({"name": "workout", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "make it harder"),
    ({"name": "client call", "importance": 0.5, "duration": 30, "category": "work", "difficulty": 0.3, "fixed_time": False, "recurrent": False}, "make it urgent"),
    ({"name": "yoga", "category": "work", "duration": 60, "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "categorize it as fitness"),
]

print("=" * 60)
print("  MODIFY TESTS (After chat.py fix)")
print("=" * 60)

for i, (task, change) in enumerate(tests, 1):
    schema = {k: {"value": v, "predicted": False} for k, v in task.items()}
    result = p.predict_modify(schema, change)
    print(f"\n{i}. Change: {change}")
    if "error" not in result:
        for field, entry in result.items():
            if isinstance(entry, dict):
                print(f"   -> {field}: {entry.get('value')}")
    else:
        print(f"   ERROR: {result}")
