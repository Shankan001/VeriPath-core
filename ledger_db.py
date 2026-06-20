import json
import os
from datetime import datetime, timezone

DATA_DIR  = "data"
LEDGER_FILE = os.path.join(DATA_DIR, "ledger.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_ledger(company: str = None) -> list[dict]:
    _ensure_dir()
    if not os.path.exists(LEDGER_FILE):
        return []
    try:
        with open(LEDGER_FILE, "r") as f:
            records = json.load(f)
        if company:
            c = company.strip().lower()
            records = [r for r in records
                       if r.get("company","").strip().lower() == c]
        return records
    except (json.JSONDecodeError, IOError):
        return []

def save_ledger_record(record: dict) -> None:
    """Append one record to ledger. Company field must already be set."""
    _ensure_dir()
    records = load_ledger()
    records.append(record)
    with open(LEDGER_FILE, "w") as f:
        json.dump(records, f, indent=2, default=str)

def update_ledger_record(session_id: str, row_index: int,
                         updated_fields: dict, company: str) -> bool:
    """Edit a specific row within a session. Returns True if found and updated."""
    _ensure_dir()
    if not os.path.exists(LEDGER_FILE):
        return False
    with open(LEDGER_FILE, "r") as f:
        all_records = json.load(f)
    company_lower = company.strip().lower()
    session_rows  = [i for i, r in enumerate(all_records)
                     if r.get("session_id") == session_id
                     and r.get("company","").strip().lower() == company_lower]
    if row_index >= len(session_rows):
        return False
    target_idx = session_rows[row_index]
    all_records[target_idx].update(updated_fields)
    all_records[target_idx]["last_edited"] = datetime.now(timezone.utc).isoformat()
    with open(LEDGER_FILE, "w") as f:
        json.dump(all_records, f, indent=2, default=str)
    return True

def save_full_ledger(records: list[dict]) -> None:
    _ensure_dir()
    with open(LEDGER_FILE, "w") as f:
        json.dump(records, f, indent=2, default=str)

def clear_company_ledger(company: str) -> int:
    """Delete all ledger entries for one company. Returns count deleted."""
    if not os.path.exists(LEDGER_FILE):
        return 0
    with open(LEDGER_FILE, "r") as f:
        all_records = json.load(f)
    company_lower = company.strip().lower()
    kept    = [r for r in all_records
               if r.get("company","").strip().lower() != company_lower]
    deleted = len(all_records) - len(kept)
    save_full_ledger(kept)
    return deleted

def load_farmers(company: str = None) -> dict:
    farmers_file = os.path.join(DATA_DIR, "farmers.json")
    if not os.path.exists(farmers_file):
        return {}
    with open(farmers_file, "r") as f:
        all_farmers = json.load(f)
    if company:
        c = company.strip().lower()
        return {k: v for k, v in all_farmers.items()
                if v.get("company","").strip().lower() == c}
    return all_farmers

def save_farmers(farmers: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    farmers_file = os.path.join(DATA_DIR, "farmers.json")
    if os.path.exists(farmers_file):
        with open(farmers_file, "r") as f:
            all_farmers = json.load(f)
    else:
        all_farmers = {}
    all_farmers.update(farmers)
    with open(farmers_file, "w") as f:
        json.dump(all_farmers, f, indent=2)
