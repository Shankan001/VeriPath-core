import json
import os
from datetime import datetime

# ── Storage path ──────────────────────────────────────────────
DATA_DIR = "data"
DB_FILE  = os.path.join(DATA_DIR, "consignments.json")

def _ensure_dir():
    """Create the data/ folder if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)

# ── Core functions ─────────────────────────────────────────────

def load_consignments() -> list[dict]:
    """Load all consignments from disk. Returns empty list if none saved yet."""
    _ensure_dir()
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_consignments(records: list[dict]) -> None:
    """Overwrite the entire consignments file with the provided list."""
    _ensure_dir()
    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=2, default=str)

def add_consignment(record: dict) -> list[dict]:
    """
    Append a single consignment record and persist to disk.
    Automatically stamps it with an ID and created_at timestamp.
    Returns the full updated list.
    """
    records = load_consignments()
    record["id"] = f"VP-{len(records) + 1:04d}"          # e.g. VP-0001
    record["created_at"] = datetime.utcnow().isoformat()  # UTC timestamp
    records.append(record)
    save_consignments(records)
    return records

def delete_consignment(record_id: str) -> list[dict]:
    """Remove a consignment by its VP-XXXX id. Returns updated list."""
    records = load_consignments()
    records = [r for r in records if r.get("id") != record_id]
    save_consignments(records)
    return records

def clear_all_consignments() -> None:
    """Wipe all data. Use carefully — useful for demo resets."""
    save_consignments([])

# ── Quick test (run: python db.py) ────────────────────────────
if __name__ == "__main__":
    clear_all_consignments()
    
    test_record = {
        "exporter":    "Kakuzi PLC",
        "crop":        "Avocado",
        "weight_kg":   5000,
        "county":      "Murang'a",
        "hs_code":     "0804.40",
        "kra_pin":     "A123456789B",
        "destination": "Netherlands",
    }
    
    updated = add_consignment(test_record)
    print(f"✅ Added record. Total records: {len(updated)}")
    print(f"   ID assigned: {updated[0]['id']}")
    print(f"   Timestamp:   {updated[0]['created_at']}")
    
    loaded = load_consignments()
    print(f"✅ Reload from disk confirmed: {len(loaded)} record(s)")
    print("\nFull record:")
    print(json.dumps(loaded[0], indent=2))
