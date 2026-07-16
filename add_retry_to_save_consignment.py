with open("supabase_db.py", "r") as f:
    content = f.read()

old = '''def save_consignment_db(record: dict) -> bool:
    try:
        record.pop("id", None)
        get_client().table("consignments").insert(record).execute()
        return True
    except Exception as e:
        print(f"[DB] save_consignment error: {e}")
        return False'''

new = '''def save_consignment_db(record: dict, max_retries: int = 3) -> bool:
    import time
    record.pop("id", None)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            get_client().table("consignments").insert(record).execute()
            return True
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # Only retry on transient network/SSL issues, not real data errors
            # (e.g. bad column, constraint violation) which would just fail again
            is_transient = any(k in error_str for k in ["ssl", "eof", "timeout", "connection"])
            if is_transient and attempt < max_retries:
                print(f"[DB] save_consignment transient error (attempt {attempt}/{max_retries}): {e} — retrying...")
                time.sleep(1.5 * attempt)  # brief backoff before retry
                continue
            print(f"[DB] save_consignment error (attempt {attempt}/{max_retries}): {e}")
            return False
    return False'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("supabase_db.py", "w") as f:
        f.write(content)
    print("Patched — save_consignment_db now retries on transient network/SSL errors.")
