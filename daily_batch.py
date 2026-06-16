import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date
from io import BytesIO

LEDGER_DB = "ledger.json"

def load_ledger():
    if os.path.exists(LEDGER_DB):
        with open(LEDGER_DB, "r") as f:
            return json.load(f)
    return []

def render_daily_batch_page():
    st.markdown("# 📅 Daily Batch Reports")
    st.markdown("<p style='color:#64748b'>View and download all packhouse intake records grouped by day</p>", unsafe_allow_html=True)

    ledger = load_ledger()
    if not ledger:
        st.warning("No intake records yet. Complete packhouse intake sessions first.")
        return

    df = pd.DataFrame(ledger)

    # ── Date picker ────────────────────────────────────────────────────────
    available_dates = sorted(df["intake_date"].unique(), reverse=True)
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.selectbox(
            "Select Date",
            options=available_dates,
            format_func=lambda d: f"{d} ({datetime.strptime(d, '%Y-%m-%d').strftime('%A')})"
        )
    with col2:
        packhouses = ["All Packhouses"] + sorted(df["packhouse"].unique().tolist())
        selected_ph = st.selectbox("Filter by Packhouse", packhouses)

    # ── Filter ─────────────────────────────────────────────────────────────
    day_df = df[df["intake_date"] == selected_date].copy()
    if selected_ph != "All Packhouses":
        day_df = day_df[day_df["packhouse"] == selected_ph]

    if day_df.empty:
        st.info("No records for this date/packhouse combination.")
        return

    day_name = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%A %d %B %Y")
    st.markdown(f"### 📋 {day_name}")

    # ── Summary metrics ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Records</div>
            <div class='metric-value'>{len(day_df)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Weight (KG)</div>
            <div class='metric-value'>{day_df['weight_kg'].sum():,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Unique Farmers</div>
            <div class='metric-value'>{day_df['farmer_id'].nunique()}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        amber_red = day_df[day_df["eudr_risk"].isin(["AMBER","RED"])].shape[0]
        color = "#fbbf24" if amber_red > 0 else "#4ade80"
        st.markdown(f"""<div class='metric-card' style='border-color:{color}'>
            <div class='metric-label'>EUDR Flags</div>
            <div class='metric-value' style='color:{color}'>{amber_red}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Table ──────────────────────────────────────────────────────────────
    display_cols = ["session_id","farmer_name","county","packhouse","crop",
                    "hs_code","weight_kg","grade","eudr_risk","audit_status","notes"]
    available = [c for c in display_cols if c in day_df.columns]
    st.dataframe(day_df[available], use_container_width=True)

    st.markdown("---")

    # ── Downloads ──────────────────────────────────────────────────────────
    st.markdown("### ⬇️ Download Batch Report")
    col1, col2 = st.columns(2)

    with col1:
        csv = day_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name=f"VeriPath_Batch_{selected_date}_{selected_ph.replace(' ','_')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Summary sheet
                summary = pd.DataFrame([{
                    "Date":            selected_date,
                    "Day":             day_name,
                    "Packhouse":       selected_ph,
                    "Total Records":   len(day_df),
                    "Total Weight KG": day_df["weight_kg"].sum(),
                    "Unique Farmers":  day_df["farmer_id"].nunique(),
                    "EUDR Flags":      amber_red,
                    "Generated At":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                }])
                summary.to_excel(writer, sheet_name="Summary", index=False)

                # Detail sheet
                day_df[available].to_excel(writer, sheet_name="Batch Detail", index=False)

                # Per-crop breakdown
                crop_summary = day_df.groupby("crop").agg(
                    Records=("farmer_id","count"),
                    Total_KG=("weight_kg","sum"),
                    Farmers=("farmer_id","nunique")
                ).reset_index()
                crop_summary.to_excel(writer, sheet_name="By Crop", index=False)

            output.seek(0)
            st.download_button(
                "⬇️ Download Excel (3 sheets)",
                data=output,
                file_name=f"VeriPath_Batch_{selected_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            st.warning("Run: pip install openpyxl")
