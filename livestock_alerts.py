import streamlit as st
import urllib.parse
from datetime import datetime, timezone
from supabase_db import get_supabase_client

# ── SQL (run once in Supabase):
# CREATE TABLE IF NOT EXISTS alert_log (
#     id            SERIAL PRIMARY KEY,
#     animal_tag    TEXT NOT NULL,
#     company       TEXT NOT NULL,
#     triggered_by  TEXT NOT NULL,
#     triggered_at  TIMESTAMPTZ DEFAULT NOW(),
#     alert_type    TEXT,
#     status        TEXT,
#     temp_celsius  NUMERIC(4,1),
#     health_status TEXT,
#     owner_phone   TEXT,
#     vet_phone     TEXT,
#     message_sent  TEXT,
#     notes         TEXT
# );
#
# ALTER TABLE animals ADD COLUMN IF NOT EXISTS owner_phone TEXT;
# ALTER TABLE animals ADD COLUMN IF NOT EXISTS vet_phone   TEXT;
# ALTER TABLE animals ADD COLUMN IF NOT EXISTS vet_name    TEXT;

def _client():
    return get_supabase_client()

def _build_owner_message(animal: dict, temp: float | None,
                          trigger: str, extra: str = "") -> str:
    tag     = animal.get("animal_tag","—")
    species = animal.get("species","Animal")
    breed   = animal.get("breed","—")
    county  = animal.get("county","—")
    farm    = animal.get("farm_location","—")
    now     = datetime.now().strftime("%d %b %Y %H:%M")
    temp_line = f"🌡 Temperature: *{temp}°C*\n" if temp else ""
    return (
        f"🚨 *VeriPath Health Alert*\n\n"
        f"Your animal needs attention:\n\n"
        f"🏷 Tag: *{tag}*\n"
        f"🐾 Animal: *{species} — {breed}*\n"
        f"📍 Location: *{farm}, {county}*\n"
        f"{temp_line}"
        f"⚠️ Status: *{trigger}*\n"
        f"{('📋 Notes: ' + extra + chr(10)) if extra else ''}"
        f"⏰ Logged: {now}\n\n"
        f"Please contact your veterinarian immediately.\n"
        f"_Powered by VeriPath Africa — veripath.co.ke_"
    )

def _build_vet_message(animal: dict, owner_name: str,
                        temp: float | None, trigger: str,
                        symptoms: list[str]) -> str:
    tag     = animal.get("animal_tag","—")
    species = animal.get("species","Animal")
    breed   = animal.get("breed","—")
    county  = animal.get("county","—")
    farm    = animal.get("farm_location","—")
    now     = datetime.now().strftime("%d %b %Y %H:%M")
    temp_line = f"🌡 Temperature: *{temp}°C*\n" if temp else ""
    sym_line  = (f"📋 Symptoms: {', '.join(symptoms)}\n") if symptoms else ""
    return (
        f"🩺 *VeriPath Vet Dispatch*\n\n"
        f"Clinical attention required:\n\n"
        f"🏷 Tag: *{tag}*\n"
        f"🐾 Animal: *{species} — {breed}*\n"
        f"👤 Owner: *{owner_name}*\n"
        f"📍 Location: *{farm}, {county}*\n"
        f"{temp_line}"
        f"{sym_line}"
        f"⚠️ Trigger: *{trigger}*\n"
        f"⏰ Time: {now}\n\n"
        f"Please attend within the recommended window.\n"
        f"_VeriPath Africa — Livestock Intelligence_"
    )

def _whatsapp_link(phone: str, message: str) -> str:
    clean = phone.strip().replace(" ","").replace("-","").replace("+","")
    if not clean.startswith("254"):
        clean = "254" + clean.lstrip("0")
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean}?text={encoded}"

def log_alert(record: dict) -> bool:
    try:
        _client().table("alert_log").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to log alert: {e}")
        return False

