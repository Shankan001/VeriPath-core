import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_client

def _client():
    return get_client()

COST_TYPES = {
    "🌾 Feed & Fodder":      "feed",
    "💊 Medication":         "medication",
    "🩺 Vet Fee":            "vet_fee",
    "👷 Labour":             "labour",
    "💧 Water":              "water",
    "🚜 Transport":          "transport",
    "📡 Hardware":           "hardware",
    "🏗 Infrastructure":     "infrastructure",
    "🌿 Supplements":        "supplements",
    "🔧 Maintenance":        "maintenance",
    "📋 Other":              "other",
}

def save_cost(record: dict) -> bool:
    try:
        _client().table("animal_costs").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save cost: {e}")
        return False

def load_costs(company: str, animal_tag: str = None,
               month: int = None, year: int = None) -> list[dict]:
    try:
        q = (_client().table("animal_costs")
             .select("*")
             .eq("company", company))
        if animal_tag:
            q = q.eq("animal_tag", animal_tag)
        res = q.order("cost_date", desc=True).execute()
        data = res.data or []
        if month and year:
            data = [r for r in data
                    if r.get("cost_date","").startswith(f"{year}-{month:02d}")]
        return data
    except Exception:
        return []

def load_cost_summary(company: str) -> dict:
    """Returns total costs per type across all animals."""
    costs = load_costs(company)
    summary = {}
    for c in costs:
        ct = c.get("cost_type","other")
        summary[ct] = summary.get(ct, 0) + float(c.get("amount_kes",0))
    return summary

