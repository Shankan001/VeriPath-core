import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

LEDGER_DB     = "ledger.json"
PRE_AUDIT_DB  = "pre_audit.json"

REQUIRED_FIELDS = ["farmer_id","farmer_name","county","crop","hs_code","weight_kg","eudr_risk","packhouse","intake_date"]
EUDR_AMBER_RED  = ["AMBER","RED"]
EUDR_NEEDS_GPS  = ["Coffee","Tea","Maize"]

def load_ledger():
    if os.path.exists(LEDGER_DB):
        with open(LEDGER_DB, "r") as f:
            return json.load(f)
    return []

def save_ledger(ledger):
    with open(LEDGER_DB, "w") as f:
        json.dump(ledger, f, indent=2)

def load_pre_audit():
    if os.path.exists(PRE_AUDIT_DB):
        with open(PRE_AUDIT_DB, "r") as f:
            return json.load(f)
    return []

def save_pre_audit(data):
    with open(PRE_AUDIT_DB, "w") as f:
        json.dump(data, f, indent=2)

def run_audit(records: list) -> dict:
    passed, eudr_flags, missing_flags = [], [], []

    for r in records:
        issues = []

        # Missing field check
        for field in REQUIRED_FIELDS:
            val = r.get(field,"")
            if not val or str(val).strip() in ("","—","Unknown","None"):
                issues.append(f"Missing: {field}")

        # GPS check for EUDR crops
        if r.get("crop","") in EUDR_NEEDS_GPS and not r.get("gps","").strip():
            issues.append(f"EUDR: GPS polygon missing for {r['crop']}")

        # EUDR risk flag
        if r.get("eudr_risk","") in EUDR_AMBER_RED:
            issues.append(f"EUDR: {r['eudr_risk']} risk — {r['crop']} requires Due Diligence Statement")

        if issues:
            flagged = {**r, "audit_issues": issues, "audit_status": "flagged"}
            if any("EUDR" in i for i in issues):
                eudr_flags.append(flagged)
            else:
                missing_flags.append(flagged)
        else:
            passed.append({**r, "audit_issues": [], "audit_status": "clean"})

    return {
        "total":         len(records),
        "passed":        len(passed),
        "eudr_flags":    eudr_flags,
        "missing_flags": missing_flags,
        "clean_records": passed,
        "all_clean":     len(eudr_flags) == 0 and len(missing_flags) == 0,
        "run_at":        datetime.now().isoformat(),
    }

