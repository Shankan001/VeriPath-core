import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase_db import get_supabase_client

def _client():
    return get_supabase_client()

def _load(table: str, company: str, limit: int = 500) -> list[dict]:
    try:
        q = _client().table(table).select("*")
        if company:
            q = q.eq("company", company)
        res = q.order("id", desc=True).limit(limit).execute()
        return res.data or []
    except Exception:
        return []

def _metric(col, label: str, value, color: str = "#38bdf8"):
    col.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value' style='color:{color}'>{value}</div>
    </div>""", unsafe_allow_html=True)

def render_admin_overview(profile: dict):
    role    = profile.get("role","")
    company = profile.get("company","") if role != "admin" else ""

    if role != "admin":
        st.warning("🔒 Admin only.")
        return

    st.markdown("# 📊 Admin Overview")
    st.markdown(
        "<p style='color:#64748b'>Both modules — Crops + Livestock KPIs</p>",
        unsafe_allow_html=True
    )

    tab_live, tab_crops, tab_users = st.tabs([
        "🐄 Livestock KPIs", "🌿 Crops KPIs", "👥 Users & Activity"
    ])

    # ── TAB 1: Livestock ───────────────────────────────────────────────────
    with tab_live:
        st.markdown("<div class='section-header'>LIVESTOCK MODULE</div>",
                    unsafe_allow_html=True)

        animals   = _load("animals", company)
        temps     = _load("animal_temps", company)
        sym_logs  = _load("symptom_logs", company)
        alerts    = _load("alert_log", company)
        consults  = _load("vet_consultations", company)
        hardware  = _load("hardware_registry", company)

        red_count = sum(1 for a in animals if a.get("health_status") == "RED")
        yel_count = sum(1 for a in animals if a.get("health_status") == "YELLOW")
        grn_count = sum(1 for a in animals if a.get("health_status") == "GREEN")

        c1,c2,c3,c4 = st.columns(4)
        _metric(c1, "TOTAL ANIMALS",   len(animals))
        _metric(c2, "🚨 RED ALERTS",   red_count,  "#dc2626")
        _metric(c3, "⚠️ YELLOW WATCH", yel_count,  "#d97706")
        _metric(c4, "✅ HEALTHY",       grn_count,  "#16a34a")

        st.markdown("---")
        c5,c6,c7,c8 = st.columns(4)
        _metric(c5, "TEMP READINGS",    len(temps))
        _metric(c6, "SYMPTOM LOGS",     len(sym_logs))
        _metric(c7, "ALERTS FIRED",     len(alerts))
        _metric(c8, "VET CONSULTS",     len(consults))

        st.markdown("---")
        c9,c10,c11,c12 = st.columns(4)
        collars  = sum(1 for h in hardware if h.get("hardware_type") == "VP-COL")
        boluses  = sum(1 for h in hardware if h.get("hardware_type") == "VP-BOL")
        assigned = sum(1 for h in hardware if h.get("status") == "assigned")
        total_consult_kes = sum(
            float(c.get("vet_payout_kes",0)) for c in consults
        )
        _metric(c9,  "📡 COLLARS",      collars,  "#38bdf8")
        _metric(c10, "💊 BOLUSES",      boluses,  "#a78bfa")
        _metric(c11, "ASSIGNED UNITS",  assigned, "#4ade80")
        _metric(c12, "VET PAYOUTS",
                f"KES {total_consult_kes:,.0f}", "#fbbf24")

        if animals:
            st.markdown("---")
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(
                    "<div class='section-header'>ANIMALS BY SPECIES</div>",
                    unsafe_allow_html=True
                )
                df_sp = pd.DataFrame(animals)
                if "species" in df_sp.columns:
                    sp_counts = df_sp["species"].value_counts().reset_index()
                    sp_counts.columns = ["Species","Count"]
                    st.bar_chart(sp_counts.set_index("Species"))

            with col_r:
                st.markdown(
                    "<div class='section-header'>HEALTH STATUS BREAKDOWN</div>",
                    unsafe_allow_html=True
                )
                status_data = pd.DataFrame({
                    "Status": ["GREEN","YELLOW","RED"],
                    "Count":  [grn_count, yel_count, red_count]
                })
                st.bar_chart(status_data.set_index("Status"))

        if alerts:
            st.markdown("---")
            st.markdown(
                "<div class='section-header'>RECENT ALERTS</div>",
                unsafe_allow_html=True
            )
            df_alerts = pd.DataFrame(alerts)[[
                "animal_tag","triggered_at","triggered_by",
                "temp_celsius","alert_type"
            ]].head(10)
            df_alerts["triggered_at"] = pd.to_datetime(
                df_alerts["triggered_at"]
            ).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(df_alerts, use_container_width=True, hide_index=True)

    # ── TAB 2: Crops ───────────────────────────────────────────────────────
    with tab_crops:
        st.markdown("<div class='section-header'>CROPS MODULE</div>",
                    unsafe_allow_html=True)
        try:
            from ledger_db import load_ledger as _ll
            ledger = _ll("")
            df_l   = pd.DataFrame(ledger) if ledger else pd.DataFrame()
        except Exception:
            df_l = pd.DataFrame()

        try:
            from supabase_db import load_ledger_db
            df_l2 = pd.DataFrame(load_ledger_db(""))
            if not df_l2.empty:
                df_l = df_l2
        except Exception:
            pass

        ca,cb,cc,cd = st.columns(4)
        total_consign = len(df_l)
        total_weight  = (df_l["weight_kg"].astype(float).sum()
                         if not df_l.empty and "weight_kg" in df_l.columns else 0)
        total_fob     = (df_l["FOB_Value_USD"].astype(float).sum()
                         if not df_l.empty and "FOB_Value_USD" in df_l.columns else 0)
        valid_pins    = (df_l[df_l["PIN_Valid"]=="✅ Valid"].shape[0]
                         if not df_l.empty and "PIN_Valid" in df_l.columns else 0)

        _metric(ca, "CONSIGNMENTS",   total_consign)
        _metric(cb, "WEIGHT (KG)",    f"{total_weight:,.0f}")
        _metric(cc, "FOB VALUE",      f"${total_fob:,.2f}", "#4ade80")
        _metric(cd, "VERIFIED PINs",  valid_pins, "#fbbf24")

        if not df_l.empty:
            st.markdown("---")
            col_la, col_lb = st.columns(2)
            with col_la:
                st.markdown(
                    "<div class='section-header'>BY CROP</div>",
                    unsafe_allow_html=True
                )
                crop_col = ("crop" if "crop" in df_l.columns
                            else "Crop_Type" if "Crop_Type" in df_l.columns
                            else None)
                if crop_col:
                    cc_data = df_l[crop_col].value_counts().reset_index()
                    cc_data.columns = ["Crop","Count"]
                    st.bar_chart(cc_data.set_index("Crop"))
            with col_lb:
                st.markdown(
                    "<div class='section-header'>BY COUNTY</div>",
                    unsafe_allow_html=True
                )
                county_col = ("county" if "county" in df_l.columns
                              else "Origin_County" if "Origin_County" in df_l.columns
                              else None)
                if county_col and "weight_kg" in df_l.columns:
                    cf_data = (df_l.groupby(county_col)["weight_kg"]
                               .sum().reset_index())
                    cf_data.columns = ["County","Weight_KG"]
                    st.bar_chart(cf_data.set_index("County"))
        else:
            st.info("No crops ledger data yet.")

    # ── TAB 3: Users ───────────────────────────────────────────────────────
    with tab_users:
        st.markdown("<div class='section-header'>USER ACTIVITY</div>",
                    unsafe_allow_html=True)
        try:
            from auth import get_user_count
            from supabase_db import load_users
            users = load_users()
        except Exception:
            users = []

        if not users:
            st.info("No users found.")
            return

        df_u = pd.DataFrame(users)

        cu1,cu2,cu3,cu4 = st.columns(4)
        _metric(cu1, "TOTAL USERS", len(df_u))

        crops_users = (df_u[df_u["module"] == "🌿 VeriPath Crops"].shape[0]
                       if "module" in df_u.columns else 0)
        live_users  = (df_u[df_u["module"] == "🐄 VeriPath Livestock"].shape[0]
                       if "module" in df_u.columns else 0)
        trial_users = (df_u[df_u["subscription_tier"] == "trial"].shape[0]
                       if "subscription_tier" in df_u.columns else 0)

        _metric(cu2, "🌿 CROPS USERS",     crops_users, "#16a34a")
        _metric(cu3, "🐄 LIVESTOCK USERS", live_users,  "#d97706")
        _metric(cu4, "⏳ ON TRIAL",        trial_users, "#64748b")

        st.markdown("---")
        show_cols = [c for c in [
            "username","full_name","company","role",
            "module","subscription_tier","created_at","last_login"
        ] if c in df_u.columns]
        st.dataframe(df_u[show_cols], use_container_width=True, hide_index=True)

        if st.button("⬇ Export Users CSV"):
            st.download_button(
                "Download CSV",
                data=df_u[show_cols].to_csv(index=False).encode("utf-8"),
                file_name=f"veripath_users_{date.today()}.csv",
                mime="text/csv"
            )
