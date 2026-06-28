import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from supabase_db import get_supabase_client

def _client():
    return get_supabase_client()

def load_alerts(company: str) -> list[dict]:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("company", company)
               .eq("health_status", "RED")
               .execute())
        return res.data or []
    except Exception:
        return []

def load_animal_full(animal_tag: str) -> dict:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("animal_tag", animal_tag)
               .limit(1)
               .execute())
        return res.data[0] if res.data else {}
    except Exception:
        return {}

def load_temp_history(animal_tag: str) -> list[dict]:
    try:
        res = (_client().table("animal_temps")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("recorded_at", desc=True)
               .limit(14)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_symptom_history(animal_tag: str) -> list[dict]:
    try:
        res = (_client().table("symptom_logs")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("logged_at", desc=True)
               .limit(14)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_assessments(animal_tag: str) -> list[dict]:
    try:
        res = (_client().table("disease_assessments")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("assessed_at", desc=True)
               .limit(10)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_all_animals(company: str) -> list[dict]:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("company", company)
               .eq("status", "active")
               .order("health_status", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

def _status_color(status: str) -> tuple[str, str]:
    return {
        "RED":    ("#dc2626", "#1a0a0a"),
        "YELLOW": ("#d97706", "#1a0f00"),
        "GREEN":  ("#16a34a", "#071a0f"),
        "BLUE":   ("#38bdf8", "#0f2233"),
    }.get(status, ("#64748b", "#0d1224"))

def _alert_card(a: dict) -> str:
    color, bg = _status_color(a.get("health_status","GREEN"))
    age = a.get("age_months","?")
    return f"""
    <div style='background:{bg};border:2px solid {color};
                border-radius:14px;padding:18px 20px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center'>
            <div>
                <div style='font-family:Space Mono,monospace;color:{color};
                            font-size:1rem;font-weight:700'>
                    🚨 {a.get("animal_tag","—")}
                </div>
                <div style='color:#e8eaf0;margin-top:4px;font-size:0.88rem'>
                    {a.get("species","—")} · {a.get("breed","—")} · {a.get("sex","—")}
                </div>
                <div style='color:#64748b;font-size:0.78rem;margin-top:2px'>
                    {age} months · {a.get("county","—")} · {a.get("farm_location","—")}
                </div>
            </div>
            <div style='text-align:right'>
                <div style='font-family:Space Mono,monospace;color:{color};
                            font-size:0.85rem;font-weight:700'>
                    {a.get("health_status","—")}
                </div>
                <div style='color:#64748b;font-size:0.72rem;margin-top:4px'>
                    {a.get("owner_username","—")}
                </div>
            </div>
        </div>
    </div>
    """

def render_vet_dashboard(profile: dict):
    company  = profile.get("company", "")
    username = profile.get("username", "")
    role     = profile.get("role", "")

    if role not in ("veterinarian", "admin", "farm_manager"):
        st.warning("🔒 Vet dashboard requires veterinarian or admin role.")
        return

    st.markdown("# 🩺 Vet Dashboard")
    st.markdown(
        "<p style='color:#64748b'>Clinical alerts · patient history · disease scoring</p>",
        unsafe_allow_html=True
    )

    all_animals = load_all_animals(company)
    red_animals = [a for a in all_animals if a.get("health_status") == "RED"]
    yel_animals = [a for a in all_animals if a.get("health_status") == "YELLOW"]

    # ── KPI row ────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>TOTAL ANIMALS</div>
        <div class='metric-value'>{len(all_animals)}</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>🚨 RED ALERTS</div>
        <div class='metric-value' style='color:#dc2626'>{len(red_animals)}</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>⚠️ YELLOW WATCH</div>
        <div class='metric-value' style='color:#d97706'>{len(yel_animals)}</div>
    </div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>✅ HEALTHY</div>
        <div class='metric-value' style='color:#16a34a'>
            {len(all_animals) - len(red_animals) - len(yel_animals)}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    tab_alerts, tab_history, tab_patient = st.tabs([
        "🚨 Clinical Alerts", "📋 Patient History", "🔬 Patient File"
    ])

    # ── TAB 1: Clinical Alerts ─────────────────────────────────────────────
    with tab_alerts:
        if not red_animals:
            st.success("✅ No RED alerts. All animals in normal or watch range.")
        else:
            st.markdown(
                f"<div class='section-header'>🚨 {len(red_animals)} ANIMALS NEED ATTENTION</div>",
                unsafe_allow_html=True
            )
            for a in red_animals:
                st.markdown(_alert_card(a), unsafe_allow_html=True)

                # Quick action buttons per animal
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"🔬 Assess {a['animal_tag']}",
                                 key=f"assess_{a['animal_tag']}",
                                 use_container_width=True):
                        st.session_state["vet_selected_animal"] = a["animal_tag"]
                        st.session_state["vet_active_tab"] = "patient"
                        st.rerun()
                with col_b:
                    if st.button(f"📋 History {a['animal_tag']}",
                                 key=f"hist_{a['animal_tag']}",
                                 use_container_width=True):
                        st.session_state["vet_selected_animal"] = a["animal_tag"]
                        st.rerun()
                st.markdown("<div style='margin-bottom:8px'></div>",
                            unsafe_allow_html=True)

        if yel_animals:
            st.markdown("---")
            st.markdown(
                f"<div class='section-header'>⚠️ {len(yel_animals)} ON WATCH</div>",
                unsafe_allow_html=True
            )
            for a in yel_animals:
                color, bg = _status_color("YELLOW")
                st.markdown(f"""
                <div style='background:{bg};border:1px solid {color};
                            border-radius:12px;padding:14px 18px;margin-bottom:8px'>
                    <span style='font-family:Space Mono,monospace;color:{color};font-weight:700'>
                        {a.get("animal_tag","—")}
                    </span>
                    <span style='color:#94a3b8;font-size:0.82rem;margin-left:12px'>
                        {a.get("species","—")} · {a.get("breed","—")} · {a.get("county","—")}
                    </span>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: Patient History ─────────────────────────────────────────────
    with tab_history:
        st.markdown("<div class='section-header'>SELECT ANIMAL</div>",
                    unsafe_allow_html=True)

        if not all_animals:
            st.info("No animals registered yet.")
            return

        tag_options = [a["animal_tag"] for a in all_animals]
        default_tag = st.session_state.get("vet_selected_animal", tag_options[0])
        default_idx = tag_options.index(default_tag) if default_tag in tag_options else 0

        selected_tag = st.selectbox("Animal tag", tag_options, index=default_idx,
                                    key="hist_tag_select")
        animal       = load_animal_full(selected_tag)

        if animal:
            color, bg = _status_color(animal.get("health_status","GREEN"))
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color};
                        border-radius:12px;padding:16px 20px;margin:12px 0'>
                <div style='font-family:Space Mono,monospace;color:{color};font-size:1rem;font-weight:700'>
                    {animal.get("animal_tag","—")} — {animal.get("health_status","—")}
                </div>
                <div style='color:#e8eaf0;margin-top:6px'>
                    {animal.get("species","—")} · {animal.get("breed","—")} ·
                    {animal.get("sex","—")} · {animal.get("coat_color","—")}
                </div>
                <div style='color:#64748b;font-size:0.8rem;margin-top:4px'>
                    {animal.get("age_months","?")} months ·
                    {animal.get("county","—")} · {animal.get("farm_location","—")}
                </div>
            </div>
            """, unsafe_allow_html=True)

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("<div class='section-header'>TEMPERATURE TREND</div>",
                        unsafe_allow_html=True)
            temps = load_temp_history(selected_tag)
            if temps:
                df_t = pd.DataFrame(temps)
                df_t["recorded_at"] = pd.to_datetime(
                    df_t["recorded_at"]).dt.strftime("%m-%d %H:%M")
                df_t["temp_celsius"] = df_t["temp_celsius"].astype(float)
                st.line_chart(df_t.set_index("recorded_at")["temp_celsius"])
            else:
                st.info("No temperature readings yet.")

        with col_r:
            st.markdown("<div class='section-header'>SYMPTOM FLAGS</div>",
                        unsafe_allow_html=True)
            sym_logs = load_symptom_history(selected_tag)
            if sym_logs:
                for log in sym_logs[:7]:
                    flag      = log.get("overall_flag","—")
                    color_map = {"RED":"#dc2626","YELLOW":"#d97706","GREEN":"#16a34a"}
                    c         = color_map.get(flag,"#64748b")
                    log_date  = log.get("logged_at","")[:10]
                    symptoms  = log.get("symptoms",{})
                    active    = ([k for k, v in symptoms.items() if v]
                                 if isinstance(symptoms, dict) else [])
                    st.markdown(f"""
                    <div style='border-left:3px solid {c};padding:6px 12px;
                                margin-bottom:6px;background:#0d1224;border-radius:0 8px 8px 0'>
                        <div style='color:{c};font-family:Space Mono,monospace;
                                    font-size:0.78rem;font-weight:700'>
                            {log_date} — {flag}
                        </div>
                        <div style='color:#64748b;font-size:0.73rem;margin-top:2px'>
                            {", ".join(active[:4]) if active else "No symptoms"}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No symptom logs yet.")

        st.markdown("---")
        st.markdown("<div class='section-header'>DISEASE ASSESSMENTS</div>",
                    unsafe_allow_html=True)
        assessments = load_assessments(selected_tag)
        if assessments:
            df_a = pd.DataFrame(assessments)[[
                "assessed_at","top_diagnosis","ccpp_score",
                "ppr_score","ecf_score","risk_level","assessed_by"
            ]]
            df_a["assessed_at"] = pd.to_datetime(
                df_a["assessed_at"]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(df_a, use_container_width=True, hide_index=True)
        else:
            st.info("No disease assessments recorded yet.")

    # ── TAB 3: Patient File ────────────────────────────────────────────────
    with tab_patient:
        st.markdown("<div class='section-header'>OPEN PATIENT FILE</div>",
                    unsafe_allow_html=True)

        if not all_animals:
            st.info("No animals registered yet.")
            return

        tag_options_p  = [a["animal_tag"] for a in all_animals]
        preselected    = st.session_state.get("vet_selected_animal", tag_options_p[0])
        default_idx_p  = tag_options_p.index(preselected) if preselected in tag_options_p else 0
        selected_tag_p = st.selectbox("Animal tag", tag_options_p,
                                      index=default_idx_p, key="patient_tag_select")
        animal_p       = load_animal_full(selected_tag_p)

        if not animal_p:
            st.warning("Animal not found.")
            return

        # Full profile
        color_p, bg_p = _status_color(animal_p.get("health_status","GREEN"))
        st.markdown(f"""
        <div style='background:{bg_p};border:2px solid {color_p};
                    border-radius:14px;padding:20px 24px;margin-bottom:20px'>
            <div style='font-family:Space Mono,monospace;color:{color_p};
                        font-size:1.1rem;font-weight:700;margin-bottom:10px'>
                {animal_p.get("animal_tag","—")} PATIENT FILE
            </div>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px'>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Species: <span style='color:#e8eaf0'>{animal_p.get("species","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Breed: <span style='color:#e8eaf0'>{animal_p.get("breed","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Sex: <span style='color:#e8eaf0'>{animal_p.get("sex","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Age: <span style='color:#e8eaf0'>{animal_p.get("age_months","?")} months</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Coat: <span style='color:#e8eaf0'>{animal_p.get("coat_color","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    County: <span style='color:#e8eaf0'>{animal_p.get("county","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Farm: <span style='color:#e8eaf0'>{animal_p.get("farm_location","—")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Collar: <span style='color:#38bdf8'>{animal_p.get("collar_id","None")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Bolus: <span style='color:#a78bfa'>{animal_p.get("bolus_id","None")}</span>
                </div>
                <div style='color:#94a3b8;font-size:0.82rem'>
                    Registered by: <span style='color:#e8eaf0'>{animal_p.get("registered_by","—")}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Last 3 temp readings inline
        temps_p = load_temp_history(selected_tag_p)
        if temps_p:
            st.markdown("<div class='section-header'>LAST TEMPERATURES</div>",
                        unsafe_allow_html=True)
            for t in temps_p[:3]:
                t_color, t_bg = _status_color(t.get("health_status","GREEN"))
                st.markdown(f"""
                <div style='background:{t_bg};border:1px solid {t_color};
                            border-radius:8px;padding:10px 14px;margin-bottom:6px;
                            display:flex;justify-content:space-between'>
                    <span style='font-family:Space Mono,monospace;color:{t_color};font-weight:700'>
                        {t.get("temp_celsius","—")}°C
                    </span>
                    <span style='color:#64748b;font-size:0.78rem'>
                        {t.get("time_of_day","—")} ·
                        {t.get("recorded_at","")[:16].replace("T"," ")}
                    </span>
                </div>
                """, unsafe_allow_html=True)
