"""
VeriPath — Pre-Audit Quarantine Desk
Shows flagged intake records individually (separable by packhouse/county),
lets compliance officer/exporter review and fix issues directly, or
override and approve anyway. Verified/clean records are shown in a
separate summary count.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from ledger_db import load_ledger, update_ledger_record_by_id
from supabase_db import get_client


def render_quarantine_desk_page(profile: dict):
    st.markdown("# 🧪 Pre-Audit Quarantine Desk")
    st.markdown(
        "<p style='color:#64748b'>Review flagged intake records individually, "
        "fix issues, or override and approve.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    company = profile.get("company", "") if profile.get("role") != "admin" else ""
    role = profile.get("role", "")

    ledger = load_ledger(company)
    if not ledger:
        st.info("No intake records found.")
        return

    df = pd.DataFrame(ledger)

    verified_count = len(df[df.get("audit_status") == "verified"]) if "audit_status" in df.columns else 0
    flagged_count = len(df[df.get("audit_status") == "flagged"]) if "audit_status" in df.columns else 0
    unaudited_count = len(df[~df.get("audit_status", pd.Series()).isin(["verified", "flagged"])]) if "audit_status" in df.columns else len(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"<div style='background:#071a0f;border:1px solid #16a34a;border-radius:8px;padding:16px;text-align:center'>"
            f"<div style='color:#94a3b8;font-size:0.8rem'>🟢 VERIFIED</div>"
            f"<div style='font-size:2rem;font-weight:700;color:#4ade80'>{verified_count}</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='background:#1a1400;border:1px solid #d97706;border-radius:8px;padding:16px;text-align:center'>"
            f"<div style='color:#94a3b8;font-size:0.8rem'>🟠 FLAGGED</div>"
            f"<div style='font-size:2rem;font-weight:700;color:#fbbf24'>{flagged_count}</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"<div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;padding:16px;text-align:center'>"
            f"<div style='color:#94a3b8;font-size:0.8rem'>⚪ NOT YET AUDITED</div>"
            f"<div style='font-size:2rem;font-weight:700;color:#94a3b8'>{unaudited_count}</div>"
            f"</div>", unsafe_allow_html=True
        )

    st.markdown("---")

    if flagged_count == 0:
        st.success("✅ No flagged records — quarantine desk is clear.")
        return

    flagged_df = df[df["audit_status"] == "flagged"].copy()

    st.markdown("### Filter flagged records")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        packhouse_options = ["All Packhouses"] + sorted([p for p in flagged_df["packhouse"].dropna().unique() if p])
        selected_packhouse = st.selectbox("Packhouse", packhouse_options)
    with col_f2:
        county_options = ["All Counties"] + sorted([c for c in flagged_df["county"].dropna().unique() if c])
        selected_county = st.selectbox("County", county_options)

    if selected_packhouse != "All Packhouses":
        flagged_df = flagged_df[flagged_df["packhouse"] == selected_packhouse]
    if selected_county != "All Counties":
        flagged_df = flagged_df[flagged_df["county"] == selected_county]

    st.markdown(f"**{len(flagged_df)} flagged record(s)**")
    st.markdown("---")

    for _, row in flagged_df.iterrows():
        record_id = row["id"]
        with st.container():
            st.markdown(
                f"<div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:8px;padding:14px 18px;margin-bottom:6px'>"
                f"<b style='color:#f87171'>{row.get('farmer_name','—')}</b> · "
                f"{row.get('county','—')} · {row.get('weight_kg','—')} kg<br>"
                f"<span style='color:#fbbf24;font-size:0.85rem'>{row.get('audit_failure_reason','—')}</span>"
                f"</div>", unsafe_allow_html=True
            )

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                with st.expander("✏️ Review & Fix"):
                    with st.form(f"fix_form_{record_id}"):
                        new_packhouse = st.text_input("Packhouse", value=row.get("packhouse","") or "")
                        new_gps = st.text_input("GPS", value=row.get("gps","") or "")
                        new_hs_code = st.text_input("HS Code", value=row.get("hs_code","") or "")
                        submit_fix = st.form_submit_button("💾 Save & Re-check", use_container_width=True)

                    if submit_fix:
                        updates = {"packhouse": new_packhouse, "gps": new_gps, "hs_code": new_hs_code}
                        update_ledger_record_by_id(record_id, updates)

                        # Re-evaluate this single record against the same audit rules
                        from pre_audit import run_audit
                        updated_record = {**row.to_dict(), **updates}
                        recheck = run_audit([updated_record])

                        if recheck["all_clean"]:
                            update_ledger_record_by_id(record_id, {
                                "audit_status": "verified",
                                "audit_failure_reason": None,
                                "flagged_for_approval": False,
                            })
                            st.success("✅ Fixed and now verified.")
                        else:
                            remaining_issues = "; ".join(
                                recheck["eudr_flags"][0]["audit_issues"] if recheck["eudr_flags"]
                                else recheck["missing_flags"][0]["audit_issues"]
                            )
                            update_ledger_record_by_id(record_id, {"audit_failure_reason": remaining_issues})
                            st.warning(f"⚠️ Still has issues: {remaining_issues}")
                        st.rerun()

            with col_b:
                with st.expander("⚠️ Override & Approve Anyway"):
                    override_reason = st.text_area("Override reason *", key=f"override_reason_{record_id}")
                    if st.button("⚠️ Confirm Override", key=f"override_btn_{record_id}", use_container_width=True):
                        if not override_reason.strip():
                            st.error("Override reason is required.")
                        else:
                            update_ledger_record_by_id(record_id, {
                                "audit_status": "overridden",
                                "approved_for_submission": True,
                                "approved_by": profile.get("username"),
                                "approved_at": datetime.now(timezone.utc).isoformat(),
                                "audit_failure_reason": f"OVERRIDDEN: {override_reason.strip()}",
                            })
                            st.warning(f"⚠️ Overridden by {profile.get('full_name', role)}: {override_reason}")
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
                        st.warning("No phone number available for this contact.")
