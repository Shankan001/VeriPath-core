from supabase_db import (
    load_consignments_db,
    save_consignment_db,
    clear_company_consignments_db
)
from datetime import datetime, timezone

def load_consignments(company: str = None) -> list[dict]:
    return load_consignments_db(company)

def save_consignments(records: list[dict]) -> None:
    for r in records:
        save_consignment_db(r)

def add_consignment(record: dict, company: str = "") -> list[dict]:
    record["company"]    = company or record.get("company","")
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    save_consignment_db(record)
    return load_consignments_db(company)

def clear_company_consignments(company: str) -> int:
    return clear_company_consignments_db(company)

def clear_all_consignments() -> None:
    pass  # Disabled in Supabase mode — use per-company clear