def render_pre_audit_page(profile: dict):
    st.markdown("# 🔍 Pre-Audit Gate")
    st.markdown("<p style='color:#64748b'>EUDR compliance check + missing fields check — must pass before portal submission</p>", unsafe_allow_html=True)

    ledger = load_ledger()
    if not ledger:
        st.warning("No intake records to audit. Complete packhouse intake sessions first.")
        return

    df = pd.DataFrame(ledger)

    # ── Select batch to audit ──────────────────────────────────────────────
    st.markdown("### Select Batch to Audit")
    available_dates = sorted(df["intake_date"].unique(), reverse=True) if "intake_date" in df.columns else []

    if not available_dates:
        st.warning("No dated intake records found.")
        return

    col1, col2 = st.columns(2)
    with col1:
        audit_date = st.selectbox(
            "Select Date",
            options=available_dates,
            format_func=lambda d: f"{d} ({datetime.strptime(d, '%Y-%m-%d').strftime('%A')})"
        )
    with col2:
        packhouses = ["All Packhouses"] + sorted(df["packhouse"].unique().tolist())
        audit_ph   = st.selectbox("Packhouse", packhouses)

    batch_df = df[df["intake_date"] == audit_date].copy()
    if audit_ph != "All Packhouses":
        batch_df = batch_df[batch_df["packhouse"] == audit_ph]

    if batch_df.empty:
        st.info("No records for this selection.")
        return

    st.markdown(f"**{len(batch_df)} records selected for audit — {audit_date} — {audit_ph}**")
    st.markdown("---")

    # ── Run Audit ──────────────────────────────────────────────────────────
    if st.button("🔍 Run Pre-Audit Check", use_container_width=True, type="primary"):
        with st.spinner("Running compliance checks..."):
            result = run_audit(batch_df.to_dict("records"))
        st.session_state["audit_result"] = result
        st.session_state["audit_date"]   = audit_date
        st.session_state["audit_ph"]     = audit_ph

    if "audit_result" not in st.session_state:
        return

    result = st.session_state["audit_result"]

    # ── Results ────────────────────────────────────────────────────────────
    st.markdown("### Audit Results")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Records</div>
            <div class='metric-value'>{result["total"]}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class='metric-card' style='border-color:#16a34a'>
            <div class='metric-label'>✅ Clean</div>
            <div class='metric-value' style='color:#4ade80'>{result["passed"]}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        ec = len(result["eudr_flags"])
        st.markdown(f"""<div class='metric-card' style='border-color:{"#d97706" if ec>0 else "#16a34a"}'>
            <div class='metric-label'>⚠️ EUDR Flags</div>
            <div class='metric-value' style='color:{"#fbbf24" if ec>0 else "#4ade80"}'>{ec}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        mc = len(result["missing_flags"])
        st.markdown(f"""<div class='metric-card' style='border-color:{"#dc2626" if mc>0 else "#16a34a"}'>
            <div class='metric-label'>🔴 Missing Fields</div>
            <div class='metric-value' style='color:{"#f87171" if mc>0 else "#4ade80"}'>{mc}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── EUDR Flags detail ──────────────────────────────────────────────────
    if result["eudr_flags"]:
        st.markdown("#### ⚠️ EUDR Flags — Action Required")
        for r in result["eudr_flags"]:
            st.markdown(f"""
            <div style='background:#1a1400;border:1px solid #d97706;border-radius:8px;padding:12px 16px;margin-bottom:8px'>
                <b style='color:#fbbf24'>{r.get("farmer_name","—")}</b>
                &nbsp;·&nbsp; {r.get("crop","—")}
                &nbsp;·&nbsp; {r.get("county","—")}
                &nbsp;·&nbsp; {r.get("weight_kg","—")} kg<br>
                <span style='color:#f87171;font-size:0.85rem'>{"<br>".join(r.get("audit_issues",[]))}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Missing field flags ────────────────────────────────────────────────
    if result["missing_flags"]:
        st.markdown("#### 🔴 Missing Fields — Must Fix Before Submission")
        for r in result["missing_flags"]:
            st.markdown(f"""
            <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:8px;padding:12px 16px;margin-bottom:8px'>
                <b style='color:#f87171'>{r.get("farmer_name","—")}</b>
                &nbsp;·&nbsp; {r.get("crop","—")}
                &nbsp;·&nbsp; {r.get("packhouse","—")}<br>
                <span style='color:#f87171;font-size:0.85rem'>{"<br>".join(r.get("audit_issues",[]))}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Clean records ──────────────────────────────────────────────────────
    if result["clean_records"]:
        with st.expander(f"✅ {result['passed']} Clean Records"):
            clean_df = pd.DataFrame(result["clean_records"])
            cols = ["farmer_name","county","crop","weight_kg","eudr_risk","packhouse"]
            st.dataframe(clean_df[[c for c in cols if c in clean_df.columns]], use_container_width=True)

    st.markdown("---")

    # ── Submit Gate ────────────────────────────────────────────────────────
    role = profile.get("role","")

    if result["all_clean"]:
        st.markdown("""
        <div style='background:#071a0f;border:2px solid #16a34a;border-radius:12px;padding:18px 22px;margin:14px 0;text-align:center'>
            <div style='font-size:1.2rem;font-weight:700;color:#4ade80'>✅ ALL RECORDS CLEAN — READY FOR PORTAL SUBMISSION</div>
            <div style='color:#94a3b8;font-size:0.85rem;margin-top:6px'>No EUDR flags. No missing fields. Batch approved for transmission.</div>
        </div>
        """, unsafe_allow_html=True)

        if role in ("admin","exporter"):
            if st.button("🚀 Approve & Push to Government Portals", use_container_width=True, type="primary"):
                st.session_state["batch_approved"]     = True
                st.session_state["approved_records"]   = result["clean_records"]
                st.session_state["approved_date"]      = audit_date
                st.success("✅ Batch approved. Go to **Transmit to Portals** to complete submission.")
        else:
            st.info(f"Your role ({role}) can review audit results but cannot approve portal submission. An admin or exporter must approve.")
    else:
        total_flags = len(result["eudr_flags"]) + len(result["missing_flags"])
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:12px;padding:18px 22px;margin:14px 0;text-align:center'>
            <div style='font-size:1.2rem;font-weight:700;color:#f87171'>🔴 {total_flags} ISSUE(S) FOUND — SUBMISSION BLOCKED</div>
            <div style='color:#94a3b8;font-size:0.85rem;margin-top:6px'>Resolve all flagged records before this batch can be submitted to government portals.</div>
        </div>
        """, unsafe_allow_html=True)

        if role in ("admin","exporter"):
            st.markdown("#### Override (Admin Only)")
            override_reason = st.text_area("Override reason *", placeholder="Explain why you are overriding audit flags...")
            if st.button("⚠️ Override & Approve Anyway", use_container_width=True):
                if not override_reason.strip():
                    st.error("Override reason is required.")
                else:
                    all_records = result["clean_records"] + result["eudr_flags"] + result["missing_flags"]
                    st.session_state["batch_approved"]   = True
                    st.session_state["approved_records"] = all_records
                    st.session_state["override_reason"]  = override_reason
                    st.warning(f"⚠️ Override applied by {profile['full_name']}. Reason: {override_reason}")
                    st.success("Go to **Transmit to Portals** to complete submission.")
