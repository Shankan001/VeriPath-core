import streamlit as st
import pandas as pd
from datetime import datetime, timezone, time
from supabase_db import get_client

# ── Supabase table (run once in SQL editor):
# CREATE TABLE IF NOT EXISTS animal_temps (
#     id           SERIAL PRIMARY KEY,
#     animal_tag   TEXT NOT NULL,
#     company      TEXT NOT NULL,
#     recorded_by  TEXT NOT NULL,
#     temp_celsius NUMERIC(4,1) NOT NULL,
#     recorded_at  TIMESTAMPTZ DEFAULT NOW(),
#     time_of_day  TEXT,
#     health_status TEXT,
#     notes        TEXT
# );

SPECIES_THRESHOLDS = {
    "Goat": {
        "normal_min": 38.5, "normal_max": 40.0,
        "mild": 40.2, "significant": 40.5, "emergency": 41.5,
        "icon": "🐐",
    },
    "Cattle": {
        "normal_min": 38.0, "normal_max": 39.3,
        "mild": 39.5, "significant": 39.8, "emergency": 40.5,
        "icon": "🐄",
    },
    "Sheep": {
        "normal_min": 38.5, "normal_max": 39.5,
        "mild": 39.8, "significant": 40.0, "emergency": 41.0,
        "icon": "🐑",
    },
}

def _client():
    return get_client()

def _time_of_day() -> str:
    h = datetime.now().hour
    if 6 <= h < 12:  return "morning"
    if 12 <= h < 17: return "afternoon"
    if 17 <= h < 20: return "evening"
    return "night"

def classify_temp(temp: float, species: str, time_of_day: str) -> dict:
    """
    Returns dict with status, label, color, bg, message.
    GREEN  = normal range
    YELLOW = elevated but daytime only → heat stress, not pathological
    RED    = pathological — elevated at night/persistent
    """
    cfg = SPECIES_THRESHOLDS.get(species, SPECIES_THRESHOLDS["Goat"])

    if temp < cfg["normal_min"]:
        return {
            "status": "BLUE", "label": "● HYPOTHERMIA",
            "color": "#38bdf8", "bg": "#0f2233",
            "message": f"Below normal ({cfg['normal_min']}°C). Check for shock or exposure.",
            "alert_level": 2,
        }
    if temp <= cfg["normal_max"]:
        return {
            "status": "GREEN", "label": "● HEALTHY",
            "color": "#16a34a", "bg": "#071a0f",
            "message": f"Normal range ({cfg['normal_min']}–{cfg['normal_max']}°C).",
            "alert_level": 0,
        }
    if temp < cfg["significant"]:
        if time_of_day in ("afternoon", "evening"):
            return {
                "status": "YELLOW", "label": "● HEAT STRESS",
                "color": "#d97706", "bg": "#1a0f00",
                "message": f"Mild elevation at {time_of_day}. Likely ambient heat — recheck at night.",
                "alert_level": 1,
            }
        else:
            return {
                "status": "RED", "label": "● ALERT",
                "color": "#dc2626", "bg": "#1a0a0a",
                "message": f"Mild fever at {time_of_day} — not heat stress. Pathological cause likely.",
                "alert_level": 3,
            }
    if temp < cfg["emergency"]:
        return {
            "status": "RED", "label": "● ALERT",
            "color": "#dc2626", "bg": "#1a0a0a",
            "message": f"Significant fever ({temp}°C). Vet attention required within 12 hours.",
            "alert_level": 3,
        }
    return {
        "status": "RED", "label": "🚨 EMERGENCY",
        "color": "#ff0000", "bg": "#2d0000",
        "message": f"EMERGENCY: {temp}°C. Dispatch vet immediately.",
        "alert_level": 4,
    }

def save_temp_reading(record: dict) -> bool:
    try:
        _client().table("animal_temps").insert(record).execute()
        # Also update health_status on the animal record
        _client().table("animals").update(
            {"health_status": record["health_status"]}
        ).eq("animal_tag", record["animal_tag"]).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save reading: {e}")
        return False

