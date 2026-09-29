"""
VeriPath — Growth & Feed Tracker
Herdsman-facing entry forms for weight logging and feed *quantity*
logging, plus a performance overview (ADG, cost-per-kg-gained, FCR)
per animal.

Cost of feed is NOT logged here — it's logged in the existing
Cost of Production page (livestock_costs.py -> animal_costs table,
cost_type='feed'), which already supports single-animal and
whole-herd-split entry. This file only tracks feed QUANTITY, so FCR
(feed conversion ratio) can be computed; the money side stays in the
one place it already lives, avoiding a second, inconsistent path
writing to animal_costs.

Writes to: growth_records, feed_input_records
Reads from views: animal_adg, animal_cost_per_kg_gained, animal_fcr
"""

import streamlit as st
import pandas as pd
from datetime import date
from supabase_db import get_client
from livestock import load_animals

ALLOWED_ROLES = ("admin", "farm_manager", "diaspora_owner", "herdsman")

WEIGHT_TYPES = ["birth", "weaning", "periodic", "sale"]
WEIGH_METHODS = ["scale", "tape_estimate"]
FEED_TYPES = [
    "Napier grass", "Dairy meal", "Mineral lick", "Hay", "Silage",
    "Maize germ", "Wheat bran", "Concentrate pellets", "Other"
]


def _client():
    return get_client()


def save_growth_record(record: dict) -> bool:
    try:
        _client().table("growth_records").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save weight record: {e}")
        return False


def save_feed_record(record: dict) -> bool:
    try:
        _client().table("feed_input_records").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save feed record: {e}")
        return False


def get_growth_history(animal_tag: str) -> list[dict]:
    try:
        res = (_client().table("growth_records")
               .select("*")
               .eq("animal_tag", animal_tag)
               .order("recorded_date", desc=False)
               .execute())
        return res.data or []
    except Exception as e:
        st.error(f"Failed to load growth history: {e}")
        return []


def get_performance_view(view_name: str, animal_tags: list[str]) -> list[dict]:
    if not animal_tags:
        return []
    try:
        res = (_client().table(view_name)
               .select("*")
               .in_("animal_tag", animal_tags)
               .execute())
        return res.data or []
    except Exception as e:
        st.error(f"Failed to load {view_name}: {e}")
        return []


def _metric_card(label: str, value: str, color: str) -> str:
    return f"""
    <div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value' style='color:{color}'>{value}</div>
    </div>"""


def _weight_badge(weight_type: str) -> str:
    cfg = {
        "birth":    ("#38bdf8", "BIRTH"),
        "weaning":  ("#fbbf24", "WEANING"),
        "periodic": ("#4ade80", "PERIODIC"),
        "sale":     ("#a78bfa", "SALE"),
    }
    color, label = cfg.get(weight_type, ("#64748b", weight_type.upper()))
    return (f"<span style='background:#0d1224;border:1px solid {color};"
            f"border-radius:20px;padding:3px 10px;font-size:0.72rem;"
            f"color:{color};font-family:Space Mono,monospace'>{label}</span>")


def _animal_options(company: str):
    animals = load_animals(company)
    lookup = {
        f"{a['animal_tag']} — {a.get('breed','')} ({a.get('species','')})": a
        for a in animals
    }
    return lookup, animals


