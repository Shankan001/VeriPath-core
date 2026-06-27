with open("packhouse.py","r") as f:
    content = f.read()

# Replace save_full_ledger with individual record saves
old = '''                for row in st.session_state.intake_rows:
                    all_records.append({
                        "session_id":   session_id,
                        "batch_ref":    batch_ref or session_id,
                        "intake_date":  intake_date.isoformat(),
                        "day_of_week":  day_of_week,
                        "farmer_id":    selected_id,
                        "farmer_name":  farmer["name"],
                        "farmer_phone": farmer["phone"],
                        "county":       farmer["county"],
                        "sub_location": farmer.get("sub_location",""),
                        "gps":          farmer.get("gps",""),
                        "farm_size_ha": farmer["farm_size_ha"],
                        "crop":         row["crop"],
                        "hs_code":      row["hs_code"],
                        "weight_kg":    row["weight_kg"],
                        "grade":        row["grade"],
                        "eudr_risk":    row["eudr_risk"],
                        "notes":        row["notes"],
                        "packhouse":    packhouse_name,
                        "timestamp":    timestamp,
                        "status":       "pending_audit",
                        "audit_status": "unreviewed",
                        "company":      company,
                    })
                save_full_ledger(all_records)'''

new = '''                from supabase_db import save_ledger_record_db
                for row in st.session_state.intake_rows:
                    save_ledger_record_db({
                        "session_id":   session_id,
                        "batch_ref":    batch_ref or session_id,
                        "intake_date":  intake_date.isoformat(),
                        "day_of_week":  day_of_week,
                        "farmer_id":    selected_id,
                        "farmer_name":  farmer["name"],
                        "farmer_phone": farmer["phone"],
                        "county":       farmer["county"],
                        "sub_location": farmer.get("sub_location",""),
                        "gps":          farmer.get("gps",""),
                        "farm_size_ha": farmer["farm_size_ha"],
                        "crop":         row["crop"],
                        "hs_code":      row["hs_code"],
                        "weight_kg":    row["weight_kg"],
                        "grade":        row["grade"],
                        "eudr_risk":    row["eudr_risk"],
                        "notes":        row["notes"],
                        "packhouse":    packhouse_name,
                        "timestamp":    timestamp,
                        "status":       "pending_audit",
                        "audit_status": "unreviewed",
                        "company":      company,
                    })'''

if old in content:
    content = content.replace(old, new)
    print("✅ packhouse save patched to Supabase")
else:
    print("❌ Save block not found")

# Fix edit save
old2 = '''                    save_full_ledger(all_records)
                        st.success("✅ Record updated.")'''
new2 = '''                    from supabase_db import update_ledger_record_db
                    update_ledger_record_db(
                        session_id, row_crop, company_lower,
                        {"weight_kg": new_weight, "grade": new_grade,
                         "notes": new_notes, "packhouse": new_packhouse}
                    )
                        st.success("✅ Record updated.")'''

# Fix delete
old3 = '''                        all_records   = [
                            r for r in all_records
                            if not (r.get("session_id") == session_id
                                    and r.get("crop") == row_crop
                                    and r.get("company","").strip().lower() == company_lower)
                        ]
                        save_full_ledger(all_records)
                        st.success("🗑 Record deleted.")'''
new3 = '''                        from supabase_db import delete_ledger_record_db
                        delete_ledger_record_db(session_id, row_crop, company)
                        st.success("🗑 Record deleted.")'''

for o, n, label in [(old2, new2, "edit"), (old3, new3, "delete")]:
    if o in content:
        content = content.replace(o, n)
        print(f"✅ packhouse {label} patched")
    else:
        print(f"⚠️ {label} block not found — will fix separately")

with open("packhouse.py","w") as f:
    f.write(content)
