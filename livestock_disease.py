import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from supabase_db import get_supabase_client

# ── Supabase table (run once in SQL editor):
# CREATE TABLE IF NOT EXISTS disease_assessments (
#     id             SERIAL PRIMARY KEY,
#     animal_tag     TEXT NOT NULL,
#     company        TEXT NOT NULL,
#     assessed_by    TEXT NOT NULL,
#     assessed_at    TIMESTAMPTZ DEFAULT NOW(),
#     temp_celsius   NUMERIC(4,1),
#     fever_hours    INTEGER,
#     symptoms       JSONB,
#     ccpp_score     INTEGER,
#     ppr_score      INTEGER,
#     ecf_score      INTEGER,
#     top_diagnosis  TEXT,
#     risk_level     TEXT,
#     recommendation TEXT,
#     notes          TEXT
# );

def _client():
    return get_supabase_client()

# ── Disease definitions ────────────────────────────────────────────────────
DISEASES = {
    "CCPP": {
        "name":        "Contagious Caprine Pleuropneumonia",
        "species":     ["Goat"],
        "color":       "#dc2626",
        "bg":          "#1a0a0a",
        "icon":        "🫁",
        "description": "Highly contagious bacterial lung disease in goats. Fatal if untreated.",
        "symptoms": {
            "fever_12_48hrs":        {"label": "Fever present 12–48 hrs",          "weight": 25},
            "painful_breathing":     {"label": "Painful/laboured breathing",        "weight": 25},
            "coughing":              {"label": "Coughing (dry then moist)",         "weight": 20},
            "nasal_discharge":       {"label": "Nasal discharge",                   "weight": 15},
            "reluctance_to_move":    {"label": "Reluctant to move, stands apart",   "weight": 10},
            "loss_of_appetite":      {"label": "Loss of appetite",                  "weight": 5},
        },
        "vet_action":  "Isolate immediately. Tylosin or Oxytetracycline within 24hrs. Notify DVS.",
        "urgency":     "DISPATCH VET WITHIN 6 HOURS",
    },
    "PPR": {
        "name":        "Peste des Petits Ruminants",
        "species":     ["Goat", "Sheep"],
        "color":       "#d97706",
        "bg":          "#1a0f00",
        "icon":        "🦠",
        "description": "Viral disease. Notifiable to DVS Kenya. Spreads rapidly in herds.",
        "symptoms": {
            "fever_24_72hrs":        {"label": "Fever 24–72 hrs before other signs", "weight": 20},
            "depression":            {"label": "Severe depression / lethargy",        "weight": 20},
            "ocular_discharge":      {"label": "Eye discharge (watery then mucopurulent)", "weight": 20},
            "nasal_discharge":       {"label": "Nasal discharge",                    "weight": 15},
            "oral_lesions":          {"label": "Oral lesions / necrotic stomatitis", "weight": 15},
            "diarrhea":              {"label": "Profuse diarrhea",                   "weight": 10},
        },
        "vet_action":  "NOTIFIABLE DISEASE. Contact DVS Kenya immediately. No cure — supportive care + antibiotics for secondary infection.",
        "urgency":     "NOTIFY DVS KENYA WITHIN 24 HOURS",
    },
    "ECF": {
        "name":        "East Coast Fever",
        "species":     ["Cattle"],
        "color":       "#7c3aed",
        "bg":          "#120a1a",
        "icon":        "🕷",
        "description": "Tick-borne protozoan disease. Major cattle killer in East Africa.",
        "symptoms": {
            "fever_2_5days":         {"label": "Fever 2–5 days before other signs", "weight": 20},
            "enlarged_lymph_nodes":  {"label": "Enlarged lymph nodes (parotid)",    "weight": 25},
            "weakness":              {"label": "Progressive weakness",               "weight": 20},
            "respiratory_distress":  {"label": "Respiratory distress / nasal froth","weight": 20},
            "lacrimation":           {"label": "Excessive tearing",                 "weight": 10},
            "loss_of_appetite":      {"label": "Loss of appetite",                  "weight": 5},
        },
        "vet_action":  "Buparvaquone (Butalex) injection within 48hrs of fever onset. Tick control immediately.",
        "urgency":     "TREAT WITHIN 48 HOURS OR FATALITY LIKELY",
    },
}

def score_disease(symptom_responses: dict, disease_key: str) -> int:
    """Returns 0-100 probability score for a disease."""
    disease = DISEASES[disease_key]
    total_weight = sum(s["weight"] for s in disease["symptoms"].values())
    earned = sum(
        disease["symptoms"][sym]["weight"]
        for sym in disease["symptoms"]
        if symptom_responses.get(sym, False)
    )
    return round((earned / total_weight) * 100) if total_weight else 0

