import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_client

# ── SQL (run once in Supabase):
# CREATE TABLE IF NOT EXISTS symptom_logs (
#     id           SERIAL PRIMARY KEY,
#     animal_tag   TEXT NOT NULL,
#     company      TEXT NOT NULL,
#     logged_by    TEXT NOT NULL,
#     logged_at    TIMESTAMPTZ DEFAULT NOW(),
#     log_date     DATE,
#     symptoms     JSONB,
#     behavior     TEXT,
#     appetite     TEXT,
#     stool        TEXT,
#     gait         TEXT,
#     overall_flag TEXT,
#     notes        TEXT
# );

def _client():
    return get_client()

SYMPTOM_GROUPS = {
    "Respiratory": {
        "coughing":           "Coughing",
        "nasal_discharge":    "Nasal discharge",
        "laboured_breathing": "Laboured / painful breathing",
        "nasal_froth":        "Froth at nostrils",
    },
    "Eyes & Mouth": {
        "eye_discharge":      "Eye discharge (watery or thick)",
        "excessive_tearing":  "Excessive tearing",
        "oral_lesions":       "Mouth sores / ulcers",
        "drooling":           "Excessive drooling / salivation",
    },
    "Body & Skin": {
        "enlarged_lymph":     "Swollen lymph nodes (neck / shoulder)",
        "skin_lesions":       "Skin lesions or hair loss",
        "bloating":           "Bloating / distended abdomen",
        "limping":            "Limping or joint swelling",
    },
    "Behaviour": {
        "lethargy":           "Lethargy / standing apart from herd",
        "restlessness":       "Restlessness or agitation",
        "aggression":         "Unusual aggression",
        "pawing_ground":      "Pawing at ground / head pressing",
    },
}

APPETITE_OPTIONS = ["Normal", "Reduced", "Not eating at all", "Eating more than usual"]
STOOL_OPTIONS    = ["Normal", "Loose / diarrhea", "Blood in stool", "No stool (constipated)", "Unusual color"]
GAIT_OPTIONS     = ["Normal", "Slight limp", "Severe limp", "Refusing to walk", "Ataxia / staggering"]

def _auto_flag(symptoms: dict, appetite: str, stool: str, gait: str) -> str:
    """Rule-based overall flag from checklist."""
    red_symptoms = {
        "laboured_breathing","nasal_froth","oral_lesions",
        "enlarged_lymph","pawing_ground",
    }
    yellow_symptoms = {
        "coughing","nasal_discharge","eye_discharge",
        "lethargy","bloating","limping",
    }
    active = {k for k, v in symptoms.items() if v}
    if (active & red_symptoms
            or stool in ("Blood in stool",)
            or gait in ("Refusing to walk","Ataxia / staggering")
            or appetite == "Not eating at all"):
        return "RED"
    if (active & yellow_symptoms
            or stool in ("Loose / diarrhea","No stool (constipated)")
            or gait in ("Slight limp","Severe limp")
            or appetite == "Reduced"):
        return "YELLOW"
    return "GREEN"

def _flag_badge(flag: str) -> str:
    cfg = {
        "GREEN":  ("#16a34a", "#071a0f", "● ALL CLEAR"),
        "YELLOW": ("#d97706", "#1a0f00", "● WATCH"),
        "RED":    ("#dc2626", "#1a0a0a", "🚨 ALERT"),
    }
    color, bg, label = cfg.get(flag, ("#64748b","#0d1224","—"))
    return (f"<span style='background:{bg};border:1px solid {color};"
            f"border-radius:20px;padding:4px 14px;font-size:0.82rem;"
            f"color:{color};font-family:Space Mono,monospace'>{label}</span>")

def save_log(record: dict) -> bool:
    try:
        _client().table("symptom_logs").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save log: {e}")
        return False

