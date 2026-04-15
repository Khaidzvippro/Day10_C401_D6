import sys
from pathlib import Path

# Add day10/lab to path
sys.path.append('day10/lab')
from transform.cleaning_rules import load_raw_csv, clean_rows

def test_file(file_path):
    print(f"\n===== Testing {file_path} =====")
    rows = load_raw_csv(Path(file_path))
    cleaned, quarantine = clean_rows(rows)
    print(f"Total Rows     : {len(rows)}")
    print(f"Cleaned Rows   : {len(cleaned)}")
    print(f"Quarantine Rows: {len(quarantine)}")
    
    reasons = {}
    for q in quarantine:
        reason = q.get('reason', 'unknown')
        reasons[reason] = reasons.get(reason, 0) + 1
        
    print("Quarantine Reasons Distribution:")
    for r, c in reasons.items():
        print(f"  - {r}: {c}")

test_file("day10/lab/data/raw/policy_export_dirty.csv")
test_file("day10/lab/data/raw/policy_export_dirty_test.csv")
