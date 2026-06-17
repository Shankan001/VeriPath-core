import json
import os

DATA_DIR = "data"

SKELETON_FILES = {
    "users.json":        {},
    "companies.json":    {},
    "invite_codes.json": {},
    "consignments.json": [],
    "kpi_overrides.json":{},
}

def ensure_data_files():
    """Call at app startup — creates missing data files with empty structure."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for filename, default in SKELETON_FILES.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f, indent=2)

if __name__ == "__main__":
    ensure_data_files()
    print("✅ All data files initialised.")
    for f in SKELETON_FILES:
        print(f"   data/{f}")
