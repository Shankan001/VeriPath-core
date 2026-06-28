import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_client

def _client():
    return get_client()

def load_my_animals(company: str, owner_username: str) -> list[dict]:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("company", company)
               .eq("owner_username", owner_username)
               .eq("status", "active")
               .execute())
        return res.data or []
    except Exception:
        return []

def load_all_company_animals(company: str) -> list[dict]:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("company", company)
               .eq("status", "active")
               .execute())
        return res.data or []
    except Exception:
        return []

def load_latest_temp(animal_tag: str) -> dict | None:
    try:
        res = (_client().table("animal_temps")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("recorded_at", desc=True)
               .limit(1)
               .execute())
        return res.data[0] if res.data else None
    except Exception:
        return None

def load_latest_symptom(animal_tag: str) -> dict | None:
    try:
        res = (_client().table("symptom_logs")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("logged_at", desc=True)
               .limit(1)
               .execute())
        return res.data[0] if res.data else None
    except Exception:
        return None

def load_temp_trend(animal_tag: str, limit: int = 7) -> list[dict]:
    try:
        res = (_client().table("animal_temps")
               .select("temp_celsius, recorded_at, health_status, time_of_day")
               .eq("animal_tag", animal_tag)
               .order("recorded_at", desc=True)
               .limit(limit)
               .execute())
        return list(reversed(res.data or []))
    except Exception:
        return []

def _age_display(birth_date_str: str) -> str:
    try:
        bd   = date.fromisoformat(birth_date_str)
        diff = date.today() - bd
        months = diff.days // 30
        if months >= 24:
            return f"{months // 12} yrs {months % 12} mo"
        return f"{months} months"
    except Exception:
        return "—"

def _status_cfg(status: str) -> tuple[str, str, str]:
    return {
        "RED":    ("#dc2626", "#1a0a0a", "🚨 ALERT"),
        "YELLOW": ("#d97706", "#1a0f00", "⚠️ WATCH"),
        "GREEN":  ("#16a34a", "#071a0f", "✅ HEALTHY"),
        "BLUE":   ("#38bdf8", "#0f2233", "❄️ HYPOTHERMIA"),
    }.get(status, ("#64748b", "#0d1224", "● UNKNOWN"))

SPECIES_ICON = {"Goat": "🐐", "Cattle": "🐄", "Sheep": "🐑"}

def _animal_card_diaspora(a: dict, latest_temp: dict | None,
                           latest_sym: dict | None) -> str:
    status = a.get("health_status", "GREEN")
    color, bg, label = _status_cfg(status)
    icon   = SPECIES_ICON.get(a.get("species",""), "🐾")
    age    = _age_display(a.get("birth_date",""))

    temp_line = ""
    if latest_temp:
        t         = latest_temp.get("temp_celsius","—")
        t_time    = latest_temp.get("recorded_at","")[:16].replace("T"," ")
        t_tod     = latest_temp.get("time_of_day","")
        temp_line = (f"<div style='color:#94a3b8;font-size:0.78rem;margin-top:4px'>"
                     f"🌡 Last temp: <span style='color:#e8eaf0'>{t}°C</span> "
                     f"· {t_tod} · {t_time}</div>")

    sym_line = ""
    if latest_sym:
        sym_flag  = latest_sym.get("overall_flag","—")
        sym_date  = latest_sym.get("logged_at","")[:10]
        sym_color = {"RED":"#dc2626","YELLOW":"#d97706","GREEN":"#16a34a"}.get(sym_flag,"#64748b")
        sym_line  = (f"<div style='color:#94a3b8;font-size:0.78rem;margin-top:2px'>"
                     f"📋 Last check: <span style='color:{sym_color}'>{sym_flag}</span>"
                     f" · {sym_date}</div>")

    hw_line = ""
    if a.get("collar_id"):
        hw_line += "<span style='color:#38bdf8;font-size:0.72rem'>📡 COLLAR </span>"
    if a.get("bolus_id"):
        hw_line += "<span style='color:#a78bfa;font-size:0.72rem'>💊 BOLUS</span>"
    if hw_line:
        hw_line = f"<div style='margin-top:6px'>{hw_line}</div>"

    return f"""
    <div style='background:{bg};border:2px solid {color};
                border-radius:16px;padding:20px 22px;margin-bottom:16px'>
        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
            <div style='flex:1'>
                <div style='font-family:Space Mono,monospace;font-size:1.05rem;
                            color:{color};font-weight:700'>
                    {icon} {a.get("animal_tag","—")}
                </div>
                <div style='color:#e8eaf0;margin-top:6px;font-size:0.88rem'>
                    {a.get("breed","—")} · {a.get("sex","—")} · {a.get("coat_color","—")}
                </div>
                <div style='color:#64748b;font-size:0.78rem;margin-top:2px'>
                    {age} · {a.get("county","—")} · {a.get("farm_location","—")}
                </div>
                {temp_line}
                {sym_line}
                {hw_line}
            </div>
            <div style='text-align:center;min-width:80px'>
                <div style='background:{bg};border:1px solid {color};
                            border-radius:50%;width:60px;height:60px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.5rem;margin:0 auto'>
                    {icon}
                </div>
                <div style='font-family:Space Mono,monospace;color:{color};
                            font-size:0.7rem;margin-top:6px;font-weight:700'>
                    {label}
                </div>
            </div>
        </div>
    </div>
    """

