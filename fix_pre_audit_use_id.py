with open("pre_audit.py", "r") as f:
    content = f.read()

old_import = "from ledger_db import load_ledger, save_full_ledger, update_ledger_record"
new_import = "from ledger_db import load_ledger, save_full_ledger, update_ledger_record_by_id"
content = content.replace(old_import, new_import)

old_persist = '''        now_iso = datetime.now(timezone.utc).isoformat()
        for r in result["clean_records"]:
            update_ledger_record(
                r.get("session_id",""), r.get("crop",""), company,
                {"audit_status": "verified", "last_edited": now_iso}
            )
        for r in (result["eudr_flags"] + result["missing_flags"]):
            update_ledger_record(
                r.get("session_id",""), r.get("crop",""), company,
                {
                    "audit_status": "flagged",
                    "flagged_at": now_iso,
                    "flagged_for_approval": True,
                    "audit_failure_reason": "; ".join(r.get("audit_issues", [])),
                }
            )'''

new_persist = '''        now_iso = datetime.now(timezone.utc).isoformat()
        for r in result["clean_records"]:
            if r.get("id"):
                update_ledger_record_by_id(r["id"], {"audit_status": "verified"})
        for r in (result["eudr_flags"] + result["missing_flags"]):
            if r.get("id"):
                update_ledger_record_by_id(r["id"], {
                    "audit_status": "flagged",
                    "flagged_at": now_iso,
                    "flagged_for_approval": True,
                    "audit_failure_reason": "; ".join(r.get("audit_issues", [])),
                })'''

if old_persist not in content:
    print("ERROR: target block not found — no changes made.")
else:
    content = content.replace(old_persist, new_persist)
    with open("pre_audit.py", "w") as f:
        f.write(content)
    print("Patched pre_audit.py to update by id, safely.")
