"""
VeriPath Regulatory Certificate Vault — Stage 6
The Streamlit UI page: upload → extract → parse → review → save → status.
Matches the render_X_page(profile=profile) pattern used across the app,
and reuses the existing .risk-high/.risk-medium/.risk-low/.risk-exempt
CSS classes already defined in app.py for consistent visual language.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from pdf_extract import extract_text_from_pdf, truncate_for_api
from certificate_parser import parse_certificate, FIELD_SCHEMAS
from vault_checks import save_certificate_to_vault
from kra_origin_pdf import generate_kra_origin_pdf
from supabase_db import get_client

DOC_TYPE_LABELS = {
    "HCD_EXPORT_LICENCE": "HCD Export Licence",
    "KEPHIS_PHYTOSANITARY": "KEPHIS Phytosanitary Certificate",
    "KRA_CERTIFICATE_ORIGIN": "KRA Certificate of Origin",
    "GLOBALGAP_MRL": "GlobalG.A.P / MRL Test Certificate",
}

STATUS_RISK_CLASS = {
    "verified": "risk-low",
    "pending": "risk-exempt",
    "flagged": "risk-medium",
    "red_listed": "risk-high",
    "expired": "risk-medium",
}

STATUS_LABEL = {
    "verified": "✅ VERIFIED",
    "pending": "⏳ PENDING REVIEW",
    "flagged": "⚠ FLAGGED",
    "red_listed": "🔴 RED-LISTED",
    "expired": "⚠ EXPIRED",
}


def render_certificate_vault_page(profile: dict):
    st.markdown("# 🔐 Regulatory Certificate Vault")
    st.markdown(
        "<p style='color:#64748b'>Upload HCD, KEPHIS, KRA, and GlobalG.A.P documents — "
        "VeriPath extracts the data and cross-checks it automatically.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    supabase = get_client()
    company = profile.get("company", "")
    username = profile.get("username", "")

    st.markdown("<div class='section-header'>UPLOAD A CERTIFICATE</div>", unsafe_allow_html=True)

    col_type, col_file = st.columns([1, 2])
    with col_type:
        doc_type = st.selectbox(
            "Document type",
            options=list(DOC_TYPE_LABELS.keys()),
            format_func=lambda k: DOC_TYPE_LABELS[k]
        )
    with col_file:
        uploaded = st.file_uploader("PDF certificate", type=["pdf"], key="vault_upload")

    outgrower_block_id = None
    farm_lat, farm_lon = None, None
    consignment_id = None

    if doc_type == "GLOBALGAP_MRL":
        outgrower_block_id = st.text_input(
            "Outgrower block ID (required for MRL red-listing to work)",
            help="If this test fails, every certificate tied to this block ID gets flagged automatically."
        )
    if doc_type == "KRA_CERTIFICATE_ORIGIN":
        col_lat, col_lon = st.columns(2)
        with col_lat:
            farm_lat = st.number_input("Farm latitude", value=0.0, format="%.6f")
        with col_lon:
            farm_lon = st.number_input("Farm longitude", value=0.0, format="%.6f")
    if doc_type == "KEPHIS_PHYTOSANITARY":
        consignment_id = st.text_input(
            "Linked consignment ID (for weight cross-check against packhouse intake)",
            help="Leave blank to skip the weight comparison — status will show as Pending instead of Verified."
        )

    if uploaded is not None and st.button("🔍 Extract & Verify", type="primary", use_container_width=True):
        with st.spinner("Reading PDF..."):
            extraction = extract_text_from_pdf(uploaded.getvalue())

        if not extraction["success"]:
            st.error(f"❌ {extraction['error']}")
            st.stop()

        with st.spinner("Extracting structured data with Claude..."):
            text_for_api = truncate_for_api(extraction["text"])
            parse_result = parse_certificate(text_for_api, doc_type)

        if not parse_result["success"]:
            st.error(f"❌ Could not parse certificate: {parse_result['error']}")
            st.stop()

        parsed_data = parse_result["data"]

        st.markdown("<div class='section-header'>EXTRACTED DATA — REVIEW BEFORE SAVING</div>", unsafe_allow_html=True)
        st.json(parsed_data)

        save_result = save_certificate_to_vault(
            supabase=supabase,
            document_type=doc_type,
            parsed_data=parsed_data,
            raw_text=extraction["text"],
            file_name=uploaded.name,
            uploaded_by=username,
            farm_latitude=farm_lat if doc_type == "KRA_CERTIFICATE_ORIGIN" else None,
            farm_longitude=farm_lon if doc_type == "KRA_CERTIFICATE_ORIGIN" else None,
            outgrower_block_id=outgrower_block_id or None,
        )

        if not save_result["success"]:
            st.error(f"❌ {save_result['error']}")
            st.stop()

        status = save_result["status"]
        risk_class = STATUS_RISK_CLASS.get(status, "risk-exempt")
        label = STATUS_LABEL.get(status, status.upper())

        st.markdown(f"""
        <div class='risk-card {risk_class}'>
            <div style='font-family:"Space Mono",monospace;font-size:0.95rem'>{label}</div>
            <div style='color:#94a3b8;margin-top:6px;font-size:0.85rem'>
                Verification code: <b style='color:#e8eaf0'>{save_result['vp_visa_code']}</b>
            </div>
            {f"<div style='color:#fbbf24;margin-top:6px;font-size:0.85rem'>{save_result['reason']}</div>" if save_result.get('reason') else ""}
        </div>
        """, unsafe_allow_html=True)

        st.session_state["_last_vault_id"] = save_result["vault_id"]
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='section-header'>VAULT RECORDS</div>", unsafe_allow_html=True)

    try:
        records = supabase.table("export_regulatory_vault").select("*").order(
            "created_at", desc=True
        ).limit(50).execute().data
    except Exception as e:
        st.error(f"Could not load vault records: {str(e)}")
        records = []

    if not records:
        st.info("No certificates uploaded yet.")
        return

    df = pd.DataFrame(records)
    display_cols = ["vp_visa_code", "document_type", "holder_name", "document_number",
                     "verification_status", "flag_reason", "expiry_date"]
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    kra_records = [r for r in records if r.get("document_type") == "KRA_CERTIFICATE_ORIGIN"]
    if kra_records:
        st.markdown("---")
        st.markdown("<div class='section-header'>DOWNLOAD ORIGIN VERIFICATION PDF</div>", unsafe_allow_html=True)
        options = {r["vp_visa_code"]: r for r in kra_records}
        selected_code = st.selectbox("Select a certificate", options=list(options.keys()))
        if st.button("📄 Generate PDF", use_container_width=True):
            pdf_bytes, err = generate_kra_origin_pdf(options[selected_code])
            if err:
                st.error(f"❌ {err}")
            else:
                st.download_button(
                    "⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=f"{selected_code}_origin_verification.pdf",
                    mime="application/pdf",
                )
