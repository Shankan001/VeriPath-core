with open("kpi_dashboard.py", "r") as f:
    content = f.read()

anchor = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Live Portal Transmission</div>", unsafe_allow_html=True)'''

documents_section = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Company Support — Documents & Profile</div>", unsafe_allow_html=True)

    from supabase_db import get_company, ensure_company, update_company_profile, get_client as _gc3

    _companies_dict = list_all_companies(exporters_only=True)
    _support_company_names = sorted([c["Company"] for c in _companies_dict]) if _companies_dict else []

    if _support_company_names:
        support_company = st.selectbox("Select company", _support_company_names, key="support_company_select")

        _rec = get_company(support_company) or ensure_company(support_company)

        with st.form("admin_company_profile_form"):
            st.markdown("**Core Compliance Fields**")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                admin_kra_pin = st.text_input("Exporter KRA PIN", value=_rec.get("exporter_kra_pin","") or "")
            with col_p2:
                admin_afa = st.text_input("AFA License Number", value=_rec.get("afa_license_number","") or "")
            if st.form_submit_button("💾 Save Core Fields", use_container_width=True):
                update_company_profile(support_company, admin_kra_pin, admin_afa)
                st.success(f"✅ Core fields saved for {support_company}.")
                st.rerun()

        st.markdown("---")
        st.markdown("**Additional Documents / Requirements**")

        try:
            existing_docs = _gc3().table("company_documents").select("*").eq(
                "company", support_company
            ).order("updated_at", desc=True).execute().data
        except Exception:
            existing_docs = []

        if existing_docs:
            import pandas as pd
            doc_df = pd.DataFrame(existing_docs)[["document_name","document_value","notes","updated_at"]]
            st.dataframe(doc_df, use_container_width=True, hide_index=True)

            del_options = {d["document_name"]: d["id"] for d in existing_docs}
            col_del1, col_del2 = st.columns([3,1])
            with col_del1:
                to_delete = st.selectbox("Remove a document", ["—"] + list(del_options.keys()), key="del_doc_select")
            with col_del2:
                if st.button("🗑️ Remove", use_container_width=True) and to_delete != "—":
                    _gc3().table("company_documents").delete().eq("id", del_options[to_delete]).execute()
                    st.success(f"Removed {to_delete}.")
                    st.rerun()
        else:
            st.info("No additional documents on file for this company yet.")

        with st.form("add_company_document_form"):
            st.markdown("Add a new document / requirement")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                new_doc_name = st.text_input("Document name", placeholder="e.g. Phytosanitary Certificate Ref")
            with col_d2:
                new_doc_value = st.text_input("Value / reference", placeholder="e.g. PHY-2026-00123")
            new_doc_notes = st.text_area("Notes (optional)", placeholder="Any context for support/compliance team")
            if st.form_submit_button("➕ Add Document", use_container_width=True):
                if not new_doc_name.strip():
                    st.error("Document name is required.")
                else:
                    _gc3().table("company_documents").insert({
                        "company": support_company,
                        "document_name": new_doc_name.strip(),
                        "document_value": new_doc_value.strip(),
                        "notes": new_doc_notes.strip(),
                        "updated_by": "admin",
                    }).execute()
                    st.success(f"✅ Added {new_doc_name} for {support_company}.")
                    st.rerun()
    else:
        st.info("No companies to manage yet.")

    st.markdown("---")

''' + anchor

if anchor not in content:
    print("ERROR: anchor not found — no changes made.")
else:
    content = content.replace(anchor, documents_section)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("Added Company Support (documents & profile) section to KPI Dashboard.")
