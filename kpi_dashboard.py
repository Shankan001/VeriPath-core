import json
import os
from datetime import datetime, timezone

DATA_DIR        = "data"
COMPANIES_FILE  = os.path.join(DATA_DIR, "companies.json")
USERS_FILE      = os.path.join(DATA_DIR, "users.json")
KPI_FILE        = os.path.join(DATA_DIR, "kpi_overrides.json")

TIER_PRICES_KES = {
    "Starter":       2_500,
    "Growth":       20_000,
    "Enterprise":   65_000,
    "Green Channel":150_000,
    "trial":              0,
}

def _load(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def _save_kpi_overrides(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KPI_FILE, "w") as f:
        json.dump(data, f, indent=2)

def compute_kpis() -> dict:
    companies = _load(COMPANIES_FILE)
    overrides = _load(KPI_FILE)
    now       = datetime.now(timezone.utc)

    paying = [c for c in companies.values()
              if c.get("subscription_tier","trial") not in ("trial","expired_paid")]
    trial  = [c for c in companies.values()
              if c.get("subscription_tier","trial") == "trial"]

    # ── MRR ──────────────────────────────────────────────────
    mrr = sum(TIER_PRICES_KES.get(c.get("subscription_tier","trial"), 0)
              for c in companies.values())

    # ── ARR ──────────────────────────────────────────────────
    arr = mrr * 12

    # ── Churn ────────────────────────────────────────────────
    churn_rate = overrides.get("churn_rate_pct", 0.0)

    # ── CAC ──────────────────────────────────────────────────
    cac = overrides.get("cac_kes", 5_000)

    # ── LTV ──────────────────────────────────────────────────
    avg_mrr = (mrr / len(paying)) if paying else 0
    monthly_churn = (churn_rate / 100) if churn_rate > 0 else 0.01
    ltv = round(avg_mrr / monthly_churn, 0)

    ltv_cac = round(ltv / cac, 1) if cac > 0 else 0

    # ── Tier breakdown ────────────────────────────────────────
    tier_breakdown = {}
    for c in companies.values():
        t = c.get("subscription_tier", "trial")
        tier_breakdown[t] = tier_breakdown.get(t, 0) + 1

    # ── User count ────────────────────────────────────────────
    users = _load(USERS_FILE)

    return {
        "mrr":             mrr,
        "arr":             arr,
        "total_companies": len(companies),
        "paying_companies":len(paying),
        "trial_companies": len(trial),
        "total_users":     len(users),
        "churn_rate":      churn_rate,
        "cac_kes":         cac,
        "ltv_kes":         int(ltv),
        "ltv_cac_ratio":   ltv_cac,
        "tier_breakdown":  tier_breakdown,
        "computed_at":     now.strftime("%d %b %Y %H:%M UTC"),
    }

def render_kpi_dashboard(profile: dict):
    import streamlit as st
    import pandas as pd
    from trial import set_company_subscription, list_all_companies

    if profile.get("role") != "admin":
        st.error("🔒 Access Denied. Admin only.")
        st.stop()

    st.markdown("# 📈 Business Intelligence Dashboard")
    st.markdown("<p style='color:#64748b'>Admin · Company-level subscriptions · Live data</p>",
                unsafe_allow_html=True)

    kpis = compute_kpis()
    overrides = _load(KPI_FILE)

    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Revenue Metrics</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "MRR",  f"KES {kpis['mrr']:,}",         "Monthly Recurring Revenue", "#38bdf8")
    _kpi_card(c2, "ARR",  f"KES {kpis['arr']:,}",         "Annual Recurring Revenue",  "#818cf8")
    _kpi_card(c3, "CAC",  f"KES {kpis['cac_kes']:,}",     "Cost to Acquire Customer",  "#fb923c")
    _kpi_card(c4, "LTV",  f"KES {kpis['ltv_kes']:,}",     "Customer Lifetime Value",   "#4ade80")

    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Company & Health Metrics</div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    _kpi_card(c5, "Companies",    str(kpis["total_companies"]),  "Total onboarded",        "#e2e8f0")
    _kpi_card(c6, "Paying",       str(kpis["paying_companies"]), "Active subscriptions",   "#4ade80")
    _kpi_card(c7, "Churn Rate",   f"{kpis['churn_rate']}%",      "Monthly churn",
              "#f87171" if kpis["churn_rate"] > 5 else "#4ade80")
    _kpi_card(c8, "LTV : CAC",    f"{kpis['ltv_cac_ratio']} : 1","Healthy if > 3:1",
              "#4ade80" if kpis["ltv_cac_ratio"] >= 3 else "#fbbf24")

    # ── Company table ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>All Companies</div>", unsafe_allow_html=True)
    companies_list = list_all_companies()
    if companies_list:
        df = pd.DataFrame(companies_list)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No companies registered yet.")

    # ── Upgrade company ───────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Upgrade Company Subscription</div>", unsafe_allow_html=True)

    company_names = [c["Company"] for c in companies_list] if companies_list else []
    if company_names:
        with st.form("upgrade_company_form"):
            target_company = st.selectbox("Select Company", company_names)
            new_tier       = st.selectbox("New Tier",
                                ["Starter","Growth","Enterprise","Green Channel"])
            months         = st.number_input("Months", min_value=1, max_value=12, value=1)
            col_p, col_b   = st.columns([2,1])
            price          = TIER_PRICES_KES.get(new_tier, 0) * months
            col_p.markdown(f"**Total: KES {price:,}** ({months} month{'s' if months>1 else ''})")
            if col_b.form_submit_button("⬆️ Apply Upgrade", use_container_width=True):
                ok = set_company_subscription(target_company, new_tier, months)
                if ok:
                    st.success(f"✅ {target_company} upgraded to {new_tier} for {months} month(s). "
                               f"All users at this company now have full access.")
                    st.rerun()
                else:
                    st.error("❌ Upgrade failed.")
    else:
        st.info("No companies to upgrade yet.")

    # ── Admin overrides ───────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Admin Overrides</div>", unsafe_allow_html=True)
    with st.form("overrides_form"):
        col_a, col_b = st.columns(2)
        new_cac   = col_a.number_input("CAC (KES)", min_value=0, max_value=500_000,
                                        value=overrides.get("cac_kes", 5_000), step=500)
        new_churn = col_b.number_input("Monthly Churn Rate (%)", min_value=0.0, max_value=100.0,
                                        value=float(overrides.get("churn_rate_pct", 0.0)), step=0.1)
        if st.form_submit_button("💾 Save Overrides", use_container_width=True):
            overrides["cac_kes"]        = new_cac
            overrides["churn_rate_pct"] = new_churn
            _save_kpi_overrides(overrides)
            st.success("✅ Overrides saved.")
            st.rerun()

    st.markdown(f"""
    <div style='margin-top:20px;text-align:right;color:#334155;font-size:0.7rem;
                font-family:Space Mono,monospace'>
        Last computed: {kpis["computed_at"]}
    </div>
    """, unsafe_allow_html=True)

def _kpi_card(col, label, value, sub, color):
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
