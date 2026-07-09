"""
VeriPath — NDVI Crop Health Dashboard
Shows each farm's latest NDVI reading (green/yellow/red), a trend chart,
and any active drought/disease stress alerts.
"""

import streamlit as st
import pandas as pd
from supabase_db import get_client


def classify_ndvi(value: float) -> tuple:
    if value is None:
        return "⚪ No data", "#94a3b8"
    if value >= 0.5:
        return "🟢 Healthy", "#22c55e"
    elif value >= 0.3:
        return "🟡 Stressed", "#eab308"
    else:
        return "🔴 Critical", "#ef4444"


def render_ndvi_dashboard_page(profile: dict):
    st.markdown("# 🌱 NDVI Crop Health")
    st.markdown(
        "<p style='color:#64748b'>Satellite-based crop greenness (NDVI) per farm, "
        "updated every ~14 days via Sentinel Hub.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    supabase = get_client()
    company = profile.get("company", "") if profile.get("role") != "admin" else ""

    # Get farm boundaries, scoped by company via owning farmer (same pattern as farm_boundary_upload.py)
    try:
        farms = supabase.table("farm_boundaries").select(
            "id, farm_name, farmer_id, area_hectares"
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

    farm_lookup = {f["farm_name"]: f for f in farms}
    selected_name = st.selectbox("Select farm", options=list(farm_lookup.keys()))
    selected_farm = farm_lookup[selected_name]
    farm_id = selected_farm["id"]

    st.markdown("---")

    # Latest reading + trend
    try:
        readings = supabase.table("ndvi_readings").select(
            "reading_date, ndvi_mean, ndvi_min, ndvi_max, cloud_cover_pct"
        ).eq("farm_boundary_id", farm_id).order("reading_date", desc=False).execute().data
    except Exception as e:
        st.error(f"Could not load NDVI readings: {str(e)}")
        readings = []

    if not readings:
        st.info(f"No NDVI readings yet for **{selected_name}**. Data populates after the tracker runs on this farm.")
    else:
        latest = readings[-1]
        label, color = classify_ndvi(latest["ndvi_mean"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"<div style='background:{color}22;border-left:4px solid {color};padding:12px;border-radius:6px'>"
                f"<div style='color:#94a3b8;font-size:12px'>LATEST NDVI</div>"
                f"<div style='font-size:28px;font-weight:700'>{latest['ndvi_mean']:.3f}</div>"
                f"<div style='color:{color};font-weight:600'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col2:
            st.metric("Reading date", latest["reading_date"])
        with col3:
            st.metric("Farm size", f"{selected_farm.get('area_hectares', 0):.2f} ha")

        st.markdown("###")
        st.markdown("**NDVI Trend**")
        df = pd.DataFrame(readings)
        df["reading_date"] = pd.to_datetime(df["reading_date"])
        st.line_chart(df.set_index("reading_date")[["ndvi_mean"]])

    st.markdown("---")
    st.markdown("**Active Stress Alerts**")

    try:
        alerts = supabase.table("ndvi_stress_alerts").select(
            "created_at, previous_ndvi, current_ndvi, percent_drop, alert_type, notified_exporter, notified_farmer"
        ).eq("farm_boundary_id", farm_id).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Could not load alerts: {str(e)}")
        alerts = []

    if not alerts:
        st.success("✅ No stress alerts for this farm.")
    else:
        for alert in alerts:
            st.warning(
                f"⚠️ **{alert['percent_drop']}% NDVI drop** on {alert['created_at'][:10]} "
                f"({alert['previous_ndvi']:.3f} → {alert['current_ndvi']:.3f})"
            )

    st.markdown("---")
    st.markdown("<div class='section-header'>ALL FARMS — LATEST STATUS</div>", unsafe_allow_html=True)

    overview_rows = []
    for f in farms:
        try:
            latest_reading = supabase.table("ndvi_readings").select(
                "ndvi_mean, reading_date"
            ).eq("farm_boundary_id", f["id"]).order("reading_date", desc=True).limit(1).execute().data
        except Exception:
            latest_reading = []

        if latest_reading:
            val = latest_reading[0]["ndvi_mean"]
            label, _ = classify_ndvi(val)
            overview_rows.append({
                "Farm": f["farm_name"],
                "NDVI": val,
                "Status": label,
                "Last reading": latest_reading[0]["reading_date"],
            })
        else:
            overview_rows.append({
                "Farm": f["farm_name"],
                "NDVI": None,
                "Status": "⚪ No data",
                "Last reading": "—",
            })

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)
