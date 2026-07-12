from supabase_db import (
    load_farmers_db, save_farmer_db,
    load_ledger_db, save_ledger_record_db,
    update_ledger_record_db, delete_ledger_record_db,
    clear_company_ledger_db, save_full_ledger_db
)

def load_farmers(company: str = None) -> dict:
    return load_farmers_db(company)

def save_farmers(farmers: dict) -> None:
    for fid, data in farmers.items():
        save_farmer_db(fid, data)

def load_ledger(company: str = None) -> list[dict]:
    return load_ledger_db(company)

def save_ledger_record(record: dict) -> None:
    save_ledger_record_db(record)

def save_full_ledger(records: list[dict]) -> None:
    pass  # Not used in Supabase mode — records saved individually

def update_ledger_record(session_id: str, crop: str,
                          company: str, updates: dict) -> bool:
    return update_ledger_record_db(session_id, crop, company, updates)

def delete_ledger_record(session_id: str, crop: str,
                          company: str) -> bool:
    return delete_ledger_record_db(session_id, crop, company)

def clear_company_ledger(company: str) -> int:
    return clear_company_ledger_db(company)

def update_ledger_record_by_id(record_id: int, updates: dict) -> bool:
    from supabase_db import update_ledger_record_by_id_db
    return update_ledger_record_by_id_db(record_id, updates)
