import json
import os
from datetime import datetime, timezone

DATA_DIR = "data"
DB_FILE  = os.path.join(DATA_DIR, "consignments.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_consignments(company: str = None) -> list[dict]:
    _ensure_dir()
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            records = json.load(f)
        if company:
            company = company.strip().lower()
            records = [r for r in records
                       if r.get("company","").strip().lower() == company]
        return records
    except (json.JSONDecodeError, IOError):
        return []

def save_consignments(records: list[dict]) -> None:
    _ensure_dir()
    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=2, default=str)

def add_consignment(record: dict, company: str = "") -> list[dict]:
    all_records = load_consignments()
    record["id"]         = f"VP-{len(all_records) + 1:04d}"
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    record["company"]    = company.strip() if company else record.get("company","")
    all_records.append(record)
    save_consignments(all_records)
    return all_records

def delete_consignment(record_id: str) -> list[dict]:
    records = load_consignments()
    records = [r for r in records if r.get("id") != record_id]
    save_consignments(records)
    return records

def clear_company_consignments(company: str) -> int:
    """Wipe all consignments for one company only. Returns count deleted."""
    all_records = load_consignments()
    company_lower = company.strip().lower()
    kept    = [r for r in all_records
               if r.get("company","").strip().lower() != company_lower]
    deleted = len(all_records) - len(kept)
    save_consignments(kept)
    return deleted

def clear_all_consignments() -> None:
    save_consignments([])
