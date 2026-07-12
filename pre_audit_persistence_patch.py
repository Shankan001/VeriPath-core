with open("pre_audit.py", "r") as f:
    content = f.read()

# Add persistence import
old_import = "from ledger_db import load_ledger, save_full_ledger"
new_import = "from ledger_db import load_ledger, save_full_ledger, update_ledger_record\nfrom datetime import datetime, timezone"

content = content.replace(old_import, new_import)

# After running the audit, persist audit_status to each record in the database
old_run_button = '''    if st.button("🔍 Run Pre-Audit Check", use_container_width=True, type="primary"):
        result = run_audit(batch_df.to_dict("records"))
        st.session_state["audit_result"] = result
        # Clear any previous submission flag when re-running audit
        st.session_state.pop("submission_flagged", None)'''

new_run_button = '''    if st.button("🔍 Run Pre-Audit Check", use_container_width=True, type="primary"):
        result = run_audit(batch_df.to_dict("records"))
        st.session_state["audit_result"] = result
        st.session_state.pop("submission_flagged", None)

        # Persist audit_status to the database so it survives refresh and
        # is visible on the Quarantine Desk without re-running the audit.
        now_iso = datetime.now(timezone.utc).isoformat()
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
                    "notes": "; ".join(r.get("audit_issues", [])),
                }
            )'''

content = content.replace(old_run_button, new_run_button)

with open("pre_audit.py", "w") as f:
    f.write(content)

print("Patched pre_audit.py with persistence.")