def load_logs(company: str, limit: int = 30) -> list[dict]:
    try:
        res = (_client().table("symptom_logs")
               .select("*")
               .eq("company", company)
               .order("logged_at", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_animal_logs(animal_tag: str, limit: int = 14) -> list[dict]:
    try:
        res = (_client().table("symptom_logs")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("logged_at", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception:
        return []

def render_symptom_log(profile: dict):
    company  = profile.get("company", "")
    username = profile.get("username", "")
    role     = profile.get("role", "")

    st.markdown("# 📋 Daily Symptom Log")
    st.markdown(
        "<p style='color:#64748b'>Morning & evening herdsman checklist — feeds disease engine</p>",
        unsafe_allow_html=True
    )

    tab_log, tab_review = st.tabs(["✏️ Log Symptoms", "📊 Review Logs"])

    # ── TAB 1: Log ─────────────────────────────────────────────────────────
    with tab_log:
        if role not in ("admin","farm_manager","veterinarian","herdsman"):
            st.warning("🔒 Symptom logging requires herdsman role or above.")
            return

        # Load animals
        try:
            res = (_client().table("animals")
                   .select("animal_tag, species, breed, sex, health_status")
                   .eq("company", company)
                   .eq("status", "active")
                   .execute())
            animals = res.data or []
        except Exception:
            animals = []

        if not animals:
            st.info("No animals registered. Add animals in Animal Registry first.")
            return

        # RED animals first
        sorted_animals = (
            [a for a in animals if a.get("health_status") == "RED"] +
            [a for a in animals if a.get("health_status") != "RED"]
        )
        animal_options = {
            f"{'🚨 ' if a.get('health_status')=='RED' else ''}"
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in sorted_animals
        }

        st.markdown("<div class='section-header'>SELECT ANIMAL</div>",
                    unsafe_allow_html=True)
        selected_label  = st.selectbox("Animal", list(animal_options.keys()))
        selected_animal = animal_options[selected_label]

        # Show last log for this animal
        last_logs = load_animal_logs(selected_animal["animal_tag"], limit=1)
        if last_logs:
            last = last_logs[0]
            last_date = last.get("logged_at","")[:10]
            last_flag = last.get("overall_flag","—")
            st.markdown(
                f"<small style='color:#64748b'>Last log: {last_date} — "
                f"{_flag_badge(last_flag)}</small>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("<div class='section-header'>SYMPTOM CHECKLIST</div>",
                    unsafe_allow_html=True)

        all_symptoms = {}
        for group_name, group_symptoms in SYMPTOM_GROUPS.items():
            st.markdown(
                f"<div style='color:#38bdf8;font-family:Space Mono,monospace;"
                f"font-size:0.8rem;margin:14px 0 6px 0;text-transform:uppercase;"
                f"letter-spacing:0.08em'>{group_name}</div>",
                unsafe_allow_html=True
            )
            cols = st.columns(2)
            for i, (sym_key, sym_label) in enumerate(group_symptoms.items()):
                with cols[i % 2]:
                    all_symptoms[sym_key] = st.checkbox(sym_label, key=f"log_{sym_key}")

        st.markdown("---")
        st.markdown("<div class='section-header'>BEHAVIOUR & VITALS</div>",
                    unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            appetite = st.selectbox("Appetite", APPETITE_OPTIONS)
        with col2:
            stool = st.selectbox("Stool", STOOL_OPTIONS)
        with col3:
            gait = st.selectbox("Gait / Movement", GAIT_OPTIONS)

        notes = st.text_area("Herdsman notes",
                             placeholder="Any other observations...", height=80)

        st.markdown("---")
        if st.button("✅ Submit Daily Log", use_container_width=True, type="primary"):
            flag = _auto_flag(all_symptoms, appetite, stool, gait)
            active_symptoms = [k for k, v in all_symptoms.items() if v]

            st.markdown(
                f"<div style='margin:12px 0'>Overall status: {_flag_badge(flag)}</div>",
                unsafe_allow_html=True
            )

            if active_symptoms:
                st.markdown(
                    f"<div style='color:#94a3b8;font-size:0.82rem'>"
                    f"Symptoms logged: {', '.join(active_symptoms)}</div>",
                    unsafe_allow_html=True
                )

            record = {
                "animal_tag":   selected_animal["animal_tag"],
                "company":      company,
                "logged_by":    username,
                "logged_at":    datetime.now(timezone.utc).isoformat(),
                "log_date":     date.today().isoformat(),
                "symptoms":     all_symptoms,
                "behavior":     gait,
                "appetite":     appetite,
                "stool":        stool,
                "gait":         gait,
                "overall_flag": flag,
                "notes":        notes.strip() or None,
            }
            if save_log(record):
                st.success(
                    f"✅ Log saved for {selected_animal['animal_tag']} — {flag} status."
                )
                if flag == "RED":
                    st.error("🚨 RED flag. WhatsApp alert fires in Step 9.")
                elif flag == "YELLOW":
                    st.warning("⚠️ YELLOW flag. Monitor closely — recheck in 4 hours.")
                st.rerun()

    # ── TAB 2: Review ──────────────────────────────────────────────────────
    with tab_review:
        st.markdown("<div class='section-header'>RECENT LOGS</div>",
                    unsafe_allow_html=True)

        logs = load_logs(company)
        if not logs:
            st.info("No symptom logs recorded yet.")
            return

        # Summary counts
        red_count    = sum(1 for l in logs if l.get("overall_flag") == "RED")
        yellow_count = sum(1 for l in logs if l.get("overall_flag") == "YELLOW")
        green_count  = sum(1 for l in logs if l.get("overall_flag") == "GREEN")

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>🚨 RED FLAGS</div>
            <div class='metric-value' style='color:#dc2626'>{red_count}</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>⚠️ YELLOW FLAGS</div>
            <div class='metric-value' style='color:#d97706'>{yellow_count}</div>
        </div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>✅ ALL CLEAR</div>
            <div class='metric-value' style='color:#16a34a'>{green_count}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        flag_filter = st.multiselect(
            "Filter by flag",
            ["RED","YELLOW","GREEN"],
            default=["RED","YELLOW"]
        )
        filtered = [l for l in logs if l.get("overall_flag") in flag_filter] if flag_filter else logs

        for log in filtered:
            flag       = log.get("overall_flag","—")
            logged_at  = log.get("logged_at","")[:16].replace("T"," ")
            symptoms   = log.get("symptoms", {})
            active_sym = [k for k, v in symptoms.items() if v] if isinstance(symptoms, dict) else []
            color_map  = {"RED":"#dc2626","YELLOW":"#d97706","GREEN":"#16a34a"}
            bg_map     = {"RED":"#1a0a0a","YELLOW":"#1a0f00","GREEN":"#071a0f"}
            color = color_map.get(flag,"#64748b")
            bg    = bg_map.get(flag,"#0d1224")

            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color};
                        border-radius:12px;padding:14px 18px;margin-bottom:10px'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                    <div style='font-family:Space Mono,monospace;
                                color:{color};font-weight:700'>
                        {log.get('animal_tag','—')}
                    </div>
                    <div style='color:#64748b;font-size:0.75rem'>{logged_at}</div>
                </div>
                <div style='color:#94a3b8;font-size:0.8rem;margin-top:4px'>
                    Appetite: {log.get('appetite','—')} ·
                    Stool: {log.get('stool','—')} ·
                    Gait: {log.get('gait','—')}
                </div>
                <div style='color:#64748b;font-size:0.75rem;margin-top:4px'>
                    {', '.join(active_sym) if active_sym else 'No symptoms checked'}
                </div>
                {f"<div style='color:#94a3b8;font-size:0.78rem;margin-top:4px;font-style:italic'>{log.get('notes','')}</div>" if log.get('notes') else ''}
            </div>
            """, unsafe_allow_html=True)

        if st.button("⬇ Export Logs CSV"):
            df = pd.DataFrame(logs)
            st.download_button(
                "Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"veripath_symptom_logs_{date.today()}.csv",
                mime="text/csv"
            )
