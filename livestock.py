import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone
from supabase_db import get_supabase_client

# ── Helpers ────────────────────────────────────────────────────────────────
def _client():
    return get_supabase_client()

def _next_tag(company: str) -> str:
    """Generate next VP-LIV-XXXX tag for this company."""
    try:
        res = (_client().table("animals")
               .select("animal_tag")
               .eq("company", company)
               .execute())
        existing = [r["animal_tag"] for r in (res.data or [])]
        nums = []
        for tag in existing:
            parts = tag.split("-")
            if len(parts) == 3 and parts[2].isdigit():
                nums.append(int(parts[2]))
        next_num = (max(nums) + 1) if nums else 1
        return f"VP-LIV-{next_num:04d}"
    except Exception:
        import secrets
        return f"VP-LIV-{secrets.token_hex(2).upper()}"

def _age_months(birth_date: date) -> int:
    today = date.today()
    return (today.year - birth_date.year) * 12 + (today.month - birth_date.month)

def load_animals(company: str) -> list[dict]:
    try:
        res = (_client().table("animals")
               .select("*")
               .eq("company", company)
               .eq("status", "active")
               .order("registered_at", desc=True)
               .execute())
        return res.data or []
    except Exception as e:
        st.error(f"Failed to load animals: {e}")
        return []

def save_animal(record: dict) -> bool:
    try:
        _client().table("animals").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save animal: {e}")
        return False

# ── Species config ─────────────────────────────────────────────────────────
SPECIES_CONFIG = {
    "Goat": {
        "breeds": ["Galla", "Boer", "Toggenburg", "Alpine", "Nubian",
                   "Small East African", "Dorper cross", "Other"],
        "temp_normal": (38.5, 40.0),
        "temp_mild":   40.2,
        "temp_sig":    40.5,
        "temp_emerg":  41.5,
        "icon": "🐐",
    },
    "Cattle": {
        "breeds": ["Boran", "Sahiwal", "Friesian", "Ayrshire", "Zebu",
                   "Angus cross", "Simmental cross", "Other"],
        "temp_normal": (38.0, 39.3),
        "temp_mild":   39.5,
        "temp_sig":    39.8,
        "temp_emerg":  40.5,
        "icon": "🐄",
    },
    "Sheep": {
        "breeds": ["Dorper", "Red Maasai", "Merino", "Hampshire", "Other"],
        "temp_normal": (38.5, 39.5),
        "temp_mild":   39.8,
        "temp_sig":    40.0,
        "temp_emerg":  41.0,
        "icon": "🐑",
    },
}

SEX_OPTIONS      = ["Male", "Female", "Castrated Male"]
COAT_OPTIONS     = ["Brown", "Black", "White", "Black & White", "Brown & White",
                    "Tan", "Grey", "Spotted", "Other"]
COUNTY_OPTIONS   = [
    "Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa",
    "Homa Bay","Isiolo","Kajiado","Kakamega","Kericho","Kiambu","Kilifi",
    "Kirinyaga","Kisii","Kisumu","Kitui","Kwale","Laikipia","Lamu","Machakos",
    "Makueni","Mandera","Marsabit","Meru","Migori","Mombasa","Murang'a",
    "Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri",
    "Samburu","Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia",
    "Turkana","Uasin Gishu","Vihiga","Wajir","West Pokot"
]

# ── Status badge HTML ───────────────────────────────────────────────────────
def _status_badge(status: str) -> str:
    cfg = {
        "GREEN":  ("#16a34a", "#071a0f", "● HEALTHY"),
        "YELLOW": ("#d97706", "#1a0f00", "● HEAT STRESS"),
        "RED":    ("#dc2626", "#1a0a0a", "● ALERT"),
        "active": ("#38bdf8", "#0f2233", "ACTIVE"),
    }
    color, bg, label = cfg.get(status, ("#64748b","#0d1224", status.upper()))
    return (f"<span style='background:{bg};border:1px solid {color};"
            f"border-radius:20px;padding:3px 10px;font-size:0.72rem;"
            f"color:{color};font-family:Space Mono,monospace'>{label}</span>")

