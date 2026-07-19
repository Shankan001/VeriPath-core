with open("kpi_dashboard.py", "r") as f:
    content = f.read()

anchor = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Company Support — Documents & Profile</div>", unsafe_allow_html=True)'''

phone_section = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>User Phone Numbers (Password Reset)</div>", unsafe_allow_html=True)

    from supabase_db import load_users as _load_users_phone, get_client as _gc4

    _all_users = _load_users_phone()
    _companies_for_phone = sorted(set(u.get("company","") for u in _all_users.values() if u.get("company")))

    if _companies_for_phone:
        phone_company = st.selectbox("Select company", _companies_for_phone, key="phone_backfill_company")
        _company_users = [u for u in _all_users.values() if u.get("company") == phone_company]

        if _company_users:
            import pandas as pd
            phone_df = pd.DataFrame([
                {"Username": u["username"], "Full Name": u.get("full_name",""),
                 "Role": u.get("role",""), "Phone": u.get("phone") or "⚠️ Missing"}
                for u in _company_users
            ])
            st.dataframe(phone_df, use_container_width=True, hide_index=True)

            missing_phone_users = [u["username"] for u in _company_users if not u.get("phone")]
            if missing_phone_users:
                st.markdown("**Set a phone number for a user missing one:**")
                col_ph1, col_ph2 = st.columns([2,2])
                with col_ph1:
                    target_user = st.selectbox("User", missing_phone_users, key="phone_backfill_user")
                with col_ph2:
                    new_phone_val = st.text_input("Phone number", placeholder="0712345678", key="phone_backfill_input")
                if st.button("💾 Save Phone Number", key="phone_backfill_save"):
                    from phone_utils import normalize_kenyan_phone
                    normalized = normalize_kenyan_phone(new_phone_val)
                    if not normalized:
                        st.error("Please enter a valid phone number (e.g. 07XXXXXXXX).")
                    else:
                        _gc4().table("users").update({"phone": normalized}).eq("username", target_user).execute()
                        st.success(f"✅ Phone number saved for {target_user}.")
                        st.rerun()
            else:
                st.success("✅ All users in this company have a phone number on file.")
        else:
            st.info("No users found for this company.")
    else:
        st.info("No companies found.")

    st.markdown("---")

''' + anchor

if anchor not in content:
    print("ERROR: anchor not found — no changes made.")
else:
    content = content.replace(anchor, phone_section)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("Added admin phone backfill section to KPI Dashboard.")
