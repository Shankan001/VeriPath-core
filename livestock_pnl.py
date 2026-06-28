import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase_db import get_client

def _client():
    return get_client()

def _load(table: str, company: str,
          month: int = None, year: int = None) -> list[dict]:
    try:
        q = _client().table(table).select("*").eq("company", company)
        res = q.order("id", desc=True).limit(500).execute()
        data = res.data or []
        if month and year:
            date_field = {
                "animal_costs": "cost_date",
                "milk_records":  "record_date",
                "vet_consultations": "consulted_at",
            }.get(table, "created_at")
            prefix = f"{year}-{month:02d}"
            data = [r for r in data
                    if str(r.get(date_field,"")).startswith(prefix)]
        return data
    except Exception:
        return []

def render_pnl_dashboard(profile: dict):
    company = profile.get("company","")
    role    = profile.get("role","")

    if role not in ("admin","farm_manager","diaspora_owner"):
        st.warning("🔒 P&L dashboard requires farm_manager or admin role.")
        return

    st.markdown("# 📈 Farm P&L Dashboard")
    st.markdown(
        "<p style='color:#64748b'>Revenue vs costs · profit per animal · break-even</p>",
        unsafe_allow_html=True
    )

    # Period selector
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_month = st.selectbox(
            "Month", list(range(1,13)),
            index=date.today().month - 1,
            format_func=lambda m: datetime(2000,m,1).strftime("%B")
        )
    with col_f2:
        sel_year = st.number_input(
            "Year", min_value=2024, max_value=2030,
            value=date.today().year
        )

    # Load all data sources
    costs    = _load("animal_costs",      company, sel_month, sel_year)
    milk     = _load("milk_records",       company, sel_month, sel_year)
    vet_fees = _load("vet_consultations",  company, sel_month, sel_year)

    # Load animals
    try:
        res = (_client().table("animals")
               .select("animal_tag, species, breed, sex, birth_date")
               .eq("company", company)
               .eq("status","active")
               .execute())
        animals = res.data or []
    except Exception:
        animals = []

    if not animals:
        st.info("No animals registered yet.")
        return

    # ── Aggregate ──────────────────────────────────────────────────────
    total_costs   = sum(float(c.get("amount_kes",0)) for c in costs)
    total_vet     = sum(float(v.get("fee_kes",0)) for v in vet_fees)
    total_revenue = sum(float(m.get("revenue_kes",0)) for m in milk)
    total_all_costs = total_costs + total_vet
    net_profit    = total_revenue - total_all_costs
    margin_pct    = ((net_profit / total_revenue * 100)
                     if total_revenue > 0 else 0)

    # ── KPI Strip ──────────────────────────────────────────────────────
    profit_color = "#4ade80" if net_profit >= 0 else "#f87171"
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>TOTAL REVENUE</div>
        <div class='metric-value' style='color:#4ade80'>
            KES {total_revenue:,.0f}
        </div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>TOTAL COSTS</div>
        <div class='metric-value' style='color:#f87171'>
            KES {total_all_costs:,.0f}
        </div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>NET PROFIT</div>
        <div class='metric-value' style='color:{profit_color}'>
            KES {net_profit:,.0f}
        </div>
    </div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>MARGIN</div>
        <div class='metric-value' style='color:{profit_color}'>
            {margin_pct:.1f}%
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Summary table ──────────────────────────────────────────────────
    st.markdown("<div class='section-header'>P&L SUMMARY</div>",
                unsafe_allow_html=True)
    month_name = datetime(2000, sel_month, 1).strftime("%B")
    rows = [
        ("🥛 Milk Revenue",      total_revenue,       "#4ade80"),
        ("🌾 Feed & Other Costs",total_costs,          "#f87171"),
        ("🩺 Vet Fees",          total_vet,            "#f87171"),
        ("📊 Net Profit/Loss",   net_profit,           profit_color),
    ]
    for label, amount, color in rows:
        prefix = "+" if amount >= 0 else ""
        st.markdown(f"""
        <div style='background:#111827;border:1px solid #1e3a5f;
                    border-radius:10px;padding:12px 18px;margin-bottom:6px;
                    display:flex;justify-content:space-between;align-items:center'>
            <span style='color:#e8eaf0;font-size:0.9rem'>{label}</span>
            <span style='font-family:Space Mono,monospace;
                         color:{color};font-size:1rem;font-weight:700'>
                {prefix}KES {abs(amount):,.0f}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Per animal P&L ─────────────────────────────────────────────────
    st.markdown("<div class='section-header'>P&L PER ANIMAL</div>",
                unsafe_allow_html=True)

    animal_tags = [a["animal_tag"] for a in animals]
    animal_info = {a["animal_tag"]: a for a in animals}

    # Build per-animal data
    animal_pnl = []
    for tag in animal_tags:
        a_costs   = sum(float(c["amount_kes"]) for c in costs
                        if c.get("animal_tag") == tag)
        a_vet     = sum(float(v["fee_kes"]) for v in vet_fees
                        if v.get("animal_tag") == tag)
        a_revenue = sum(float(m["revenue_kes"]) for m in milk
                        if m.get("animal_tag") == tag)
        a_total_costs = a_costs + a_vet
        a_profit  = a_revenue - a_total_costs
        a_info    = animal_info.get(tag,{})

        animal_pnl.append({
            "tag":      tag,
            "species":  a_info.get("species","—"),
            "breed":    a_info.get("breed","—"),
            "revenue":  a_revenue,
            "costs":    a_total_costs,
            "profit":   a_profit,
        })

    # Sort by profit descending
    animal_pnl.sort(key=lambda x: x["profit"], reverse=True)

    for a in animal_pnl:
        p_color = "#4ade80" if a["profit"] >= 0 else "#f87171"
        p_bg    = "#071a0f" if a["profit"] >= 0 else "#1a0a0a"
        p_label = f"+KES {a['profit']:,.0f}" if a["profit"] >= 0 else f"-KES {abs(a['profit']):,.0f}"
        st.markdown(f"""
        <div style='background:{p_bg};border:1px solid {p_color};
                    border-radius:12px;padding:14px 18px;margin-bottom:8px'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <div style='font-family:Space Mono,monospace;
                                color:#38bdf8;font-weight:700'>
                        {a["tag"]}
                    </div>
                    <div style='color:#64748b;font-size:0.78rem;margin-top:2px'>
                        {a["species"]} · {a["breed"]}
                    </div>
                    <div style='color:#94a3b8;font-size:0.78rem;margin-top:4px'>
                        Revenue: KES {a["revenue"]:,.0f} ·
                        Costs: KES {a["costs"]:,.0f}
                    </div>
                </div>
                <div style='font-family:Space Mono,monospace;
                            color:{p_color};font-size:1.1rem;font-weight:700'>
                    {p_label}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Break-even calculator ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div class='section-header'>BREAK-EVEN CALCULATOR</div>",
                unsafe_allow_html=True)

    dairy_milk = [m for m in milk]
    if dairy_milk and total_all_costs > 0:
        avg_price = (sum(float(m["price_per_ltr"]) for m in dairy_milk)
                     / len(dairy_milk))
        days_in_month  = 30
        breakeven_ltrs = total_all_costs / avg_price if avg_price > 0 else 0
        breakeven_daily = round(breakeven_ltrs / days_in_month, 1)
        actual_daily    = round(
            sum(float(m["total_ltrs"]) for m in dairy_milk) / days_in_month, 1
        )
        above_breakeven = actual_daily >= breakeven_daily

        be_color = "#4ade80" if above_breakeven else "#f87171"
        st.markdown(f"""
        <div style='background:#0f2233;border:2px solid {be_color};
                    border-radius:14px;padding:20px 24px'>
            <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px'>
                <div style='text-align:center'>
                    <div style='color:#64748b;font-size:0.72rem;
                                font-family:Space Mono,monospace'>
                        BREAK-EVEN YIELD
                    </div>
                    <div style='color:#fbbf24;font-size:1.3rem;
                                font-weight:700;font-family:Space Mono,monospace'>
                        {breakeven_daily}L/day
                    </div>
                </div>
                <div style='text-align:center'>
                    <div style='color:#64748b;font-size:0.72rem;
                                font-family:Space Mono,monospace'>
                        ACTUAL YIELD
                    </div>
                    <div style='color:{be_color};font-size:1.3rem;
                                font-weight:700;font-family:Space Mono,monospace'>
                        {actual_daily}L/day
                    </div>
                </div>
                <div style='text-align:center'>
                    <div style='color:#64748b;font-size:0.72rem;
                                font-family:Space Mono,monospace'>
                        STATUS
                    </div>
                    <div style='color:{be_color};font-size:1.1rem;
                                font-weight:700;font-family:Space Mono,monospace'>
                        {"✅ PROFITABLE" if above_breakeven else "❌ BELOW B/E"}
                    </div>
                </div>
            </div>
            <div style='color:#64748b;font-size:0.75rem;margin-top:12px;text-align:center'>
                At KES {avg_price:.2f}/L avg price ·
                Total costs KES {total_all_costs:,.0f}/month
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Log milk records and costs to see break-even calculation.")

    # ── Export ─────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("⬇ Export P&L Report CSV"):
        df_export = pd.DataFrame(animal_pnl)
        df_export.columns = ["Animal Tag","Species","Breed",
                              "Revenue (KES)","Costs (KES)","Net Profit (KES)"]
        st.download_button(
            "Download P&L CSV",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name=f"veripath_pnl_{sel_year}_{sel_month:02d}.csv",
            mime="text/csv"
        )
