import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_client

def _client():
    return get_client()

def save_milk_record(record: dict) -> bool:
    try:
        _client().table("milk_records").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save milk record: {e}")
        return False

def load_milk_records(company: str, animal_tag: str = None,
                      month: int = None, year: int = None) -> list[dict]:
    try:
        q = (_client().table("milk_records")
             .select("*")
             .eq("company", company))
        if animal_tag:
            q = q.eq("animal_tag", animal_tag)
        res = q.order("record_date", desc=True).execute()
        data = res.data or []
        if month and year:
            data = [r for r in data
                    if r.get("record_date","").startswith(f"{year}-{month:02d}")]
        return data
    except Exception:
        return []

def get_dairy_animals(company: str) -> list[dict]:
    """Only cattle and dairy goats produce milk."""
    try:
        res = (_client().table("animals")
               .select("animal_tag, species, breed, sex")
               .eq("company", company)
               .eq("status","active")
               .in_("species",["Cattle","Goat"])
               .eq("sex","Female")
               .execute())
        return res.data or []
    except Exception:
        return []

def render_milk_tracker(profile: dict):
    company  = profile.get("company","")
    username = profile.get("username","")
    role     = profile.get("role","")

    if role not in ("admin","farm_manager","diaspora_owner"):
        st.warning("🔒 Milk tracking requires farm_manager or admin role.")
        return

    st.markdown("# 🥛 Milk Production Tracker")
    st.markdown(
        "<p style='color:#64748b'>Daily yield · revenue · break-even calculator</p>",
        unsafe_allow_html=True
    )

    dairy_animals = get_dairy_animals(company)
    if not dairy_animals:
        st.info("No female cattle or goats registered yet.")
        return

    tab_entry, tab_summary = st.tabs(["🥛 Log Milk", "📊 Production Summary"])

    # ── TAB 1: Log Milk ────────────────────────────────────────────────
    with tab_entry:
        st.markdown("<div class='section-header'>DAILY MILK LOG</div>",
                    unsafe_allow_html=True)

        options = {
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in dairy_animals
        }

        # Check market price from last record
        last_records = load_milk_records(company, month=date.today().month,
                                         year=date.today().year)
        last_price = (float(last_records[0]["price_per_ltr"])
                      if last_records else 55.0)

        with st.form("milk_entry_form"):
            sel_label  = st.selectbox("Animal *", list(options.keys()))
            sel_animal = options[sel_label]

            col1, col2, col3 = st.columns(3)
            with col1:
                record_date = st.date_input("Date *", value=date.today())
            with col2:
                morning = st.number_input("Morning yield (L)",
                                          min_value=0.0, max_value=50.0,
                                          value=0.0, step=0.1, format="%.1f")
            with col3:
                evening = st.number_input("Evening yield (L)",
                                          min_value=0.0, max_value=50.0,
                                          value=0.0, step=0.1, format="%.1f")

            total_ltrs = round(morning + evening, 2)
            col4, col5 = st.columns(2)
            with col4:
                price_per_ltr = st.number_input(
                    "Price per litre (KES)",
                    min_value=0.0, value=last_price,
                    step=1.0, format="%.2f"
                )
            with col5:
                revenue = round(total_ltrs * price_per_ltr, 2)
                st.metric("Today's Revenue (KES)", f"{revenue:,.2f}")

            notes   = st.text_input("Notes", placeholder="Any observations...")
            sub_btn = st.form_submit_button(
                "🥛 Save Milk Record", use_container_width=True, type="primary"
            )

        if sub_btn:
            if total_ltrs <= 0:
                st.warning("⚠️ Total yield is 0 — please enter morning or evening yield.")
            else:
                record = {
                    "animal_tag":   sel_animal["animal_tag"],
                    "company":      company,
                    "entered_by":   username,
                    "record_date":  record_date.isoformat(),
                    "morning_ltrs": morning,
                    "evening_ltrs": evening,
                    "total_ltrs":   total_ltrs,
                    "price_per_ltr":price_per_ltr,
                    "revenue_kes":  revenue,
                    "notes":        notes.strip() or None,
                    "created_at":   datetime.now(timezone.utc).isoformat(),
                }
                if save_milk_record(record):
                    st.success(
                        f"✅ {total_ltrs}L logged for {sel_animal['animal_tag']} "
                        f"— KES {revenue:,.2f} revenue."
                    )
                    st.rerun()

    # ── TAB 2: Production Summary ──────────────────────────────────────
    with tab_summary:
        st.markdown("<div class='section-header'>PRODUCTION SUMMARY</div>",
                    unsafe_allow_html=True)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_month = st.selectbox(
                "Month", list(range(1,13)),
                index=date.today().month - 1,
                format_func=lambda m: datetime(2000,m,1).strftime("%B"),
                key="milk_month"
            )
        with col_f2:
            sel_year = st.number_input(
                "Year", min_value=2024, max_value=2030,
                value=date.today().year, key="milk_year"
            )

        records = load_milk_records(company, month=sel_month, year=sel_year)

        if not records:
            st.info(f"No milk records for {datetime(2000,sel_month,1).strftime('%B')} {sel_year}.")
            return

        df = pd.DataFrame(records)
        df["total_ltrs"]   = df["total_ltrs"].astype(float)
        df["revenue_kes"]  = df["revenue_kes"].astype(float)

        total_litres  = df["total_ltrs"].sum()
        total_revenue = df["revenue_kes"].sum()
        days_recorded = df["record_date"].nunique()
        avg_daily     = round(total_litres / days_recorded, 1) if days_recorded else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>TOTAL YIELD</div>
            <div class='metric-value' style='color:#38bdf8'>
                {total_litres:,.1f}L
            </div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>MILK REVENUE</div>
            <div class='metric-value' style='color:#4ade80'>
                KES {total_revenue:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>AVG/DAY</div>
            <div class='metric-value'>{avg_daily}L</div>
        </div>""", unsafe_allow_html=True)
        c4.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>DAYS RECORDED</div>
            <div class='metric-value'>{days_recorded}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Trend chart
        st.markdown("<div class='section-header'>DAILY YIELD TREND</div>",
                    unsafe_allow_html=True)
        df_trend = (df.groupby("record_date")["total_ltrs"]
                      .sum().reset_index()
                      .sort_values("record_date"))
        df_trend.columns = ["Date","Total Litres"]
        st.line_chart(df_trend.set_index("Date"))

        # Per animal
        st.markdown("<div class='section-header'>BY ANIMAL</div>",
                    unsafe_allow_html=True)
        animal_milk = (df.groupby("animal_tag")
                         .agg(total_ltrs=("total_ltrs","sum"),
                              total_revenue=("revenue_kes","sum"))
                         .reset_index()
                         .sort_values("total_ltrs", ascending=False))
        for _, row in animal_milk.iterrows():
            st.markdown(f"""
            <div style='background:#111827;border:1px solid #1e3a5f;
                        border-radius:10px;padding:12px 16px;margin-bottom:6px'>
                <div style='display:flex;justify-content:space-between'>
                    <span style='font-family:Space Mono,monospace;
                                 color:#38bdf8;font-weight:700'>
                        🥛 {row["animal_tag"]}
                    </span>
                    <span style='color:#4ade80;font-family:Space Mono,monospace;
                                 font-weight:700'>
                        KES {row["total_revenue"]:,.0f}
                    </span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem;margin-top:4px'>
                    {row["total_ltrs"]:,.1f} litres this month
                </div>
            </div>
            """, unsafe_allow_html=True)
