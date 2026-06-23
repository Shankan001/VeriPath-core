with open("packhouse.py","r") as f:
    content = f.read()

old = '''            if st.button("💾 Save Edit", key=f"save_edit_{idx}"):
                if os.path.exists(ledger_path):
                    with open(ledger_path) as f:
                        all_records = json.load(f)
                    company_lower = company.strip().lower()
                    session_id    = record.get("session_id")
                    row_crop      = record.get("crop")
                    for r in all_records:
                        if (r.get("session_id") == session_id
                                and r.get("crop") == row_crop
                                and r.get("company","").strip().lower() == company_lower):
                            r["weight_kg"]  = new_weight
                            r["grade"]      = new_grade
                            r["notes"]      = new_notes
                            r["packhouse"]  = new_packhouse
                            r["last_edited"] = dt.datetime.now().isoformat()
                            break
                    save_full_ledger(all_records)
                    st.success("✅ Record updated.")
                    st.rerun()'''

new = '''            col_save, col_del = st.columns([3,1])
            with col_save:
                if st.button("💾 Save Edit", key=f"save_edit_{idx}"):
                    if os.path.exists(ledger_path):
                        with open(ledger_path) as f:
                            all_records = json.load(f)
                        company_lower = company.strip().lower()
                        session_id    = record.get("session_id")
                        row_crop      = record.get("crop")
                        for r in all_records:
                            if (r.get("session_id") == session_id
                                    and r.get("crop") == row_crop
                                    and r.get("company","").strip().lower() == company_lower):
                                r["weight_kg"]   = new_weight
                                r["grade"]       = new_grade
                                r["notes"]       = new_notes
                                r["packhouse"]   = new_packhouse
                                r["last_edited"] = dt.datetime.now().isoformat()
                                break
                        save_full_ledger(all_records)
                        st.success("✅ Record updated.")
                        st.rerun()
            with col_del:
                if st.button("🗑 Delete", key=f"del_record_{idx}",
                             type="secondary", use_container_width=True):
                    if os.path.exists(ledger_path):
                        with open(ledger_path) as f:
                            all_records = json.load(f)
                        company_lower = company.strip().lower()
                        session_id    = record.get("session_id")
                        row_crop      = record.get("crop")
                        all_records   = [
                            r for r in all_records
                            if not (r.get("session_id") == session_id
                                    and r.get("crop") == row_crop
                                    and r.get("company","").strip().lower() == company_lower)
                        ]
                        save_full_ledger(all_records)
                        st.success("🗑 Record deleted.")
                        st.rerun()'''

if old in content:
    content = content.replace(old, new)
    print("✅ Delete button added")
else:
    print("❌ Block not found")

with open("packhouse.py","w") as f:
    f.write(content)