def load_alert_log(company: str, limit: int = 30) -> list[dict]:
    try:
        res = (_client().table("alert_log")
               .select("*")
               .eq("company", company)
               .order("triggered_at", desc=True)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception:
        return []

def fire_red_alert(
    animal: dict,
    triggered_by: str,
    company: str,
    temp: float | None = None,
    trigger_reason: str = "RED health status",
    symptoms: list[str] | None = None,
    extra_notes: str = "",
):
    """
    Core alert function — call this from any module when RED is detected.
    Renders WhatsApp buttons inline. Logs to alert_log table.
    """
    symptoms = symptoms or []

    owner_phone = animal.get("owner_phone","")
    vet_phone   = animal.get("vet_phone","")
    vet_name    = animal.get("vet_name","Veterinarian")
    owner_name  = animal.get("owner_username","Owner")

    owner_msg = _build_owner_message(animal, temp, trigger_reason, extra_notes)
    vet_msg   = _build_vet_message(animal, owner_name, temp, trigger_reason, symptoms)

    st.markdown(f"""
    <div style='background:#1a0a0a;border:2px solid #dc2626;
                border-radius:14px;padding:20px 24px;margin:16px 0'>
        <div style='font-family:Space Mono,monospace;color:#dc2626;
                    font-size:1rem;font-weight:700;margin-bottom:12px'>
            🚨 RED ALERT — {animal.get("animal_tag","—")}
        </div>
        <div style='color:#94a3b8;font-size:0.85rem;line-height:1.6'>
            Trigger: {trigger_reason}<br>
            {"Temp: " + str(temp) + "°C<br>" if temp else ""}
            {"Symptoms: " + ", ".join(symptoms) + "<br>" if symptoms else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📲 Notify Owner**")
        if owner_phone:
            link = _whatsapp_link(owner_phone, owner_msg)
            st.markdown(f"""
            <a href='{link}' target='_blank' style='
                display:block;background:#075e54;color:white;
                text-align:center;padding:12px;border-radius:10px;
                font-family:Space Mono,monospace;font-size:0.85rem;
                text-decoration:none;font-weight:700;
                border:1px solid #25d366;margin-top:6px'>
                💬 WhatsApp Owner
            </a>
            """, unsafe_allow_html=True)
        else:
            st.warning("No owner phone on file.")
            st.caption("Add owner phone in Animal Registry.")

    with col2:
        st.markdown("**🩺 Dispatch Vet**")
        if vet_phone:
            link = _whatsapp_link(vet_phone, vet_msg)
            st.markdown(f"""
            <a href='{link}' target='_blank' style='
                display:block;background:#1a3a5c;color:white;
                text-align:center;padding:12px;border-radius:10px;
                font-family:Space Mono,monospace;font-size:0.85rem;
                text-decoration:none;font-weight:700;
                border:1px solid #38bdf8;margin-top:6px'>
                🩺 WhatsApp Vet ({vet_name})
            </a>
            """, unsafe_allow_html=True)
        else:
            st.warning("No vet phone on file.")
            st.caption("Add vet phone in Animal Registry.")

    # Log alert
    log_alert({
        "animal_tag":   animal.get("animal_tag","—"),
        "company":      company,
        "triggered_by": triggered_by,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "alert_type":   "RED_HEALTH",
        "status":       "fired",
        "temp_celsius": temp,
        "health_status":"RED",
        "owner_phone":  owner_phone or None,
        "vet_phone":    vet_phone or None,
        "message_sent": owner_msg,
        "notes":        extra_notes or None,
    })

def render_alert_centre(profile: dict):
    company  = profile.get("company","")
    username = profile.get("username","")
    role     = profile.get("role","")

    st.markdown("# 🚨 Alert Centre")
    st.markdown(
        "<p style='color:#64748b'>RED alerts · WhatsApp dispatch · alert history</p>",
        unsafe_allow_html=True
    )

    tab_fire, tab_log = st.tabs(["⚡ Fire Alert", "📋 Alert Log"])

    # ── TAB 1: Fire Alert ──────────────────────────────────────────────────
    with tab_fire:
        if role not in ("admin","farm_manager","veterinarian"):
            st.warning("🔒 Alert dispatch requires veterinarian or farm_manager role.")
            return

        try:
            res = (_client().table("animals")
                   .select("*")
                   .eq("company", company)
                   .eq("status","active")
                   .execute())
            animals = res.data or []
        except Exception:
            animals = []

        if not animals:
            st.info("No animals registered yet.")
            return

        # RED animals first
        red_first = (
            [a for a in animals if a.get("health_status") == "RED"] +
            [a for a in animals if a.get("health_status") != "RED"]
        )
        options = {
            f"{'🚨 ' if a.get('health_status')=='RED' else ''}"
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in red_first
        }

        selected_label  = st.selectbox("Select animal", list(options.keys()))
        selected_animal = options[selected_label]

        st.markdown("---")

        # Phone numbers — editable inline if missing
        col1, col2 = st.columns(2)
        with col1:
            owner_phone = st.text_input(
                "Owner WhatsApp (with country code)",
                value=selected_animal.get("owner_phone",""),
                placeholder="e.g. 0712345678"
            )
        with col2:
            vet_phone = st.text_input(
                "Vet WhatsApp (with country code)",
                value=selected_animal.get("vet_phone",""),
                placeholder="e.g. 0722345678"
            )

        # Save phones back to animal record if entered
        if owner_phone or vet_phone:
            update_payload = {}
            if owner_phone: update_payload["owner_phone"] = owner_phone.strip()
            if vet_phone:   update_payload["vet_phone"]   = vet_phone.strip()
            if update_payload:
                try:
                    _client().table("animals").update(update_payload).eq(
                        "animal_tag", selected_animal["animal_tag"]
                    ).execute()
                    selected_animal.update(update_payload)
                except Exception:
                    pass

        temp = st.number_input("Current temperature (°C) — optional",
                               min_value=0.0, max_value=45.0,
                               value=0.0, step=0.1, format="%.1f")
        trigger_reason = st.text_input(
            "Trigger reason",
            value="RED health status — pathological fever confirmed"
        )
        extra_notes = st.text_area("Extra notes for messages", height=80)

        st.markdown("---")
        if st.button("🚨 Fire Alert Now", use_container_width=True, type="primary"):
            fire_red_alert(
                animal         = selected_animal,
                triggered_by   = username,
                company        = company,
                temp           = temp if temp > 0 else None,
                trigger_reason = trigger_reason,
                extra_notes    = extra_notes,
            )

    # ── TAB 2: Alert Log ───────────────────────────────────────────────────
    with tab_log:
        st.markdown("<div class='section-header'>ALERT HISTORY</div>",
                    unsafe_allow_html=True)
        logs = load_alert_log(company)
        if not logs:
            st.info("No alerts fired yet.")
            return

        for log in logs:
            fired_at = log.get("triggered_at","")[:16].replace("T"," ")
            st.markdown(f"""
            <div style='background:#1a0a0a;border:1px solid #dc2626;
                        border-radius:12px;padding:14px 18px;margin-bottom:10px'>
                <div style='display:flex;justify-content:space-between'>
                    <div style='font-family:Space Mono,monospace;
                                color:#dc2626;font-weight:700'>
                        🚨 {log.get("animal_tag","—")}
                    </div>
                    <div style='color:#64748b;font-size:0.75rem'>{fired_at}</div>
                </div>
                <div style='color:#94a3b8;font-size:0.8rem;margin-top:4px'>
                    {"🌡 " + str(log.get("temp_celsius","")) + "°C · " if log.get("temp_celsius") else ""}
                    Fired by: {log.get("triggered_by","—")}
                </div>
                <div style='color:#64748b;font-size:0.75rem;margin-top:2px'>
                    Owner: {log.get("owner_phone","—")} ·
                    Vet: {log.get("vet_phone","—")}
                </div>
            </div>
            """, unsafe_allow_html=True)