def render_diaspora_dashboard(profile: dict):
    company  = profile.get("company", "")
    username = profile.get("username", "")
    role     = profile.get("role", "")

    st.markdown("# 🌍 My Animals")
    st.markdown(
        "<p style='color:#64748b'>Your herd — health status · temperature · vet reports</p>",
        unsafe_allow_html=True
    )

    # Admin/farm_manager sees all animals; diaspora_owner sees only theirs
    if role in ("admin", "farm_manager", "veterinarian"):
        animals = load_all_company_animals(company)
    else:
        animals = load_my_animals(company, username)

    if not animals:
        st.markdown("""
        <div style='background:#0d1224;border:1px dashed #1e3a5f;
                    border-radius:16px;padding:48px;text-align:center;margin-top:24px'>
            <div style='font-size:3rem'>🐄</div>
            <div style='color:#64748b;margin-top:12px;font-size:0.95rem'>
                No animals registered to your account yet.
            </div>
            <div style='color:#475569;font-size:0.8rem;margin-top:6px'>
                Contact your farm manager to register and link your animals.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Summary strip ──────────────────────────────────────────────────────
    red_count = sum(1 for a in animals if a.get("health_status") == "RED")
    yel_count = sum(1 for a in animals if a.get("health_status") == "YELLOW")
    grn_count = sum(1 for a in animals if a.get("health_status") == "GREEN")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>MY ANIMALS</div>
        <div class='metric-value'>{len(animals)}</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>🚨 ALERTS</div>
        <div class='metric-value' style='color:#dc2626'>{red_count}</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>⚠️ WATCH</div>
        <div class='metric-value' style='color:#d97706'>{yel_count}</div>
    </div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>✅ HEALTHY</div>
        <div class='metric-value' style='color:#16a34a'>{grn_count}</div>
    </div>""", unsafe_allow_html=True)

    # ── RED banner ─────────────────────────────────────────────────────────
    if red_count:
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #dc2626;
                    border-radius:12px;padding:16px 20px;margin:16px 0;text-align:center'>
            <div style='font-family:Space Mono,monospace;color:#dc2626;
                        font-size:1rem;font-weight:700'>
                🚨 {red_count} ANIMAL{"S" if red_count > 1 else ""} NEED VET ATTENTION
            </div>
            <div style='color:#94a3b8;font-size:0.82rem;margin-top:6px'>
                WhatsApp alert sent · Vet dispatch triggered
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    tab_cards, tab_trends = st.tabs(["🐄 Animal Cards", "📈 Health Trends"])

    # ── TAB 1: Cards ───────────────────────────────────────────────────────
    with tab_cards:
        # Sort: RED first, then YELLOW, then GREEN
        priority = {"RED": 0, "YELLOW": 1, "GREEN": 2, "BLUE": 0}
        sorted_animals = sorted(
            animals, key=lambda a: priority.get(a.get("health_status","GREEN"), 3)
        )

        # Filter
        filter_col1, filter_col2 = st.columns(2)
        status_filter  = filter_col1.multiselect(
            "Filter by status", ["RED","YELLOW","GREEN"], default=[]
        )
        species_filter = filter_col2.multiselect(
            "Filter by species", ["Goat","Cattle","Sheep"], default=[]
        )

        filtered = sorted_animals
        if status_filter:
            filtered = [a for a in filtered if a.get("health_status") in status_filter]
        if species_filter:
            filtered = [a for a in filtered if a.get("species") in species_filter]

        st.markdown(
            f"<div class='section-header'>HERD — {len(filtered)} ANIMALS</div>",
            unsafe_allow_html=True
        )

        for a in filtered:
            latest_temp = load_latest_temp(a["animal_tag"])
            latest_sym  = load_latest_symptom(a["animal_tag"])
            st.markdown(
                _animal_card_diaspora(a, latest_temp, latest_sym),
                unsafe_allow_html=True
            )

    # ── TAB 2: Trends ──────────────────────────────────────────────────────
    with tab_trends:
        st.markdown("<div class='section-header'>TEMPERATURE TREND</div>",
                    unsafe_allow_html=True)

        if not animals:
            st.info("No animals yet.")
            return

        tag_options = [a["animal_tag"] for a in animals]
        selected    = st.selectbox("Select animal", tag_options, key="diaspora_trend_select")
        trend       = load_temp_trend(selected, limit=14)

        if not trend:
            st.info(f"No temperature readings for {selected} yet.")
        else:
            df = pd.DataFrame(trend)
            df["recorded_at"]   = pd.to_datetime(df["recorded_at"]).dt.strftime("%m-%d %H:%M")
            df["temp_celsius"]  = df["temp_celsius"].astype(float)

            st.line_chart(df.set_index("recorded_at")["temp_celsius"])

            # Color-coded table
            for _, row in df.iterrows():
                hs    = row.get("health_status","GREEN")
                color, bg, label = _status_cfg(hs)
                st.markdown(f"""
                <div style='background:{bg};border-left:3px solid {color};
                            border-radius:0 8px 8px 0;padding:6px 14px;
                            margin-bottom:4px;display:flex;justify-content:space-between'>
                    <span style='font-family:Space Mono,monospace;color:{color};font-weight:700'>
                        {row["temp_celsius"]}°C
                    </span>
                    <span style='color:#64748b;font-size:0.75rem'>
                        {row.get("time_of_day","—")} · {row["recorded_at"]}
                    </span>
                    <span style='color:{color};font-size:0.72rem;font-family:Space Mono,monospace'>
                        {label}
                    </span>
                </div>
                """, unsafe_allow_html=True)