def get_risk_level(score: int) -> tuple[str, str, str]:
    """Returns (level, color, bg)."""
    if score >= 70:
        return "HIGH",   "#dc2626", "#1a0a0a"
    if score >= 40:
        return "MEDIUM", "#d97706", "#1a0f00"
    if score >= 20:
        return "LOW",    "#16a34a", "#071a0f"
    return "NEGLIGIBLE", "#64748b", "#0d1224"

def save_assessment(record: dict) -> bool:
    try:
        _client().table("disease_assessments").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save assessment: {e}")
        return False

def load_assessments(company: str, limit: int = 20) -> list[dict]:
    try:
        res = (_client().table("disease_assessments")
               .select("*")
               .eq("company", company)
               .order("assessed_at", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception:
        return []

def _score_bar(score: int, color: str) -> str:
    return (
        f"<div style='background:#1e2d45;border-radius:8px;height:10px;margin-top:6px'>"
        f"<div style='background:{color};width:{score}%;height:10px;"
        f"border-radius:8px;transition:width 0.5s'></div></div>"
    )

def _disease_result_card(disease_key: str, score: int) -> str:
    d = DISEASES[disease_key]
    level, color, bg = get_risk_level(score)
    bar = _score_bar(score, color)
    return (
        f"<div style='background:{bg};border:2px solid {color};"
        f"border-radius:14px;padding:18px 20px;margin-bottom:12px'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
        f"<div style='font-family:Space Mono,monospace;color:{color};font-size:1rem;font-weight:700'>"
        f"{d['icon']} {disease_key} — {d['name']}</div>"
        f"<div style='font-family:Space Mono,monospace;font-size:1.4rem;color:{color};font-weight:700'>"
        f"{score}%</div></div>"
        f"{bar}"
        f"<div style='color:#94a3b8;font-size:0.78rem;margin-top:8px'>{d['description']}</div>"
        f"<div style='color:{color};font-size:0.8rem;margin-top:6px;font-weight:600'>"
        f"Risk: {level}</div>"
        f"</div>"
    )

def render_disease_engine(profile: dict):
    company  = profile.get("company", "")
    username = profile.get("username", "")
    role     = profile.get("role", "")

    st.markdown("# 🧪 Disease Probability Engine")
    st.markdown(
        "<p style='color:#64748b'>CCPP · PPR · ECF — symptom-weighted scoring</p>",
        unsafe_allow_html=True
    )

    tab_assess, tab_history = st.tabs(["🔬 Run Assessment", "📋 Assessment History"])

    # ── TAB 1: Assessment ──────────────────────────────────────────────────
    with tab_assess:
        if role not in ("admin", "veterinarian", "farm_manager"):
            st.warning("🔒 Disease assessment requires veterinarian or farm_manager role.")
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

        # Pre-filter RED animals to top
        red_animals   = [a for a in animals if a.get("health_status") == "RED"]
        other_animals = [a for a in animals if a.get("health_status") != "RED"]
        sorted_animals = red_animals + other_animals

        animal_options = {
            f"{'🚨 ' if a.get('health_status')=='RED' else ''}"
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in sorted_animals
        }

        st.markdown("<div class='section-header'>STEP 1 — SELECT ANIMAL</div>",
                    unsafe_allow_html=True)
        selected_label  = st.selectbox("Animal", list(animal_options.keys()))
        selected_animal = animal_options[selected_label]
        species         = selected_animal.get("species", "Goat")

        # Filter diseases by species
        applicable = {
            k: v for k, v in DISEASES.items()
            if species in v["species"]
        }

        if not applicable:
            st.warning(f"No disease models configured for {species} yet.")
            return

        st.markdown("---")
        st.markdown("<div class='section-header'>STEP 2 — VITAL SIGNS</div>",
                    unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            temp = st.number_input("Current temperature (°C)",
                                   min_value=35.0, max_value=45.0,
                                   value=39.0, step=0.1, format="%.1f")
        with col2:
            fever_hours = st.number_input("Hours fever has been present",
                                          min_value=0, max_value=168, value=0, step=1)

        st.markdown("---")
        st.markdown("<div class='section-header'>STEP 3 — SYMPTOM CHECKLIST</div>",
                    unsafe_allow_html=True)

        # Collect all unique symptoms across applicable diseases
        all_symptom_keys = {}
        for d_key, d_val in applicable.items():
            for sym_key, sym_val in d_val["symptoms"].items():
                if sym_key not in all_symptom_keys:
                    all_symptom_keys[sym_key] = sym_val["label"]

        symptom_responses = {}
        cols = st.columns(2)
        for i, (sym_key, sym_label) in enumerate(all_symptom_keys.items()):
            with cols[i % 2]:
                symptom_responses[sym_key] = st.checkbox(sym_label, key=f"sym_{sym_key}")

        notes = st.text_area("Clinical notes", placeholder="Additional observations...", height=80)

        st.markdown("---")
        if st.button("🔬 Calculate Disease Probability", use_container_width=True, type="primary"):
            st.markdown("<div class='section-header'>ASSESSMENT RESULTS</div>",
                        unsafe_allow_html=True)

            scores = {k: score_disease(symptom_responses, k) for k in applicable}
            top_disease = max(scores, key=scores.get)
            top_score   = scores[top_disease]
            top_level, _, _ = get_risk_level(top_score)

            for d_key, score in sorted(scores.items(), key=lambda x: -x[1]):
                st.markdown(_disease_result_card(d_key, score), unsafe_allow_html=True)

            # Recommendation
            if top_score >= 40:
                d = DISEASES[top_disease]
                st.markdown(f"""
                <div style='background:#0f2233;border:2px solid #38bdf8;
                            border-radius:14px;padding:20px 24px;margin-top:16px'>
                    <div style='font-family:Space Mono,monospace;color:#38bdf8;
                                font-size:1rem;font-weight:700'>
                        ⚡ RECOMMENDED ACTION — {top_disease}
                    </div>
                    <div style='color:#e8eaf0;margin-top:10px;line-height:1.6'>
                        {d['vet_action']}
                    </div>
                    <div style='color:#f87171;font-family:Space Mono,monospace;
                                font-size:0.85rem;margin-top:10px;font-weight:700'>
                        ⏱ {d['urgency']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.success("✅ Low probability for all modelled diseases. Continue monitoring.")

            # Save
            record = {
                "animal_tag":    selected_animal["animal_tag"],
                "company":       company,
                "assessed_by":   username,
                "assessed_at":   datetime.now(timezone.utc).isoformat(),
                "temp_celsius":  temp,
                "fever_hours":   fever_hours,
                "symptoms":      symptom_responses,
                "ccpp_score":    scores.get("CCPP", 0),
                "ppr_score":     scores.get("PPR", 0),
                "ecf_score":     scores.get("ECF", 0),
                "top_diagnosis": top_disease,
                "risk_level":    top_level,
                "recommendation":DISEASES[top_disease]["vet_action"] if top_score >= 40 else "Monitor",
                "notes":         notes.strip() or None,
            }
            if save_assessment(record):
                st.success(f"✅ Assessment saved for {selected_animal['animal_tag']}.")

    # ── TAB 2: History ─────────────────────────────────────────────────────
    with tab_history:
        st.markdown("<div class='section-header'>RECENT ASSESSMENTS</div>",
                    unsafe_allow_html=True)
        assessments = load_assessments(company)
        if not assessments:
            st.info("No assessments recorded yet.")
            return

        for a in assessments:
            top   = a.get("top_diagnosis","—")
            score = a.get(f"{top.lower()}_score", 0) if top != "—" else 0
            level, color, bg = get_risk_level(score)
            assessed_at = a.get("assessed_at","")[:16].replace("T"," ")
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color};
                        border-radius:12px;padding:14px 18px;margin-bottom:10px'>
                <div style='display:flex;justify-content:space-between'>
                    <div style='font-family:Space Mono,monospace;color:{color};font-weight:700'>
                        {a.get('animal_tag','—')} — {top}
                    </div>
                    <div style='color:#64748b;font-size:0.78rem'>{assessed_at}</div>
                </div>
                <div style='color:#e8eaf0;margin-top:4px;font-size:0.85rem'>
                    CCPP: {a.get('ccpp_score',0)}% &nbsp;·&nbsp;
                    PPR: {a.get('ppr_score',0)}% &nbsp;·&nbsp;
                    ECF: {a.get('ecf_score',0)}%
                </div>
                <div style='color:#94a3b8;font-size:0.78rem;margin-top:2px'>
                    Risk: {level} · Assessed by {a.get('assessed_by','—')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("⬇ Export Assessments CSV"):
            df = pd.DataFrame(assessments)
            st.download_button(
                "Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"veripath_assessments_{datetime.now().date()}.csv",
                mime="text/csv"
            )