def load_temp_history(animal_tag: str, limit: int = 20) -> list[dict]:
    try:
        res = (_client().table("animal_temps")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("recorded_at", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_all_alerts(company: str) -> list[dict]:
    """Load all RED animals for this company."""
    try:
        res = (_client().table("animal_temps")
               .select("*")
               .eq("company", company)
               .in_("health_status", ["RED", "BLUE"])
               .order("recorded_at", desc=True)
               .limit(50)
               .execute())
        return res.data or []
    except Exception:
        return []

def _status_bar(result: dict) -> str:
    return (
        f"<div style='background:{result['bg']};border:2px solid {result['color']};"
        f"border-radius:12px;padding:16px 20px;margin:12px 0'>"
        f"<div style='font-family:Space Mono,monospace;font-size:1.1rem;"
        f"color:{result['color']};font-weight:700'>{result['label']}</div>"
        f"<div style='color:#94a3b8;font-size:0.85rem;margin-top:6px'>{result['message']}</div>"
        f"</div>"
    )

def render_temp_monitoring(profile: dict):
    company  = profile.get("company", "")
    username = profile.get("username", "")
    role     = profile.get("role", "")

    st.markdown("# 🌡 Temperature Monitoring")
    st.markdown("<p style='color:#64748b'>GREEN / YELLOW / RED classification per species</p>",
                unsafe_allow_html=True)

    tab_entry, tab_alerts, tab_history = st.tabs([
        "🌡 Log Temperature", "🚨 Active Alerts", "📈 History"
    ])

    # ── TAB 1: Log Temperature ─────────────────────────────────────────────
    with tab_entry:
        if role not in ("admin", "farm_manager", "veterinarian", "herdsman"):
            st.warning("🔒 Temperature entry requires herdsman role or above.")
            return

        st.markdown("<div class='section-header'>NEW TEMPERATURE READING</div>",
                    unsafe_allow_html=True)

        # Load animals for this company
        try:
            res = (_client().table("animals")
                   .select("animal_tag, species, breed, sex")
                   .eq("company", company)
                   .eq("status", "active")
                   .execute())
            animals = res.data or []
        except Exception:
            animals = []

        if not animals:
            st.info("No animals registered. Add animals in the Animal Registry first.")
            return

        animal_options = {
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')} ({a.get('sex','')})": a
            for a in animals
        }

        with st.form("temp_entry_form"):
            selected_label = st.selectbox("Select Animal *", list(animal_options.keys()))
            selected_animal = animal_options[selected_label]
            species = selected_animal.get("species", "Goat")
            cfg = SPECIES_THRESHOLDS.get(species, SPECIES_THRESHOLDS["Goat"])

            col1, col2 = st.columns(2)
            with col1:
                temp = st.number_input(
                    f"Temperature (°C) *",
                    min_value=35.0, max_value=45.0,
                    value=float(cfg["normal_min"]),
                    step=0.1, format="%.1f"
                )
            with col2:
                tod_options = ["morning", "afternoon", "evening", "night"]
                tod_default = _time_of_day()
                tod = st.selectbox("Time of Day *", tod_options,
                                   index=tod_options.index(tod_default))

            notes = st.text_input("Notes", placeholder="Any visible symptoms?")
            submitted = st.form_submit_button("📥 Log Reading", use_container_width=True, type="primary")

        if submitted:
            result = classify_temp(temp, species, tod)
            st.markdown(_status_bar(result), unsafe_allow_html=True)

            record = {
                "animal_tag":    selected_animal["animal_tag"],
                "company":       company,
                "recorded_by":   username,
                "temp_celsius":  temp,
                "recorded_at":   datetime.now(timezone.utc).isoformat(),
                "time_of_day":   tod,
                "health_status": result["status"],
                "notes":         notes.strip() or None,
            }
            if save_temp_reading(record):
                st.success(f"✅ {temp}°C logged for {selected_animal['animal_tag']} — {result['label']}")
                if result["alert_level"] >= 3:
                    st.error("🚨 RED status logged. WhatsApp alert will fire in Step 9.")

        # Reference card
        st.markdown("---")
        st.markdown("<div class='section-header'>SPECIES THRESHOLDS</div>",
                    unsafe_allow_html=True)
        for sp, cfg in SPECIES_THRESHOLDS.items():
            icon = cfg["icon"]
            st.markdown(f"""
            <div style='background:#111827;border:1px solid #1e3a5f;border-radius:10px;
                        padding:12px 16px;margin-bottom:8px'>
                <span style='font-family:Space Mono,monospace;color:#38bdf8'>
                    {icon} {sp}
                </span>
                <span style='color:#4ade80;font-size:0.8rem;margin-left:12px'>
                    Normal {cfg['normal_min']}–{cfg['normal_max']}°C
                </span>
                <span style='color:#fbbf24;font-size:0.8rem;margin-left:8px'>
                    Mild ≥{cfg['mild']}°C
                </span>
                <span style='color:#f87171;font-size:0.8rem;margin-left:8px'>
                    Sig ≥{cfg['significant']}°C
                </span>
                <span style='color:#ff0000;font-size:0.8rem;margin-left:8px'>
                    Emergency ≥{cfg['emergency']}°C
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 2: Active Alerts ───────────────────────────────────────────────
    with tab_alerts:
        st.markdown("<div class='section-header'>🚨 ANIMALS NEEDING ATTENTION</div>",
                    unsafe_allow_html=True)
        alerts = load_all_alerts(company)
        if not alerts:
            st.success("✅ No RED or BLUE alerts. All animals in normal range.")
        else:
            for a in alerts:
                recorded_at = a.get("recorded_at","")[:16].replace("T"," ")
                status = a.get("health_status","RED")
                color = "#dc2626" if status == "RED" else "#38bdf8"
                bg    = "#1a0a0a" if status == "RED" else "#0f2233"
                st.markdown(f"""
                <div style='background:{bg};border:1px solid {color};border-radius:12px;
                            padding:14px 18px;margin-bottom:10px'>
                    <div style='display:flex;justify-content:space-between'>
                        <div style='font-family:Space Mono,monospace;color:{color};font-weight:700'>
                            {a.get('animal_tag','—')}
                        </div>
                        <div style='color:#64748b;font-size:0.78rem'>{recorded_at}</div>
                    </div>
                    <div style='color:#e8eaf0;margin-top:4px'>
                        {a.get('temp_celsius','—')}°C · {a.get('time_of_day','—')}
                    </div>
                    <div style='color:#94a3b8;font-size:0.8rem;margin-top:2px'>
                        {a.get('notes') or 'No notes'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 3: History ─────────────────────────────────────────────────────
    with tab_history:
        st.markdown("<div class='section-header'>TEMPERATURE HISTORY</div>",
                    unsafe_allow_html=True)
        try:
            res = (_client().table("animals")
                   .select("animal_tag")
                   .eq("company", company)
                   .execute())
            tags = [r["animal_tag"] for r in (res.data or [])]
        except Exception:
            tags = []

        if not tags:
            st.info("No animals registered yet.")
            return

        selected_tag = st.selectbox("Select animal", tags)
        history = load_temp_history(selected_tag, limit=30)

        if not history:
            st.info(f"No temperature readings for {selected_tag} yet.")
        else:
            df = pd.DataFrame(history)
            df["recorded_at"] = pd.to_datetime(df["recorded_at"]).dt.strftime("%Y-%m-%d %H:%M")
            df["temp_celsius"] = df["temp_celsius"].astype(float)

            st.line_chart(df.set_index("recorded_at")["temp_celsius"])
            st.dataframe(
                df[["recorded_at","temp_celsius","time_of_day","health_status","notes"]],
                use_container_width=True,
                hide_index=True
            )
