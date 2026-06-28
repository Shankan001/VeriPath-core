import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_supabase_client

# ── SQL (run once in Supabase):
# CREATE TABLE IF NOT EXISTS hardware_registry (
#     id             SERIAL PRIMARY KEY,
#     company        TEXT NOT NULL,
#     hardware_type  TEXT NOT NULL,
#     hardware_id    TEXT NOT NULL,
#     animal_tag     TEXT,
#     assigned_at    TIMESTAMPTZ,
#     assigned_by    TEXT,
#     status         TEXT DEFAULT 'unassigned',
#     battery_pct    INTEGER,
#     firmware_ver   TEXT,
#     purchase_date  DATE,
#     price_kes      NUMERIC(10,2),
#     notes          TEXT,
#     created_at     TIMESTAMPTZ DEFAULT NOW()
# );

def _client():
    return get_supabase_client()

HARDWARE_TYPES = {
    "VP-COL": {
        "name":        "VP-LIV Collar",
        "icon":        "📡",
        "color":       "#38bdf8",
        "bg":          "#0f2233",
        "price_kes":   3500,
        "description": "LED ear tag collar — GREEN/YELLOW/RED health indicator",
    },
    "VP-BOL": {
        "name":        "Ceramic Rumen Bolus",
        "icon":        "💊",
        "color":       "#a78bfa",
        "bg":          "#1a0f2e",
        "price_kes":   2500,
        "description": "Internal temperature sensor — continuous monitoring",
    },
}

STATUS_OPTIONS = ["unassigned", "assigned", "faulty", "returned", "lost"]

