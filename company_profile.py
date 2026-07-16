"""
VeriPath — Company Profile
Exporter-editable company-level compliance fields (KRA PIN, AFA license)
used to populate KenTrade/KEPHIS/AFA export documents. Exporters edit their
own company; admins can view/edit any company.
"""

import streamlit as st
from supabase_db import get_company, ensure_company, update_company_profile, load_companies


def render_company_profile_page(profile: dict):
    st.markdown("# 🏢 Company Profile")
    st.markdown(
        "<p style='color:#64748b'>Your company's export credentials — used to "
        "auto-fill KenTrade/KEPHIS/AFA submission documents.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    role = profile.get("role", "")
    own_company = profile.get("company", "")

    if role == "admin":
        companies_dict = load_companies()
        company_names = sorted([c.get("company_name", k) for k, c in companies_dict.items()])
        if not company_names:
            st.info("No companies found.")
            return
        target_company = st.selectbox("Select company", company_names)
    else:
        target_company = own_company
        st.markdown(f"**Company:** {target_company}")

    company_record = get_company(target_company) or ensure_company(target_company)

    with st.form("company_profile_form"):
        exporter_kra_pin = st.text_input(
            "Exporter KRA PIN",
            value=company_record.get("exporter_kra_pin", "") or "",
            placeholder="P051XXXXXXX",
            help="Alphanumeric KRA PIN for your company (not the farmer's PIN)."
        )
        afa_license_number = st.text_input(
            "AFA License Number",
            value=company_record.get("afa_license_number", "") or "",
            placeholder="Your active AFA registration string"
        )
        submit = st.form_submit_button("💾 Save Company Profile", use_container_width=True)

    if submit:
        ok = update_company_profile(target_company, exporter_kra_pin, afa_license_number)
        if ok:
            st.success(f"✅ Company profile saved for {target_company}.")
            st.rerun()
        else:
            st.error("❌ Failed to save company profile.")
