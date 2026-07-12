with open("quarantine_desk.py", "r") as f:
    content = f.read()

old = '''            col_a, col_b = st.columns(2)
            with col_a:
                with st.expander("✏️ Review & Fix"):'''

new = '''            col_a, col_b, col_c = st.columns(3)
            with col_a:
                with st.expander("✏️ Review & Fix"):'''

content = content.replace(old, new)

old_override_close = '''            with col_b:
                with st.expander("⚠️ Override & Approve Anyway"):'''

new_override_close = '''            with col_b:
                with st.expander("⚠️ Override & Approve Anyway"):'''

# col_b stays the same (override block untouched), just add col_c for WhatsApp ping after it
old_end_of_row = '''                            st.warning(f"⚠️ Overridden by {profile.get('full_name', role)}: {override_reason}")
                            st.rerun()'''

new_end_of_row = '''                            st.warning(f"⚠️ Overridden by {profile.get('full_name', role)}: {override_reason}")
                            st.rerun()

            with col_c:
                with st.expander("📱 Ping Contact"):
                    try:
                        contacts = get_client().table("company_contacts").select(
                            "id, name, phone, contact_type"
                        ).eq("company", company.strip() if company else profile.get("company","").strip()).execute().data
                    except Exception:
                        contacts = []

                    contact_options = {"Farmer (from record)": row.get("farmer_phone", "")}
                    for c in contacts:
                        label = f"{c['name']} ({c['contact_type'].replace('_',' ').title()})"
                        contact_options[label] = c["phone"]

                    selected_contact_label = st.selectbox(
                        "Send to", options=list(contact_options.keys()), key=f"contact_select_{record_id}"
                    )
                    selected_phone = contact_options[selected_contact_label]

                    default_msg = (
                        f"VeriPath Alert: Batch for {row.get('farmer_name','—')} "
                        f"({row.get('county','—')}) was flagged: {row.get('audit_failure_reason','—')}. "
                        f"Please assist in resolving this."
                    )
                    msg = st.text_area("Message", value=default_msg, key=f"wa_msg_{record_id}")

                    if selected_phone:
                        clean_phone = selected_phone.strip().replace(" ", "").replace("+", "")
                        if clean_phone.startswith("0"):
                            clean_phone = "254" + clean_phone[1:]
                        import urllib.parse
                        wa_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
                        st.markdown(
                            f"<a href='{wa_link}' target='_blank' style='display:block;text-align:center;"
                            f"background:#25D366;color:white;padding:10px;border-radius:6px;"
                            f"text-decoration:none;font-weight:600'>📱 Open WhatsApp</a>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.warning("No phone number available for this contact.")'''

content = content.replace(old_end_of_row, new_end_of_row)

with open("quarantine_desk.py", "w") as f:
    f.write(content)

print("Patched WhatsApp ping feature.")