# ── Animal card HTML ────────────────────────────────────────────────────────
def _animal_card(a: dict) -> str:
    species  = a.get("species","")
    icon     = SPECIES_CONFIG.get(species, {}).get("icon","🐾")
    age      = _age_months(date.fromisoformat(a["birth_date"])) if a.get("birth_date") else a.get("age_months","?")
    hw_badge = ""
    if a.get("collar_id"):
        hw_badge = "<span style='color:#38bdf8;font-size:0.7rem'>📡 COLLAR</span> "
    if a.get("bolus_id"):
        hw_badge += "<span style='color:#a78bfa;font-size:0.7rem'>💊 BOLUS</span>"
    return f"""
    <div style='background:linear-gradient(135deg,#111827,#1a2540);
                border:1px solid #1e3a5f;border-radius:14px;
                padding:18px 20px;margin-bottom:12px;
                transition:border-color 0.2s'>
        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
            <div>
                <div style='font-family:Space Mono,monospace;font-size:1rem;
                            color:#38bdf8;font-weight:700'>
                    {icon} {a.get("animal_tag","—")}
                </div>
                <div style='color:#e8eaf0;margin-top:4px;font-size:0.9rem'>
                    {a.get("breed","—")} · {a.get("sex","—")} · {a.get("coat_color","—")}
                </div>
                <div style='color:#64748b;font-size:0.78rem;margin-top:2px'>
                    {age} months old · {a.get("county","—")}
                </div>
                <div style='margin-top:6px'>{hw_badge}</div>
            </div>
            <div>{_status_badge(a.get("health_status","active"))}</div>
        </div>
    </div>
    """