def render_growth_feed_tracker(profile: dict):
    company = profile.get("company", "")
    role = profile.get("role", "")
    username = profile.get("username", "")

    st.markdown("# 📈 Growth & Feed Tracker")
    st.markdown(
        "<p style='color:#64748b'>Weight history, feed quantity logging, and "
        "cost-per-kg performance per animal</p>",
        unsafe_allow_html=True
    )

    animal_lookup, animals = _animal_options(company)
    animal_tags = [a["animal_tag"] for a in animals]

    tab_overview, tab_weight, tab_feed = st.tabs(
        ["📊 Performance Overview", "⚖️ Record Weight", "🌾 Record Feed"]
    )

    with tab_overview:
        if not animals:
            st.info("Register an animal first, then come back to log weight and feed.")
        else:
            adg_rows = get_performance_view("animal_adg", animal_tags)
            cost_rows = get_performance_view("animal_cost_per_kg_gained", animal_tags)
            fcr_rows = get_performance_view("animal_fcr", animal_tags)

            adg_by_tag = {r["animal_tag"]: r for r in adg_rows}
            cost_by_tag = {r["animal_tag"]: r for r in cost_rows}
            fcr_by_tag = {r["animal_tag"]: r for r in fcr_rows}

            tracked = len(adg_rows)
            total = len(animals)

            c1, c2, c3 = st.columns(3)
            c1.markdown(_metric_card("ANIMALS TRACKED", f"{tracked}/{total}", "#38bdf8"), unsafe_allow_html=True)

            avg_adg = None
            if adg_rows:
                valid_adg = [r["adg_kg_per_day"] for r in adg_rows if r.get("adg_kg_per_day") is not None]
                if valid_adg:
                    avg_adg = round(sum(valid_adg) / len(valid_adg), 3)
            c2.markdown(_metric_card("AVG DAILY GAIN", f"{avg_adg} kg/day" if avg_adg else "—", "#4ade80"), unsafe_allow_html=True)

            avg_cost = None
            if cost_rows:
                valid_cost = [r["cost_per_kg_gained_kes"] for r in cost_rows if r.get("cost_per_kg_gained_kes") is not None]
                if valid_cost:
                    avg_cost = round(sum(valid_cost) / len(valid_cost), 2)
            c3.markdown(_metric_card("AVG COST/KG GAINED", f"KES {avg_cost}" if avg_cost else "—", "#fbbf24"), unsafe_allow_html=True)

            st.caption("Cost figures pull from Cost of Production entries (animal_costs) — log costs there, not here.")

            st.markdown("---")
            st.markdown("<div class='section-header'>PER-ANIMAL PERFORMANCE</div>", unsafe_allow_html=True)

            if tracked == 0:
                st.info("No animals have weight records yet. Log a birth or periodic weight below.")
            else:
                table_rows = []
                for a in animals:
                    tag = a["animal_tag"]
                    adg = adg_by_tag.get(tag, {})
                    cost = cost_by_tag.get(tag, {})
                    fcr = fcr_by_tag.get(tag, {})
                    if not adg:
                        continue
                    table_rows.append({
                        "Tag": tag,
                        "Breed": a.get("breed", "—"),
                        "Birth (kg)": adg.get("birth_weight_kg"),
                        "Latest (kg)": adg.get("latest_weight_kg"),
                        "ADG (kg/day)": adg.get("adg_kg_per_day"),
                        "Total Cost (KES)": cost.get("total_cost_kes"),
                        "Cost/kg Gained (KES)": cost.get("cost_per_kg_gained_kes"),
                        "FCR": fcr.get("fcr"),
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
                st.caption("FCR only shown for animals with per-animal (not pen-level) feed logs.")

    with tab_weight:
        if role not in ALLOWED_ROLES:
            st.warning("🔒 Weight logging requires herdsman, farm_manager, diaspora_owner, or admin role.")
        elif not animals:
            st.info("Register an animal first before logging weight.")
        else:
            st.markdown("<div class='section-header'>RECORD WEIGHT</div>", unsafe_allow_html=True)

            with st.form("record_weight_form", clear_on_submit=True):
                selected_label = st.selectbox("Animal *", list(animal_lookup.keys()))
                selected_animal = animal_lookup[selected_label]

                col1, col2 = st.columns(2)
                with col1:
                    weight_type = st.selectbox("Weight Type *", WEIGHT_TYPES)
                with col2:
                    weigh_method = st.selectbox("Weigh Method *", WEIGH_METHODS, index=0)

                col3, col4 = st.columns(2)
                with col3:
                    weight_kg = st.number_input("Weight (kg) *", min_value=0.1, step=0.1, format="%.1f")
                with col4:
                    recorded_date = st.date_input("Date *", value=date.today(), max_value=date.today())

                notes = st.text_area("Notes", placeholder="Any observations at weighing...", height=70)

                submitted = st.form_submit_button("✅ Save Weight Record", use_container_width=True, type="primary")

            if submitted:
                record = {
                    "animal_tag": selected_animal["animal_tag"],
                    "weight_type": weight_type,
                    "weight_kg": weight_kg,
                    "weigh_method": weigh_method,
                    "recorded_date": recorded_date.isoformat(),
                    "recorded_by": username,
                    "notes": notes.strip() or None,
                }
                if save_growth_record(record):
                    st.success(f"✅ {weight_type.title()} weight of {weight_kg} kg saved for **{selected_animal['animal_tag']}**.")
                    st.rerun()

            st.markdown("---")
            st.markdown("<div class='section-header'>WEIGHT HISTORY</div>", unsafe_allow_html=True)
            history_label = st.selectbox("View history for", list(animal_lookup.keys()), key="history_select")
            history_animal = animal_lookup[history_label]
            history = get_growth_history(history_animal["animal_tag"])

            if not history:
                st.caption("No weight records yet for this animal.")
            else:
                for h in history:
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;align-items:center;"
                        f"padding:8px 0;border-bottom:1px solid #1e293b'>"
                        f"<div>{_weight_badge(h['weight_type'])} "
                        f"<span style='color:#e8eaf0;margin-left:8px'>{h['weight_kg']} kg</span> "
                        f"<span style='color:#475569;font-size:0.78rem'>({h['weigh_method']})</span></div>"
                        f"<div style='color:#64748b;font-size:0.78rem'>{h['recorded_date']}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    with tab_feed:
        if role not in ALLOWED_ROLES:
            st.warning("🔒 Feed logging requires herdsman, farm_manager, diaspora_owner, or admin role.")
        elif not animals:
            st.info("Register an animal first before logging feed.")
        else:
            st.markdown("<div class='section-header'>RECORD FEED (QUANTITY ONLY)</div>", unsafe_allow_html=True)
            st.caption("To log the COST of this feed, use the Cost of Production page instead — this only tracks kg fed, for FCR calculation.")

            log_scope = st.radio(
                "Log for", ["Individual animal", "Pen / group"], horizontal=True
            )

            with st.form("record_feed_form", clear_on_submit=True):
                selected_animal = None
                pen_id = None

                if log_scope == "Individual animal":
                    selected_label = st.selectbox("Animal *", list(animal_lookup.keys()))
                    selected_animal = animal_lookup[selected_label]
                else:
                    pen_id = st.text_input("Pen / Group ID *", placeholder="e.g. Pen-A")
                    st.caption("Pen-level feed logs quantity only — FCR isn't computed for pen-level entries yet.")

                col1, col2 = st.columns(2)
                with col1:
                    feed_type = st.selectbox("Feed Type *", FEED_TYPES)
                with col2:
                    quantity_kg = st.number_input("Quantity (kg) *", min_value=0.1, step=0.5, format="%.1f")

                recorded_date = st.date_input("Date *", value=date.today(), max_value=date.today())

                submitted = st.form_submit_button("✅ Save Feed Record", use_container_width=True, type="primary")

            if submitted:
                if log_scope == "Pen / group" and not pen_id:
                    st.error("Pen / Group ID is required for pen-level logging.")
                else:
                    feed_record = {
                        "animal_tag": selected_animal["animal_tag"] if log_scope == "Individual animal" else None,
                        "pen_id": pen_id if log_scope == "Pen / group" else None,
                        "feed_type": feed_type,
                        "quantity_kg": quantity_kg,
                        "allocation_method": "per_animal" if log_scope == "Individual animal" else "per_pen_by_headcount",
                        "recorded_date": recorded_date.isoformat(),
                        "recorded_by": username,
                    }
                    if save_feed_record(feed_record):
                        target = selected_animal["animal_tag"] if log_scope == "Individual animal" else pen_id
                        st.success(f"✅ {quantity_kg}kg of {feed_type} logged for **{target}**.")
                        st.rerun()