def load_hardware(company: str) -> list[dict]:
    try:
        res = (_client().table("hardware_registry")
               .select("*")
               .eq("company", company)
               .order("created_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

def save_hardware(record: dict) -> bool:
    try:
        _client().table("hardware_registry").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save hardware: {e}")
        return False

def assign_hardware(hardware_id: str, animal_tag: str,
                    assigned_by: str, hw_type: str) -> bool:
    try:
        now = datetime.now(timezone.utc).isoformat()
        _client().table("hardware_registry").update({
            "animal_tag":  animal_tag,
            "assigned_at": now,
            "assigned_by": assigned_by,
            "status":      "assigned",
        }).eq("hardware_id", hardware_id).execute()

        # Update animal record
        field = "collar_id" if hw_type == "VP-COL" else "bolus_id"
        hw_status_map = {
            "VP-COL": "collar",
            "VP-BOL": "bolus",
        }
        _client().table("animals").update({
            field: hardware_id,
            "hardware_status": hw_status_map.get(hw_type, "collar"),
        }).eq("animal_tag", animal_tag).execute()
        return True
    except Exception as e:
        st.error(f"Assignment failed: {e}")
        return False

def _hw_card(hw: dict) -> str:
    hw_type = hw.get("hardware_type","VP-COL")
    cfg     = HARDWARE_TYPES.get(hw_type, HARDWARE_TYPES["VP-COL"])
    status  = hw.get("status","unassigned")
    s_color = {
        "assigned":   "#16a34a",
        "unassigned": "#64748b",
        "faulty":     "#dc2626",
        "returned":   "#d97706",
        "lost":       "#7c3aed",
    }.get(status, "#64748b")

    battery = hw.get("battery_pct")
    bat_str = f"🔋 {battery}%" if battery is not None else ""
    animal  = hw.get("animal_tag","—") if status == "assigned" else "Unassigned"

    return f"""
    <div style='background:{cfg["bg"]};border:1px solid {cfg["color"]};
                border-radius:14px;padding:16px 20px;margin-bottom:10px'>
        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
            <div>
                <div style='font-family:Space Mono,monospace;
                            color:{cfg["color"]};font-size:0.95rem;font-weight:700'>
                    {cfg["icon"]} {hw.get("hardware_id","—")}
                </div>
                <div style='color:#e8eaf0;font-size:0.82rem;margin-top:4px'>
                    {cfg["name"]}
                </div>
                <div style='color:#64748b;font-size:0.75rem;margin-top:2px'>
                    Animal: <span style='color:#94a3b8'>{animal}</span>
                    {"  " + bat_str if bat_str else ""}
                </div>
                {f"<div style='color:#64748b;font-size:0.72rem;margin-top:2px'>FW: {hw.get('firmware_ver','—')}</div>" if hw.get("firmware_ver") else ""}
            </div>
            <div style='text-align:right'>
                <div style='font-family:Space Mono,monospace;
                            color:{s_color};font-size:0.78rem;font-weight:700'>
                    {status.upper()}
                </div>
                <div style='color:#64748b;font-size:0.72rem;margin-top:4px'>
                    KES {float(hw.get("price_kes",0)):,.0f}
                </div>
            </div>
        </div>
    </div>
    """

def render_hardware_registry(profile: dict):
    company  = profile.get("company","")
    username = profile.get("username","")
    role     = profile.get("role","")

    if role not in ("admin","farm_manager","veterinarian"):
        st.warning("🔒 Hardware registry requires farm_manager or admin role.")
        return

    st.markdown("# 🔧 Hardware Registry")
    st.markdown(
        "<p style='color:#64748b'>VP-LIV collars · rumen boluses · assignment tracking</p>",
        unsafe_allow_html=True
    )

    hardware = load_hardware(company)

    # ── KPI strip ──────────────────────────────────────────────────────────
    total      = len(hardware)
    assigned   = sum(1 for h in hardware if h.get("status") == "assigned")
    unassigned = sum(1 for h in hardware if h.get("status") == "unassigned")
    faulty     = sum(1 for h in hardware if h.get("status") == "faulty")
    collars    = sum(1 for h in hardware if h.get("hardware_type") == "VP-COL")
    boluses    = sum(1 for h in hardware if h.get("hardware_type") == "VP-BOL")
    total_value= sum(float(h.get("price_kes",0)) for h in hardware)

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>TOTAL UNITS</div>
        <div class='metric-value'>{total}</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>📡 COLLARS / 💊 BOLUSES</div>
        <div class='metric-value' style='color:#38bdf8'>{collars} / {boluses}</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>ASSIGNED / FREE</div>
        <div class='metric-value' style='color:#16a34a'>{assigned} / {unassigned}</div>
    </div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>FLEET VALUE</div>
        <div class='metric-value' style='font-size:1.3rem'>
            KES {total_value:,.0f}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    tab_list, tab_add, tab_assign = st.tabs([
        "📋 Hardware List", "➕ Add Hardware", "🔗 Assign to Animal"
    ])

    # ── TAB 1: List ────────────────────────────────────────────────────────
    with tab_list:
        if not hardware:
            st.markdown("""
            <div style='background:#0d1224;border:1px dashed #1e3a5f;
                        border-radius:12px;padding:40px;text-align:center'>
                <div style='font-size:2rem'>🔧</div>
                <div style='color:#64748b;margin-top:8px'>
                    No hardware registered yet.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            col_f1, col_f2 = st.columns(2)
            type_filter   = col_f1.multiselect(
                "Type", ["VP-COL","VP-BOL"], default=[]
            )
            status_filter = col_f2.multiselect(
                "Status", STATUS_OPTIONS, default=[]
            )
            filtered = hardware
            if type_filter:
                filtered = [h for h in filtered
                            if h.get("hardware_type") in type_filter]
            if status_filter:
                filtered = [h for h in filtered
                            if h.get("status") in status_filter]

            st.markdown(
                f"<div class='section-header'>{len(filtered)} UNITS</div>",
                unsafe_allow_html=True
            )
            for hw in filtered:
                st.markdown(_hw_card(hw), unsafe_allow_html=True)

            if faulty:
                st.warning(f"⚠️ {faulty} unit(s) marked faulty — schedule replacement.")

    # ── TAB 2: Add Hardware ────────────────────────────────────────────────
    with tab_add:
        st.markdown("<div class='section-header'>REGISTER NEW UNIT</div>",
                    unsafe_allow_html=True)

        with st.form("add_hardware_form"):
            col1, col2 = st.columns(2)
            with col1:
                hw_type    = st.selectbox(
                    "Hardware type *",
                    list(HARDWARE_TYPES.keys()),
                    format_func=lambda k: f"{HARDWARE_TYPES[k]['icon']} {HARDWARE_TYPES[k]['name']}"
                )
                hw_id      = st.text_input(
                    "Hardware ID *",
                    placeholder="e.g. COL-001 or BOL-001"
                )
            with col2:
                battery    = st.number_input("Battery %", min_value=0,
                                             max_value=100, value=100)
                firmware   = st.text_input("Firmware version",
                                           placeholder="e.g. v1.2.0")

            col3, col4 = st.columns(2)
            with col3:
                purchase_date = st.date_input("Purchase date", value=date.today())
            with col4:
                price = st.number_input(
                    "Price (KES)",
                    min_value=0.0,
                    value=float(HARDWARE_TYPES.get(
                        "VP-COL",{}
                    ).get("price_kes",3500)),
                    step=100.0
                )

            notes = st.text_input("Notes", placeholder="Serial, supplier, warranty...")
            sub   = st.form_submit_button(
                "➕ Register Unit", use_container_width=True, type="primary"
            )

        if sub:
            if not hw_id.strip():
                st.error("❌ Hardware ID is required.")
            else:
                record = {
                    "company":       company,
                    "hardware_type": hw_type,
                    "hardware_id":   hw_id.strip().upper(),
                    "animal_tag":    None,
                    "assigned_at":   None,
                    "assigned_by":   None,
                    "status":        "unassigned",
                    "battery_pct":   battery,
                    "firmware_ver":  firmware.strip() or None,
                    "purchase_date": purchase_date.isoformat(),
                    "price_kes":     price,
                    "notes":         notes.strip() or None,
                    "created_at":    datetime.now(timezone.utc).isoformat(),
                }
                if save_hardware(record):
                    st.success(
                        f"✅ {HARDWARE_TYPES[hw_type]['name']} "
                        f"{hw_id.upper()} registered."
                    )
                    st.rerun()

    # ── TAB 3: Assign ──────────────────────────────────────────────────────
    with tab_assign:
        st.markdown("<div class='section-header'>ASSIGN UNIT TO ANIMAL</div>",
                    unsafe_allow_html=True)

        free_hw = [h for h in hardware if h.get("status") == "unassigned"]
        if not free_hw:
            st.info("No unassigned hardware available. Add units first.")
            return

        try:
            res = (_client().table("animals")
                   .select("animal_tag, species, breed")
                   .eq("company", company)
                   .eq("status","active")
                   .execute())
            animals = res.data or []
        except Exception:
            animals = []

        if not animals:
            st.info("No animals registered yet.")
            return

        hw_options = {
            f"{HARDWARE_TYPES.get(h['hardware_type'],{}).get('icon','🔧')} "
            f"{h['hardware_id']} — "
            f"{HARDWARE_TYPES.get(h['hardware_type'],{}).get('name','')}": h
            for h in free_hw
        }
        animal_options = {
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in animals
        }

        with st.form("assign_form"):
            sel_hw_label  = st.selectbox("Hardware unit *", list(hw_options.keys()))
            sel_ani_label = st.selectbox("Animal *", list(animal_options.keys()))
            sub_assign    = st.form_submit_button(
                "🔗 Assign Now", use_container_width=True, type="primary"
            )

        if sub_assign:
            sel_hw  = hw_options[sel_hw_label]
            sel_ani = animal_options[sel_ani_label]
            if assign_hardware(
                sel_hw["hardware_id"],
                sel_ani["animal_tag"],
                username,
                sel_hw["hardware_type"]
            ):
                st.success(
                    f"✅ {sel_hw['hardware_id']} assigned to "
                    f"{sel_ani['animal_tag']}."
                )
                st.rerun()
