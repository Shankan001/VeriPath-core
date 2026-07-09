"""
VeriPath — Flash Weather Risk Dashboard
Shows active/recent weather risk alerts (extreme heat, flash flood,
unseasonal rainfall) per farm, plus SMS delivery status.
"""

import streamlit as st
import pandas as pd
from supabase_db import get_client


def severity_badge(severity: str) -> tuple:
    if severity == "warning":
        return "🔴 Warning", "#ef4444"
    else:
        return "🟡 Watch", "#eab308"


def risk_icon(risk_type: str) -> str:
    return {
        "extreme_heat": "🌡️",
        "flash_flood": "🌊",
        "unseasonal_rainfall": "🌧️",
    }.get(risk_type, "⚠️")


def render_weather_risk_dashboard_page(profile: dict):
    st.markdown("# ⛈️ Flash Weather Risk")
    st.markdown(
        "<p style='color:#64748b'>48-hour forecast-based risk alerts per farm — "
        "extreme heat, flash flood, and unseasonal rainfall.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    supabase = get_client()
    company = profile.get("company", "") if profile.get("role") != "admin" else ""

    # Get farm boundaries, scoped by company via owning farmer
    try:
        farms = supabase.table("farm_boundaries").select(
            "id, farm_name, farmer_id"
        ).execute().data
    except Exception as e:
        st.error(f"Could not load farms: {str(e)}")
        st.stop()

    if company:
        try:
            company_norm = company.strip().lower()
            farmer_rows = supabase.table("farmers").select("farmer_id, company").execute().data
            allowed_farmer_ids = {
                f["farmer_id"] for f in farmer_rows
                if f.get("company", "").strip().lower() == company_norm
            }
            farms = [f for f in farms if f.get("farmer_id") in allowed_farmer_ids]
        except Exception as e:
            st.warning(f"Could not apply company filter: {str(e)}")

    if not farms:
        st.info("No farm boundaries found for your company yet. Upload one under 'Farm Boundary Upload'.")
        st.stop()

    farm_ids = [f["id"] for f in farms]
    farm_name_lookup = {f["id"]: f["farm_name"] for f in farms}

    # Pull all weather risk events for these farms
    try:
        events = supabase.table("weather_risk_events").select(
            "farm_id, risk_type, severity, forecast_value, recommended_action, sms_sent, created_at"
        ).in_("farm_id", farm_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Could not load weather risk events: {str(e)}")
        events = []

    # Summary counters — active alerts in the last 48 hours
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    recent_events = [
        e for e in events
        if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) >= cutoff
    ]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active alerts (48h)", len(recent_events))
    with col2:
        warnings = len([e for e in recent_events if e["severity"] == "warning"])
        st.metric("Warnings", warnings)
    with col3:
        sms_sent_count = len([e for e in recent_events if e.get("sms_sent")])
        st.metric("SMS sent (48h)", sms_sent_count)

    st.markdown("---")

    if not recent_events:
        st.success("✅ No active weather risks in the last 48 hours.")
    else:
        st.markdown("**Active Alerts**")
        for e in recent_events:
            badge, color = severity_badge(e["severity"])
            icon = risk_icon(e["risk_type"])
            farm_name = farm_name_lookup.get(e["farm_id"], "Unknown farm")
            sms_status = "📩 SMS sent" if e.get("sms_sent") else "⚠️ SMS not sent"

            st.markdown(
                f"<div style='background:{color}15;border-left:4px solid {color};padding:12px;"
                f"border-radius:6px;margin-bottom:8px'>"
                f"<div style='font-weight:700'>{icon} {farm_name} — {e['risk_type'].replace('_',' ').title()} "
                f"<span style='color:{color}'>({badge})</span></div>"
                f"<div style='color:#94a3b8;font-size:13px'>{e['created_at'][:16].replace('T',' ')} · "
                f"Forecast value: {e['forecast_value']} · {sms_status}</div>"
                f"<div style='margin-top:4px'>{e['recommended_action']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("<div class='section-header'>ALERT HISTORY</div>", unsafe_allow_html=True)

    if not events:
        st.info("No weather risk events logged yet for these farms.")
    else:
        history_rows = [{
            "Farm": farm_name_lookup.get(e["farm_id"], "Unknown"),
            "Risk type": e["risk_type"].replace("_", " ").title(),
            "Severity": e["severity"].title(),
            "Forecast value": e["forecast_value"],
            "SMS sent": "Yes" if e.get("sms_sent") else "No",
            "Date": e["created_at"][:16].replace("T", " "),
        } for e in events]
        st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
