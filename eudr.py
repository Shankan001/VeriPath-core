import streamlit as st
import os
import pandas as pd
from datetime import datetime
from supabase_db import load_ledger_db

# ── Constants ──────────────────────────────────────────────────────────────
EUDR_REGULATED_CROPS = ["Coffee", "Tea", "Maize", "Soy", "Palm Oil", "Cattle", "Cocoa", "Wood"]

EUDR_RULES = {
    # ── Floriculture — fully exempt ────────────────────────────────────────
    "Roses":         {"risk": "GREEN", "risk_level": "Exempt", "reason": "Floriculture — not subject to EUDR deforestation rules.", "action": "No EUDR action required. Standard export docs apply."},
    "Carnations":    {"risk": "GREEN", "risk_level": "Exempt", "reason": "Floriculture — not subject to EUDR deforestation rules.", "action": "No EUDR action required. Standard export docs apply."},

    # ── Vegetables / horticulture — not listed ─────────────────────────────
    "French Beans":  {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity. Standard phytosanitary applies.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},
    "Snow Peas":     {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},
    "Spinach":       {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},
    "Kale":          {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},
    "Capsicum":      {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},
    "Tomato":        {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Ensure valid phytosanitary cert and KEPHIS inspection."},

    # ── Fruits — not listed ────────────────────────────────────────────────
    "Avocado":       {"risk": "GREEN", "risk_level": "Low", "reason": "Not currently a listed EUDR commodity under Reg 2023/1115. Low deforestation risk in Kenya context.", "action": "Maintain farm-level traceability as precaution. Review list updates post-2025."},
    "Mango":         {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity. Compliant under EUDR baseline.", "action": "Standard phytosanitary documentation required."},
    "Passion Fruit": {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Standard phytosanitary documentation required."},
    "Pineapple":     {"risk": "GREEN", "risk_level": "Low", "reason": "Not a listed EUDR commodity.", "action": "Standard phytosanitary documentation required."},

    # ── Tree crops ─────────────────────────────────────────────────────────
    "Macadamia Nuts":{"risk": "GREEN", "risk_level": "Low", "reason": "Tree crop — often increases forest cover. Not listed under EUDR.", "action": "Standard phytosanitary documentation required."},
    "Macadamia":     {"risk": "GREEN", "risk_level": "Low", "reason": "Tree crop — often increases forest cover. Not listed under EUDR.", "action": "Standard phytosanitary documentation required."},

    # ── EUDR listed commodities — AMBER ────────────────────────────────────
    "Coffee":        {"risk": "AMBER", "risk_level": "Medium", "reason": "Listed EUDR commodity (Annex I). Farm polygon + satellite no-deforestation proof required for land used after Dec 31 2020.", "action": "Upload farm GPS polygon. Prepare Due Diligence Statement. Register on EU TRACES NT."},
    "Tea":           {"risk": "AMBER", "risk_level": "Medium", "reason": "Listed EUDR commodity (Annex I). Full farm-level traceability required.", "action": "Upload farm GPS polygon. Prepare Due Diligence Statement. Register on EU TRACES NT."},
    "Maize":         {"risk": "AMBER", "risk_level": "Medium", "reason": "Listed EUDR commodity (Annex I). Traceability to farm level required for EU market.", "action": "Upload farm GPS polygon. Prepare Due Diligence Statement. Register on EU TRACES NT."},
}

RISK_SCORE_MAP = {"Exempt": 0, "Low": 1, "Medium": 2, "High": 3}

CHECKLIST = {
    "GREEN": [
        "✅ Valid phytosanitary certificate (KEPHIS)",
        "✅ KRA PIN verified",
        "✅ KEPHIS inspection passed",
        "✅ County of origin recorded in VeriPath",
        "✅ HS code confirmed",
    ],
    "AMBER": [
        "✅ Valid phytosanitary certificate (KEPHIS)",
        "✅ KRA PIN verified",
        "✅ KEPHIS inspection passed",
        "✅ County of origin recorded in VeriPath",
        "✅ HS code confirmed",
        "⚠️  Farm GPS polygon uploaded (GeoJSON or KML)",
        "⚠️  Satellite deforestation check — no clearing post Dec 31 2020",
        "⚠️  Due Diligence Statement (DDS) prepared",
        "⚠️  Operator registered on EU TRACES NT system",
    ],
    "RED": [
        "✅ Valid phytosanitary certificate (KEPHIS)",
        "✅ KRA PIN verified",
        "✅ KEPHIS inspection passed",
        "✅ County of origin recorded in VeriPath",
        "✅ HS code confirmed",
        "⚠️  Farm GPS polygon uploaded (GeoJSON or KML)",
        "⚠️  Satellite deforestation check — no clearing post Dec 31 2020",
        "⚠️  Due Diligence Statement (DDS) prepared",
        "⚠️  Operator registered on EU TRACES NT system",
        "🔴  Legal land tenure proof required",
        "🔴  Independent third-party audit required",
        "🔴  Legal counsel review before export",
    ],
}

RISK_BADGE = {
    "GREEN": "🟢 GREEN — Compliant",
    "AMBER": "🟡 AMBER — Action Required",
    "RED":   "🔴 RED — Do Not Ship Without Legal Review",
}

# ── Core functions required by app.py ─────────────────────────────────────
def get_eudr_risk(crop: str, county: str = "") -> dict:
    rule = EUDR_RULES.get(crop, {
        "risk": "GREEN", "risk_level": "Low",
        "reason": "Crop not in EUDR regulated list. Standard export documentation applies.",
        "action": "Standard phytosanitary documentation required."
    })
    risk       = rule["risk"]
    risk_level = rule["risk_level"]
    return {
        "risk":        risk,
        "risk_level":  risk_level,
        "badge":       RISK_BADGE.get(risk, "🟢 GREEN — Compliant"),
        "explanation": rule["reason"],
        "action":      rule["action"],
        "score":       RISK_SCORE_MAP.get(risk_level, 1),
    }

def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    risks, scores, actions, badges = [], [], [], []
    for _, row in df.iterrows():
        crop   = str(row.get("Crop_Type", "")).strip()
        county = str(row.get("Origin_County", "")).strip()
        r      = get_eudr_risk(crop, county)
        label  = {"Low": "🟢 Low Risk", "Medium": "🟡 Medium Risk",
                  "High": "🔴 High Risk", "Exempt": "⚪ Exempt"}.get(r["risk_level"], "🟢 Low Risk")
        risks.append(label)
        scores.append(r["score"])
        actions.append(r["action"])
        badges.append(r["badge"])
    df["EUDR_Risk"]   = risks
    df["EUDR_Score"]  = scores
    df["EUDR_Action"] = actions
    df["EUDR_Badge"]  = badges
    return df

# ── Page renderer ──────────────────────────────────────────────────────────
def render_eudr_page(profile: dict = None):
    company = profile.get("company", "") if profile else ""

    st.markdown("# 🌍 EUDR Risk Scorer")
    st.markdown("<p style='color:#64748b'>EU Deforestation Regulation 2023/1115 — per-consignment compliance risk assessment</p>", unsafe_allow_html=True)

    ledger = load_ledger_db(company) if company else []
    tab1, tab2 = st.tabs(["🔍 Score a Consignment", "📊 Ledger Risk Overview"])

    with tab1:
        st.markdown("### Quick Risk Check")
        col1, col2 = st.columns(2)
        with col1:
            crop        = st.selectbox("Crop / Product", ["— Select —"] + list(EUDR_RULES.keys()))
        with col2:
            destination = st.selectbox("Destination Market", ["European Union", "United Kingdom", "USA", "Middle East", "Other"])
        has_gps = st.checkbox("Farm GPS polygon recorded?")
        has_dds = st.checkbox("Due Diligence Statement (DDS) prepared?")

        if crop != "— Select —":
            result = get_eudr_risk(crop)
            risk   = result["risk"]

            # Escalate AMBER → RED if going to EU without GPS/DDS
            if risk == "AMBER" and destination == "European Union" and (not has_gps or not has_dds):
                risk = "RED"

            color  = {"GREEN": "#4ade80", "AMBER": "#fbbf24", "RED": "#f87171"}.get(risk, "#4ade80")
            border = {"GREEN": "#16a34a", "AMBER": "#d97706", "RED": "#dc2626"}.get(risk, "#16a34a")
            bg     = {"GREEN": "#071a0f", "AMBER": "#1a1400", "RED": "#1a0a0a"}.get(risk, "#071a0f")
            icon   = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(risk, "🟢")

            st.markdown(f"""
            <div style='background:{bg};border:2px solid {border};border-radius:12px;padding:18px 22px;margin:14px 0'>
                <div style='font-size:1.4rem;font-weight:700;font-family:Space Mono,monospace;color:{color}'>{icon} {risk} — {result["risk_level"].upper()} RISK</div>
                <div style='color:#94a3b8;font-size:0.88rem;margin-top:8px'>{EUDR_RULES.get(crop, {}).get("reason", "")}</div>
                <div style='color:#e8eaf0;font-size:0.9rem;margin-top:10px'>⚡ <b>Required action:</b> {EUDR_RULES.get(crop, {}).get("action", "")}</div>
                <div style='color:#64748b;font-size:0.8rem;margin-top:8px'>EUDR Score: {result["score"]} / 3</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### Compliance Checklist")
            for item in CHECKLIST[risk]:
                st.markdown(
                    f"<div style='padding:5px 0;font-size:0.9rem;color:#e8eaf0'>{item}</div>",
                    unsafe_allow_html=True
                )

            if destination != "European Union":
                st.info(f"ℹ️ EUDR rules apply specifically to EU market exports. For **{destination}**, standard phytosanitary and bilateral trade requirements apply.")

    with tab2:
        if not ledger:
            st.info("No packhouse ledger entries yet. Complete a packhouse intake session first.")
        else:
            df          = pd.DataFrame(ledger)
            risk_counts = df["eudr_risk"].value_counts().to_dict() if "eudr_risk" in df.columns else {}

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""<div class='metric-card' style='border-color:#16a34a'>
                    <div class='metric-label'>🟢 GREEN</div>
                    <div class='metric-value' style='color:#4ade80'>{risk_counts.get("GREEN", 0)}</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class='metric-card' style='border-color:#d97706'>
                    <div class='metric-label'>🟡 AMBER</div>
                    <div class='metric-value' style='color:#fbbf24'>{risk_counts.get("AMBER", 0)}</div>
                </div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class='metric-card' style='border-color:#dc2626'>
                    <div class='metric-label'>🔴 RED</div>
                    <div class='metric-value' style='color:#f87171'>{risk_counts.get("RED", 0)}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")
            display_cols = ["timestamp", "farmer_name", "county", "crop", "hs_code", "weight_kg", "eudr_risk", "grade", "packhouse", "status"]
            available    = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available], use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Download Packhouse Ledger CSV", data=csv,
                file_name=f"VeriPath_EUDR_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
