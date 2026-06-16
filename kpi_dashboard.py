import json
import os
from datetime import datetime, timedelta

DATA_DIR   = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
KPI_FILE   = os.path.join(DATA_DIR, "kpi_overrides.json")

# ── Tier prices in KES ────────────────────────────────────────
TIER_PRICES_KES = {
    "Starter":      2_500,
    "Growth":       7_500,
    "Enterprise":  18_000,
    "Green Channel":35_000,
    "trial":            0,
}

def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _load_kpi_overrides() -> dict:
    """Admin can manually set CAC/LTV if they have external data."""
    if not os.path.exists(KPI_FILE):
        return {}
    try:
        with open(KPI_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def _save_kpi_overrides(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KPI_FILE, "w") as f:
        json.dump(data, f, indent=2)

def compute_kpis() -> dict:
    """
    Compute all KPIs from live user data.
    Returns dict of KPI name → value + meta.
    """
    users     = _load_users()
    overrides = _load_kpi_overrides()
    now       = datetime.utcnow()

    paying = [u for u in users.values() if u.get("subscription_tier","trial") != "trial"]
    trial  = [u for u in users.values() if u.get("subscription_tier","trial") == "trial"]
    total  = len(users)

    # ── MRR ──────────────────────────────────────────────────
    mrr = sum(TIER_PRICES_KES.get(u.get("subscription_tier","trial"), 0) for u in users.values())

    # ── ARR ──────────────────────────────────────────────────
    arr = mrr * 12

    # ── Churn ────────────────────────────────────────────────
    # Count users who were paying last month but downgraded/left
    # We store tier_set_at — if set > 30d ago and still paying = retained
    churned = 0
    retained = 0
    thirty_days_ago = now - timedelta(days=30)
    for u in paying:
        tier_set = u.get("tier_set_at")
        if tier_set:
            set_dt = datetime.fromisoformat(tier_set)
            if set_dt < thirty_days_ago:
                retained += 1
    # Churn rate = churned / (churned + retained) × 100
    churn_denominator = churned + retained
    churn_rate = round((churned / churn_denominator * 100), 1) if churn_denominator else 0.0

    # ── CAC (Cost per Acquired Customer) ─────────────────────
    # Default: use override if admin set it, else estimate KES 500 per paid user
    cac = overrides.get("cac_kes", 500)

    # ── LTV (Lifetime Value) ──────────────────────────────────
    # LTV = (MRR per customer) / monthly_churn_rate
    avg_mrr_per_customer = (mrr / len(paying)) if paying else 0
    monthly_churn_decimal = (churn_rate / 100) if churn_rate > 0 else 0.01  # avoid /0
    ltv = round(avg_mrr_per_customer / monthly_churn_decimal, 0)

    # ── LTV:CAC ratio ─────────────────────────────────────────
    ltv_cac = round(ltv / cac, 1) if cac > 0 else 0

    # ── Tier breakdown ────────────────────────────────────────
    tier_breakdown = {}
    for u in users.values():
        t = u.get("subscription_tier", "trial")
        tier_breakdown[t] = tier_breakdown.get(t, 0) + 1

    return {
        "mrr":              mrr,
        "arr":              arr,
        "total_users":      total,
        "paying_users":     len(paying),
        "trial_users":      len(trial),
        "churn_rate":       churn_rate,
        "cac_kes":          cac,
        "ltv_kes":          int(ltv),
        "ltv_cac_ratio":    ltv_cac,
        "tier_breakdown":   tier_breakdown,
        "computed_at":      now.strftime("%d %b %Y %H:%M UTC"),
    }

def render_kpi_dashboard(profile: dict):
    """Full admin-only KPI tab. Call from app.py page router."""
    import streamlit as st

    if profile.get("role") != "admin":
        st.error("🔒 Access Denied. This tab is for Admins only.")
        st.stop()

    st.markdown("# 📈 Business Intelligence Dashboard")
    st.markdown("<p style='color:#64748b'>Admin-only · Live metrics from user database</p>",
                unsafe_allow_html=True)

    kpis = compute_kpis()

    # ── Top KPI Cards ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Revenue Metrics</div>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    _kpi_card(col1, "MRR",
              f"KES {kpis['mrr']:,}",
              "Monthly Recurring Revenue",
              "#38bdf8")
    _kpi_card(col2, "ARR",
              f"KES {kpis['arr']:,}",
              "Annual Recurring Revenue",
              "#818cf8")
    _kpi_card(col3, "CAC",
              f"KES {kpis['cac_kes']:,}",
              "Cost to Acquire Customer",
              "#fb923c")
    _kpi_card(col4, "LTV",
              f"KES {kpis['ltv_kes']:,}",
              "Customer Lifetime Value",
              "#4ade80")

    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>User & Health Metrics</div>", unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    _kpi_card(col5, "Total Users",
              str(kpis["total_users"]),
              "All registered accounts",
              "#e2e8f0")
    _kpi_card(col6, "Paying Users",
              str(kpis["paying_users"]),
              "Active subscriptions",
              "#4ade80")
    _kpi_card(col7, "Churn Rate",
              f"{kpis['churn_rate']}%",
              "Monthly customer churn",
              "#f87171" if kpis["churn_rate"] > 5 else "#4ade80")
    _kpi_card(col8, "LTV : CAC",
              f"{kpis['ltv_cac_ratio']} : 1",
              "Healthy if > 3:1",
              "#4ade80" if kpis["ltv_cac_ratio"] >= 3 else "#fbbf24")

    # ── Tier Breakdown ────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Subscription Tier Breakdown</div>", unsafe_allow_html=True)

    import pandas as pd
    breakdown = kpis["tier_breakdown"]
    if breakdown:
        tier_df = pd.DataFrame([
            {
                "Tier":    tier,
                "Users":   count,
                "MRR (KES)": TIER_PRICES_KES.get(tier, 0) * count,
            }
            for tier, count in sorted(breakdown.items(), key=lambda x: -TIER_PRICES_KES.get(x[0],0))
        ])
        tier_df["MRR (KES)"] = tier_df["MRR (KES)"].apply(lambda x: f"KES {x:,}")
        st.dataframe(tier_df, use_container_width=True, hide_index=True)
    else:
        st.info("No users yet.")

    # ── CAC Override ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Admin Overrides</div>", unsafe_allow_html=True)

    overrides = _load_kpi_overrides()
    with st.form("cac_override_form"):
        new_cac = st.number_input(
            "Set CAC (KES) — your actual cost per customer acquired",
            min_value=0, max_value=500_000,
            value=overrides.get("cac_kes", 500), step=100
        )
        if st.form_submit_button("💾 Save CAC Override", use_container_width=True):
            overrides["cac_kes"] = new_cac
            _save_kpi_overrides(overrides)
            st.success(f"✅ CAC updated to KES {new_cac:,}. LTV:CAC will recalculate.")
            st.rerun()

    # ── Subscription Management ───────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Upgrade User Subscription</div>", unsafe_allow_html=True)

    users = _load_users()
    user_list = list(users.keys())
    if user_list:
        with st.form("upgrade_form"):
            target_user = st.selectbox("Select User", user_list)
            new_tier    = st.selectbox("New Tier", ["Starter","Growth","Enterprise","Green Channel"])
            if st.form_submit_button("⬆️ Apply Upgrade", use_container_width=True):
                from trial import set_subscription_tier
                ok = set_subscription_tier(target_user, new_tier)
                if ok:
                    st.success(f"✅ {target_user} upgraded to {new_tier}.")
                    st.rerun()
                else:
                    st.error("❌ Upgrade failed.")

    st.markdown(f"""
    <div style='margin-top:20px;text-align:right;color:#334155;font-size:0.7rem;
                font-family:Space Mono,monospace'>
        Last computed: {kpis["computed_at"]}
    </div>
    """, unsafe_allow_html=True)

def _kpi_card(col, label: str, value: str, sub: str, color: str):
    import streamlit as st
    with col:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#111827 0%,#1a2540 100%);
                    border:1px solid {color}33;border-radius:12px;
                    padding:20px 16px;margin-bottom:12px;
                    border-left:3px solid {color}'>
            <div style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;
                         color:#64748b;font-family:Space Mono,monospace'>{label}</div>
            <div style='font-size:1.6rem;font-weight:700;color:{color};
                         font-family:Space Mono,monospace;margin:6px 0'>{value}</div>
            <div style='font-size:0.72rem;color:#475569'>{sub}</div>
        </div>
        """, unsafe_allow_html=True)