def render_cost_entry(profile: dict):
    company  = profile.get("company","")
    username = profile.get("username","")
    role     = profile.get("role","")

    if role not in ("admin","farm_manager","diaspora_owner"):
        st.warning("🔒 Cost entry requires farm_manager or admin role.")
        return

    st.markdown("# 💰 Cost of Production")
    st.markdown(
        "<p style='color:#64748b'>Track feed · vet · labour · all costs per animal</p>",
        unsafe_allow_html=True
    )

    # Load animals
    try:
        res = (_client().table("animals")
               .select("animal_tag, species, breed, sex")
               .eq("company", company)
               .eq("status","active")
               .execute())
        animals = res.data or []
    except Exception:
        animals = []

    if not animals:
        st.info("No animals registered yet.")
        return

    tab_entry, tab_view = st.tabs(["➕ Log Cost", "📊 Cost Summary"])

    # ── TAB 1: Log Cost ────────────────────────────────────────────────
    with tab_entry:
        st.markdown("<div class='section-header'>LOG COST ENTRY</div>",
                    unsafe_allow_html=True)

        # Bulk or single animal
        entry_mode = st.radio(
            "Entry mode",
            ["Single animal", "Whole herd (shared cost)"],
            horizontal=True
        )

        with st.form("cost_entry_form"):
            if entry_mode == "Single animal":
                options = {
                    f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
                    for a in animals
                }
                sel_label  = st.selectbox("Animal *", list(options.keys()))
                sel_animal = options[sel_label]
                target_tags = [sel_animal["animal_tag"]]
            else:
                st.markdown(
                    f"<small style='color:#64748b'>Cost will be split equally "
                    f"across all {len(animals)} animals.</small>",
                    unsafe_allow_html=True
                )
                target_tags = [a["animal_tag"] for a in animals]

            col1, col2 = st.columns(2)
            with col1:
                cost_label = st.selectbox("Cost type *", list(COST_TYPES.keys()))
                cost_type  = COST_TYPES[cost_label]
            with col2:
                cost_date = st.date_input("Date *", value=date.today())

            col3, col4 = st.columns(2)
            with col3:
                total_amount = st.number_input(
                    "Total amount (KES) *",
                    min_value=0.0, value=0.0,
                    step=50.0, format="%.2f"
                )
            with col4:
                per_animal = (round(total_amount / len(target_tags), 2)
                              if len(target_tags) > 1 else total_amount)
                st.metric("Per animal (KES)", f"{per_animal:,.2f}")

            description = st.text_input(
                "Description",
                placeholder="e.g. Napier grass 50kg · Tylosin injection · Daily labour"
            )
            submitted = st.form_submit_button(
                "💾 Save Cost", use_container_width=True, type="primary"
            )

        if submitted:
            if total_amount <= 0:
                st.error("❌ Amount must be greater than 0.")
            else:
                saved = 0
                for tag in target_tags:
                    record = {
                        "animal_tag":  tag,
                        "company":     company,
                        "entered_by":  username,
                        "cost_date":   cost_date.isoformat(),
                        "cost_type":   cost_type,
                        "amount_kes":  per_animal,
                        "description": description.strip() or None,
                        "created_at":  datetime.now(timezone.utc).isoformat(),
                    }
                    if save_cost(record):
                        saved += 1
                if saved:
                    st.success(
                        f"✅ {cost_label} — KES {total_amount:,.2f} logged "
                        f"across {saved} animal(s)."
                    )
                    st.rerun()

    # ── TAB 2: Cost Summary ────────────────────────────────────────────
    with tab_view:
        st.markdown("<div class='section-header'>COST BREAKDOWN</div>",
                    unsafe_allow_html=True)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_month = st.selectbox(
                "Month", list(range(1,13)),
                index=date.today().month - 1,
                format_func=lambda m: datetime(2000,m,1).strftime("%B")
            )
        with col_f2:
            sel_year = st.number_input(
                "Year", min_value=2024,
                max_value=2030, value=date.today().year
            )

        costs = load_costs(company, month=sel_month, year=sel_year)

        if not costs:
            st.info(f"No costs logged for {datetime(2000,sel_month,1).strftime('%B')} {sel_year}.")
            return

        df = pd.DataFrame(costs)
        df["amount_kes"] = df["amount_kes"].astype(float)
        total_month = df["amount_kes"].sum()

        # KPI strip
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>TOTAL COSTS</div>
            <div class='metric-value' style='color:#f87171'>
                KES {total_month:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>COST ENTRIES</div>
            <div class='metric-value'>{len(df)}</div>
        </div>""", unsafe_allow_html=True)
        animals_with_costs = df["animal_tag"].nunique()
        c3.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>ANIMALS TRACKED</div>
            <div class='metric-value'>{animals_with_costs}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # By cost type
        st.markdown("<div class='section-header'>BY COST TYPE</div>",
                    unsafe_allow_html=True)
        type_summary = (df.groupby("cost_type")["amount_kes"]
                          .sum().reset_index()
                          .sort_values("amount_kes", ascending=False))
        type_summary.columns = ["Cost Type","Amount (KES)"]

        for _, row in type_summary.iterrows():
            pct = (row["Amount (KES)"] / total_month * 100) if total_month else 0
            label = next((k for k,v in COST_TYPES.items() if v == row["Cost Type"]),
                         row["Cost Type"])
            st.markdown(f"""
            <div style='background:#111827;border:1px solid #1e3a5f;
                        border-radius:10px;padding:10px 16px;margin-bottom:6px'>
                <div style='display:flex;justify-content:space-between'>
                    <span style='color:#e8eaf0;font-size:0.88rem'>{label}</span>
                    <span style='font-family:Space Mono,monospace;color:#f87171;
                                 font-weight:700'>
                        KES {row["Amount (KES)"]:,.0f}
                    </span>
                </div>
                <div style='background:#1e2d45;border-radius:4px;height:6px;margin-top:6px'>
                    <div style='background:#f87171;width:{pct:.0f}%;
                                height:6px;border-radius:4px'></div>
                </div>
                <div style='color:#64748b;font-size:0.72rem;margin-top:2px'>
                    {pct:.1f}% of total
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Per animal
        st.markdown("---")
        st.markdown("<div class='section-header'>BY ANIMAL</div>",
                    unsafe_allow_html=True)
        animal_summary = (df.groupby("animal_tag")["amount_kes"]
                            .sum().reset_index()
                            .sort_values("amount_kes", ascending=False))
        animal_summary.columns = ["Animal Tag","Total Cost (KES)"]
        st.dataframe(animal_summary, use_container_width=True, hide_index=True)

        if st.button("⬇ Export Costs CSV"):
            st.download_button(
                "Download",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"veripath_costs_{sel_year}_{sel_month:02d}.csv",
                mime="text/csv"
            )
