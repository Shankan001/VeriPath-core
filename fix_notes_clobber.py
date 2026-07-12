with open("pre_audit.py", "r") as f:
    content = f.read()

old = '''        for r in (result["eudr_flags"] + result["missing_flags"]):
            update_ledger_record(
                r.get("session_id",""), r.get("crop",""), company,
                {
                    "audit_status": "flagged",
                    "flagged_at": now_iso,
                    "flagged_for_approval": True,
                    "notes": "; ".join(r.get("audit_issues", [])),
                }
            )'''

new = '''        for r in (result["eudr_flags"] + result["missing_flags"]):
            update_ledger_record(
                r.get("session_id",""), r.get("crop",""), company,
                {
                    "audit_status": "flagged",
                    "flagged_at": now_iso,
                    "flagged_for_approval": True,
                    "audit_failure_reason": "; ".join(r.get("audit_issues", [])),
                }
            )'''

if old not in content:
    print("ERROR: target block not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("pre_audit.py", "w") as f:
        f.write(content)
    print("Patched successfully — using audit_failure_reason instead of notes.")
