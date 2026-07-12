with open("supabase_db.py", "r") as f:
    content = f.read()

old = '''def update_ledger_record_db(session_id: str, crop: str,
                              company: str, updates: dict) -> bool:'''

# Add a new, safe by-id update function right before the existing one
new = '''def update_ledger_record_by_id_db(record_id: int, updates: dict) -> bool:
    """
    Updates a single ledger row by its real primary key (id) — safe for
    tables where session_id + crop is shared across multiple farmer rows
    in the same intake batch (unlike update_ledger_record_db, which matches
    on session_id+crop+company and can silently affect multiple rows).
    """
    try:
        updates["last_edited"] = _now()
        get_client().table("ledger").update(updates).eq("id", record_id).execute()
        return True
    except Exception as e:
        print(f"[DB] update_ledger_record_by_id error: {e}")
        return False


def update_ledger_record_db(session_id: str, crop: str,
                              company: str, updates: dict) -> bool:'''

content = content.replace(old, new)

with open("supabase_db.py", "w") as f:
    f.write(content)

print("Added safe by-id update function.")
