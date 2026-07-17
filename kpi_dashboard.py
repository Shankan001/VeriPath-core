import json
import os
from datetime import datetime, timezone

DATA_DIR        = "data"
COMPANIES_FILE  = os.path.join(DATA_DIR, "companies.json")
USERS_FILE      = os.path.join(DATA_DIR, "users.json")
KPI_FILE        = os.path.join(DATA_DIR, "kpi_overrides.json")



def _load_kpi_overrides_local():
    from supabase_db import load_kpi_overrides
    return load_kpi_overrides()

def _save_kpi_overrides(data):
    from supabase_db import save_kpi_overrides
    save_kpi_overrides(
        data.get("cac_kes", 5000),
        data.get("churn_rate_pct", 0.0)
    )

def compute_kpis() -> dict:
    from supabase_db import load_companies, load_users
    companies = load_companies()
    overrides = _load_kpi_overrides_local()
    now       = datetime.now(timezone.utc)

    paying = [c for c in companies.values()
              if c.get("subscription_tier","trial") not in ("trial","expired_paid")]
    trial  = [c for c in companies.values()
              if c.get("subscription_tier","trial") == "trial"]

    # ── MRR ──────────────────────────────────────────────────
    from trial import get_module_tiers, _get_company_module
    mrr = 0
    for c in companies.values():
        tier = c.get("subscription_tier", "trial")
        if tier in ("trial", "expired_paid"):
            continue
        company_name = c.get("company_name", "")
        module = _get_company_module(company_name)
        tiers = get_module_tiers(module)
        mrr += tiers.get(tier, {}).get("price_kes", 0)

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
    from supabase_db import load_users
    users = load_users()

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
    overrides = _load_kpi_overrides_local()

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
    companies_list = list_all_companies(exporters_only=True)
    if companies_list:
        df = pd.DataFrame(companies_list)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No companies registered yet.")

    # ── Upgrade company ───────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Set Pricing</div>", unsafe_allow_html=True)

    from trial import get_module_tiers, PRICING_TIERS
    from supabase_db import get_client

    pricing_module_tab = st.radio("Module", ["Crops", "Livestock"], horizontal=True, key="pricing_module_tab")
    _pm = "crops" if pricing_module_tab == "Crops" else "livestock"
    _current_tiers = get_module_tiers(_pm)

    with st.form(f"pricing_form_{_pm}"):
        new_prices = {}
        cols = st.columns(len(_current_tiers))
        for i, (tier_name, tier_data) in enumerate(_current_tiers.items()):
            with cols[i]:
                new_prices[tier_name] = st.number_input(
                    f"{tier_name} (KES/mo)",
                    min_value=0,
                    value=int(tier_data.get("price_kes", 0)),
                    step=500,
                    key=f"price_{_pm}_{tier_name}"
                )
        if st.form_submit_button("💾 Save Pricing", use_container_width=True):
            def _slug(name):
                return name.lower().replace(" ", "_")
            for tier_name, value in new_prices.items():
                key = f"price_{_pm}_{_slug(tier_name)}_kes"
                get_client().table("platform_settings").upsert({
                    "setting_key": key,
                    "setting_value": str(value),
                    "updated_by": "admin",
                }, on_conflict="setting_key").execute()
            st.success(f"✅ {pricing_module_tab} pricing saved.")
            st.rerun()

    st.markdown("---")

    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Company Support — Documents & Profile</div>", unsafe_allow_html=True)

    from supabase_db import get_company, ensure_company, update_company_profile, get_client as _gc3

    _companies_dict = list_all_companies(exporters_only=True)
    _support_company_names = sorted([c["Company"] for c in _companies_dict]) if _companies_dict else []

    if _support_company_names:
        support_company = st.selectbox("Select company", _support_company_names, key="support_company_select")

        _rec = get_company(support_company) or ensure_company(support_company)

        with st.form("admin_company_profile_form"):
            st.markdown("**Core Compliance Fields**")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                admin_kra_pin = st.text_input("Exporter KRA PIN", value=_rec.get("exporter_kra_pin","") or "")
            with col_p2:
                admin_afa = st.text_input("AFA License Number", value=_rec.get("afa_license_number","") or "")
            if st.form_submit_button("💾 Save Core Fields", use_container_width=True):
                update_company_profile(support_company, admin_kra_pin, admin_afa)
                st.success(f"✅ Core fields saved for {support_company}.")
                st.rerun()

        st.markdown("---")
        st.markdown("**Additional Documents / Requirements**")

        try:
            existing_docs = _gc3().table("company_documents").select("*").eq(
                "company", support_company
            ).order("updated_at", desc=True).execute().data
        except Exception:
            existing_docs = []

        if existing_docs:
            import pandas as pd
            doc_df = pd.DataFrame(existing_docs)[["document_name","document_value","notes","updated_at"]]
            st.dataframe(doc_df, use_container_width=True, hide_index=True)

            del_options = {d["document_name"]: d["id"] for d in existing_docs}
            col_del1, col_del2 = st.columns([3,1])
            with col_del1:
                to_delete = st.selectbox("Remove a document", ["—"] + list(del_options.keys()), key="del_doc_select")
            with col_del2:
                if st.button("🗑️ Remove", use_container_width=True) and to_delete != "—":
                    _gc3().table("company_documents").delete().eq("id", del_options[to_delete]).execute()
                    st.success(f"Removed {to_delete}.")
                    st.rerun()
        else:
            st.info("No additional documents on file for this company yet.")

        with st.form("add_company_document_form"):
            st.markdown("Add a new document / requirement")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                new_doc_name = st.text_input("Document name", placeholder="e.g. Phytosanitary Certificate Ref")
            with col_d2:
                new_doc_value = st.text_input("Value / reference", placeholder="e.g. PHY-2026-00123")
            new_doc_notes = st.text_area("Notes (optional)", placeholder="Any context for support/compliance team")
            if st.form_submit_button("➕ Add Document", use_container_width=True):
                if not new_doc_name.strip():
                    st.error("Document name is required.")
                else:
                    _gc3().table("company_documents").insert({
                        "company": support_company,
                        "document_name": new_doc_name.strip(),
                        "document_value": new_doc_value.strip(),
                        "notes": new_doc_notes.strip(),
                        "updated_by": "admin",
                    }).execute()
                    st.success(f"✅ Added {new_doc_name} for {support_company}.")
                    st.rerun()
    else:
        st.info("No companies to manage yet.")

    st.markdown("---")

    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Live Portal Transmission</div>", unsafe_allow_html=True)

    from supabase_db import get_client as _gc2
    try:
        _live_row = _gc2().table("platform_settings").select("setting_value").eq(
            "setting_key", "live_transmission_enabled"
        ).execute().data
        _live_now = _live_row[0]["setting_value"] == "true" if _live_row else False
    except Exception:
        _live_now = False

    st.markdown(
        f"Current status: {'🟢 **ENABLED**' if _live_now else '🔒 **LOCKED**'} — "
        f"controls whether any exporter can use Live Mode on Transmit to Portals."
    )
    col_lock1, col_lock2 = st.columns(2)
    with col_lock1:
        if st.button("🔓 Enable Live Transmission", use_container_width=True, disabled=_live_now):
            _gc2().table("platform_settings").upsert({
                "setting_key": "live_transmission_enabled",
                "setting_value": "true",
                "updated_by": "admin",
            }, on_conflict="setting_key").execute()
            st.success("✅ Live transmission enabled.")
            st.rerun()
    with col_lock2:
        if st.button("🔒 Lock Live Transmission", use_container_width=True, disabled=not _live_now):
            _gc2().table("platform_settings").upsert({
                "setting_key": "live_transmission_enabled",
                "setting_value": "false",
                "updated_by": "admin",
            }, on_conflict="setting_key").execute()
            st.warning("🔒 Live transmission locked.")
            st.rerun()

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
            from trial import get_module_tiers, _get_company_module
            _module = _get_company_module(target_company)
            _tiers = get_module_tiers(_module)
            price = _tiers.get(new_tier, {}).get("price_kes", 0) * months
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