# ── Main render function ───────────────────────────────────────────────────
def render_animal_registry(profile: dict):
    company  = profile.get("company","")
    role     = profile.get("role","")
    username = profile.get("username","")

    st.markdown("# 🐄 Animal Registry")
    st.markdown("<p style='color:#64748b'>VP-LIV tagged livestock — breed, health, hardware</p>",
                unsafe_allow_html=True)

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_list, tab_reg = st.tabs(["📋 Animal List", "➕ Register Animal"])

    # ── TAB 1: Animal List ─────────────────────────────────────────────────
    with tab_list:
        animals = load_animals(company)
        if not animals:
            st.markdown("""
            <div style='background:#0d1224;border:1px dashed #1e3a5f;border-radius:12px;
                        padding:40px;text-align:center;margin-top:20px'>
                <div style='font-size:2rem'>🐄</div>
                <div style='color:#64748b;margin-top:8px'>No animals registered yet.</div>
                <div style='color:#475569;font-size:0.8rem;margin-top:4px'>
                    Use the Register Animal tab to add your first animal.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Summary metrics
            total    = len(animals)
            cattle   = sum(1 for a in animals if a.get("species") == "Cattle")
            goats    = sum(1 for a in animals if a.get("species") == "Goat")
            collared = sum(1 for a in animals if a.get("collar_id"))

            c1, c2, c3, c4 = st.columns(4)
            for col, label, val, color in [
                (c1, "TOTAL ANIMALS",  total,    "#38bdf8"),
                (c2, "CATTLE",         cattle,   "#4ade80"),
                (c3, "GOATS",          goats,    "#fbbf24"),
                (c4, "COLLARED",       collared, "#a78bfa"),
            ]:
                col.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>{label}</div>
                    <div class='metric-value' style='color:{color}'>{val}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # Filters
            col_f1, col_f2 = st.columns(2)
            species_filter = col_f1.multiselect(
                "Filter by species",
                options=list(SPECIES_CONFIG.keys()),
                default=[]
            )
            sex_filter = col_f2.multiselect(
                "Filter by sex",
                options=SEX_OPTIONS,
                default=[]
            )
            filtered = animals
            if species_filter:
                filtered = [a for a in filtered if a.get("species") in species_filter]
            if sex_filter:
                filtered = [a for a in filtered if a.get("sex") in sex_filter]

            st.markdown(f"<div class='section-header'>HERD — {len(filtered)} ANIMALS</div>",
                        unsafe_allow_html=True)

            for a in filtered:
                st.markdown(_animal_card(a), unsafe_allow_html=True)

            # Export
            if st.button("⬇ Export Registry CSV"):
                df_exp = pd.DataFrame(filtered)
                st.download_button(
                    "Download CSV",
                    data=df_exp.to_csv(index=False).encode("utf-8"),
                    file_name=f"veripath_animals_{date.today()}.csv",
                    mime="text/csv"
                )

    # ── TAB 2: Register Animal ─────────────────────────────────────────────
    with tab_reg:
        if role not in ("admin", "farm_manager", "veterinarian", "herdsman"):
            st.warning("🔒 Registration requires farm_manager, veterinarian, or admin role.")
            return

        st.markdown("<div class='section-header'>REGISTER NEW ANIMAL</div>",
                    unsafe_allow_html=True)

        next_tag = _next_tag(company)
        st.markdown(f"""
        <div style='background:#0f2233;border:1px solid #1e3a5f;border-radius:10px;
                    padding:12px 18px;margin-bottom:20px;display:inline-block'>
            <span style='color:#64748b;font-size:0.75rem;font-family:Space Mono,monospace'>
                NEXT TAG
            </span><br>
            <span style='color:#38bdf8;font-size:1.3rem;font-weight:700;
                         font-family:Space Mono,monospace'>{next_tag}</span>
        </div>
        """, unsafe_allow_html=True)

        with st.form("register_animal_form", clear_on_submit=True):
            st.markdown("**Species & Breed**")
            col1, col2 = st.columns(2)
            with col1:
                species = st.selectbox("Species *", list(SPECIES_CONFIG.keys()))
            with col2:
                breed = st.selectbox("Breed *", SPECIES_CONFIG[species]["breeds"])

            st.markdown("**Animal Details**")
            col3, col4, col5 = st.columns(3)
            with col3:
                sex = st.selectbox("Sex *", SEX_OPTIONS)
            with col4:
                coat_color = st.selectbox("Coat Color *", COAT_OPTIONS)
            with col5:
                birth_date = st.date_input(
                    "Birth Date *",
                    value=date(2023, 1, 1),
                    min_value=date(2010, 1, 1),
                    max_value=date.today()
                )

            st.markdown("**Location**")
            col6, col7 = st.columns(2)
            with col6:
                county = st.selectbox("County *", COUNTY_OPTIONS)
            with col7:
                farm_location = st.text_input("Farm / Boma Name", placeholder="e.g. Memusi Farm Block A")

            st.markdown("**Hardware (optional)**")
            col8, col9 = st.columns(2)
            with col8:
                collar_id = st.text_input("Collar ID", placeholder="e.g. COL-001")
            with col9:
                bolus_id  = st.text_input("Rumen Bolus ID", placeholder="e.g. BOL-001")

            notes = st.text_area("Notes", placeholder="Any observations at registration...", height=80)

            submitted = st.form_submit_button("✅ Register Animal", use_container_width=True, type="primary")

        if submitted:
            age = _age_months(birth_date)
            hw_status = "none"
            if collar_id and bolus_id: hw_status = "collar+bolus"
            elif collar_id:            hw_status = "collar"
            elif bolus_id:             hw_status = "bolus"

            record = {
                "animal_tag":     next_tag,
                "company":        company,
                "owner_username": username,
                "species":        species,
                "breed":          breed,
                "sex":            sex,
                "coat_color":     coat_color,
                "birth_date":     birth_date.isoformat(),
                "age_months":     age,
                "farm_location":  farm_location.strip(),
                "county":         county,
                "status":         "active",
                "collar_id":      collar_id.strip() or None,
                "bolus_id":       bolus_id.strip() or None,
                "hardware_status":hw_status,
                "registered_by":  username,
                "registered_at":  datetime.now(timezone.utc).isoformat(),
                "notes":          notes.strip() or None,
            }
            if save_animal(record):
                st.success(f"✅ {species} registered as **{next_tag}** — {age} months old.")
                st.balloons()
                st.rerun()
