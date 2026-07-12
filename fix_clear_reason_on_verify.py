with open("pre_audit.py", "r") as f:
    content = f.read()

old = '''        for r in result["clean_records"]:
            if r.get("id"):
                update_ledger_record_by_id(r["id"], {"audit_status": "verified"})'''

new = '''        for r in result["clean_records"]:
            if r.get("id"):
                update_ledger_record_by_id(r["id"], {
                    "audit_status": "verified",
                    "audit_failure_reason": None,
                    "flagged_for_approval": False,
                })'''

if old not in content:
    print("ERROR: target not found.")
else:
    content = content.replace(old, new)
    with open("pre_audit.py", "w") as f:
        f.write(content)
    print("Patched — clears audit_failure_reason on verify.")
