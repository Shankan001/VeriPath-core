import streamlit as st
import pandas as pd
import datetime
import re
import os
from dotenv import load_dotenv
from db              import load_consignments, save_consignments
from auth            import register_user, login_user
from eudr            import get_eudr_risk, score_dataframe, EUDR_REGULATED_CROPS, render_eudr_page
from bridge_engine   import transmit_consignment, get_bridge_mode, get_credential_status, set_bridge_mode, set_portal_credentials, generate_kentrade_csv, generate_kephis_csv
from supabase_db import save_transmission_log_db, load_transmission_log_db
from qr_generator    import render_qr_page
from packhouse       import render_packhouse_page
from compliance_pdf  import render_compliance_pdf_page
from daily_batch     import render_daily_batch_page
from pre_audit       import render_pre_audit_page
from data_ingestion  import render_data_ingestion_page
from trial           import render_trial_banner, render_container_tracker
from kpi_dashboard   import render_kpi_dashboard
from invite_codes    import generate_invite_code, list_invite_codes, ROLE_PREFIXES, MODULE_ROLE_MAP
from livestock          import render_animal_registry
from livestock_health   import render_temp_monitoring
from livestock_disease  import render_disease_engine
from livestock_symptoms import render_symptom_log
from livestock_vet      import render_vet_dashboard
from livestock_diaspora import render_diaspora_dashboard
from livestock_alerts   import render_alert_centre
from livestock_vet_earnings import render_vet_earnings
from livestock_hardware import render_hardware_registry
from livestock_admin    import render_admin_overview
from support import render_support_page, render_floating_support_button
from certificate_vault_page import render_certificate_vault_page
from farm_boundary_upload import render_farm_boundary_upload_page
from ndvi_dashboard import render_ndvi_dashboard_page
from weather_risk_dashboard import render_weather_risk_dashboard_page
from quarantine_desk import render_quarantine_desk_page
from company_profile import render_company_profile_page
from session_persistence import (
    get_valid_username_from_cookie, create_session,
    set_session_cookie, clear_session
)
from supabase_db import get_user
from ledger_db import save_ledger_record, load_ledger

load_dotenv()
from data_init import ensure_data_files
ensure_data_files()

st.set_page_config(page_title="VeriPath Africa | Enterprise", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0a0e1a; color: #e8eaf0; }
.stApp { background-color: #0a0e1a; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1224 0%, #111827 100%); border-right: 1px solid #1e2d45; }
section[data-testid="stSidebar"] .stRadio label { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #94a3b8; padding: 6px 0; }
section[data-testid="stSidebar"] .stRadio label:hover { color: #38bdf8; }
.metric-card { background: linear-gradient(135deg, #111827 0%, #1a2540 100%); border: 1px solid #1e3a5f; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; transition: border-color 0.2s; }
.metric-card:hover { border-color: #38bdf8; }
.metric-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; font-family: 'Space Mono', monospace; }
.metric-value { font-size: 1.8rem; font-weight: 700; color: #38bdf8; font-family: 'Space Mono', monospace; margin-top: 4px; }
.auth-logo { font-family: 'Space Mono', monospace; font-size: 1.6rem; color: #38bdf8; text-align: center; margin-bottom: 6px; letter-spacing: 0.1em; }
.auth-tagline { text-align: center; color: #64748b; font-size: 0.85rem; margin-bottom: 32px; }
.section-header { font-family: 'Space Mono', monospace; font-size: 1.1rem; color: #38bdf8; border-bottom: 1px solid #1e3a5f; padding-bottom: 8px; margin-bottom: 20px; letter-spacing: 0.05em; }
.risk-card { border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; border: 1px solid; }
.risk-high   { background: #1a0a0a; border-color: #dc2626; }
.risk-medium { background: #1a1400; border-color: #d97706; }
.risk-low    { background: #071a0f; border-color: #16a34a; }
.risk-exempt { background: #0d1224; border-color: #334155; }
.portal-card { background: #0d1224; border: 1px solid #1e3a5f; border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; }
.portal-success { border-color: #16a34a; background: #071a0f; }
.portal-pending { border-color: #d97706; background: #1a1400; }
.portal-error   { border-color: #dc2626; background: #1a0a0a; }
.mode-badge-sim  { background:#1c2a3a; color:#38bdf8; border:1px solid #1e3a5f; border-radius:20px; padding:3px 12px; font-size:0.75rem; font-family:'Space Mono',monospace; }
.mode-badge-real { background:#071a0f; color:#4ade80; border:1px solid #16a34a; border-radius:20px; padding:3px 12px; font-size:0.75rem; font-family:'Space Mono',monospace; }
.stButton > button { background: linear-gradient(135deg, #0369a1, #0284c7); color: white; border: none; border-radius: 8px; font-family: 'Space Mono', monospace; font-size: 0.85rem; padding: 10px 24px; transition: all 0.2s; }
.stButton > button:hover { background: linear-gradient(135deg, #0284c7, #38bdf8); transform: translateY(-1px); box-shadow: 0 4px 15px rgba(56,189,248,0.3); }
.stTextInput input, .stNumberInput input, .stSelectbox select { background: #111827 !important; border: 1px solid #1e3a5f !important; border-radius: 8px !important; color: #e8eaf0 !important; }
.stDataFrame { border-radius: 10px; overflow: hidden; }
.stSuccess { background: #052e16 !important; border-left: 4px solid #4ade80 !important; }
.stWarning { background: #1c1400 !important; border-left: 4px solid #fbbf24 !important; }
.stError   { background: #2d0a0a !important; border-left: 4px solid #f87171 !important; }
.user-pill { background: #0f2233; border: 1px solid #1e3a5f; border-radius: 20px; padding: 8px 14px; font-size: 0.8rem; color: #38bdf8; font-family: 'Space Mono', monospace; margin-bottom: 8px; }
.module-card { border-radius: 16px; padding: 24px 20px; text-align: center; margin-bottom: 8px; }
.module-card-crops { background: #071a0f; border: 2px solid #16a34a; }
.module-card-live  { background: #1a0f00; border: 2px solid #d97706; }
</style>
""", unsafe_allow_html=True)

# ── Module → Role mapping ──────────────────────────────────────────────────
MODULE_ROLES = {
    "🌿 VeriPath Crops": {
        "roles": ["record_keeper","agronomist","compliance_officer","exporter","admin"],
        "invite_prefixes": ["VP-REC","VP-AGR","VP-COM","VP-EXP","VP-ADM"],
        "badge_color": "#16a34a", "badge_bg": "#071a0f",
        "icon": "🌿", "description": "Export compliance & EUDR traceability",
    },
    "🐄 VeriPath Livestock": {
        "roles": ["diaspora_owner","veterinarian","farm_manager","admin"],
        "invite_prefixes": ["VP-DIA","VP-VET","VP-FMG","VP-ADM"],
        "badge_color": "#d97706", "badge_bg": "#1a0f00",
        "icon": "🐄", "description": "Diaspora animal health & biosecurity",
    },
}

HS_CODE_MAP = {
    "Maize":"1005.90","Coffee":"0901.11","Tea":"0902.30","Avocado":"0804.40",
    "French Beans":"0708.20","Roses":"0603.11","Macadamia Nuts":"0802.62",
    "Mango":"0804.50","Pineapple":"0804.30","Passion Fruit":"0810.90",
}
KENYAN_COUNTIES = [
    "Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa",
    "Homa Bay","Isiolo","Kajiado","Kakamega","Kericho","Kiambu","Kilifi",
    "Kirinyaga","Kisii","Kisumu","Kitui","Kwale","Laikipia","Lamu","Machakos",
    "Makueni","Mandera","Marsabit","Meru","Migori","Mombasa","Murang'a",
    "Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri",
    "Samburu","Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia",
    "Turkana","Uasin Gishu","Vihiga","Wajir","West Pokot"
]
COUNTY_COORDS = {
    "Nairobi":(-1.2921,36.8219),"Mombasa":(-4.0435,39.6682),
    "Kisumu":(-0.1022,34.7617),"Nakuru":(-0.3031,36.0800),
    "Kericho":(-0.3686,35.2863),"Narok":(-1.0836,35.8716),
    "Machakos":(-1.5177,37.2634),"Meru":(0.0467,37.6490),
    "Kakamega":(0.2827,34.7519),"Nyeri":(-0.4167,36.9500),
    "Kiambu":(-1.1714,36.8353),"Murang'a":(-0.7167,37.1500),
    "Embu":(-0.5333,37.4500),"Kirinyaga":(-0.5594,37.3347),
    "Nandi":(0.1833,35.1167),"Uasin Gishu":(0.5500,35.2667),
    "Trans Nzoia":(1.0167,34.9500),"Bungoma":(0.5635,34.5606),
    "Kilifi":(-3.6305,39.8499),"Kwale":(-4.1740,39.4520),
}
LEDGER_COLS = [
    'Consignment_ID','Timestamp','Farmer_Name','Crop_Type',
    'KRA_PIN','PIN_Valid','HS_Code','Origin_County',
    'Net_Weight_KG','FOB_Value_USD','Source'
]
KRA_PIN_PATTERN = re.compile(r'^[A-Z]\d{9}[A-Z]$')

# ── Role → Pages ───────────────────────────────────────────────────────────
ROLE_PAGES = {
    "farmer": ["📸 Farm Activities","📦 My Batches","💰 Payments","🌿 My Farm Profile"],
    "record_keeper": ["🌿 Outgrower Registry","📦 Packhouse Intake","📥 Data Ingestion","👥 My Team","🆘 Support"],
    "agronomist": ["🌿 Outgrower Registry","📦 Packhouse Intake"],
    "compliance_officer": [
        "📥 Data Ingestion","📅 Daily Batch Reports",
        "🔍 Pre-Audit Gate","🧪 Quarantine Desk","🌍 EUDR Risk Scorer","📄 Compliance PDF","🔐 Certificate Vault","🛰 Farm Boundary Upload","🌱 NDVI Crop Health","⛈️ Flash Weather Risk",
    ],
    "exporter": [
        "📊 Dashboard","📥 Data Ingestion","📑 Consignment Ledger",
        "🌿 Outgrower Registry","📦 Packhouse Intake","📅 Daily Batch Reports",
        "🔍 Pre-Audit Gate","🧪 Quarantine Desk","🌍 EUDR Risk Scorer","📄 Compliance PDF","🔐 Certificate Vault","🛰 Farm Boundary Upload","🌱 NDVI Crop Health","⛈️ Flash Weather Risk",
        "📡 Transmit to Portals","🌱 Carbon Tracking","🗺 Origin Map",
        "🏢 Company Profile","👥 My Team","🆘 Support",
    ],
    "admin": [
        "📊 Dashboard","📥 Data Ingestion","📑 Consignment Ledger",
        "🌿 Outgrower Registry","📦 Packhouse Intake","📅 Daily Batch Reports",
        "🔍 Pre-Audit Gate","🧪 Quarantine Desk","🌍 EUDR Risk Scorer","📄 Compliance PDF","🔐 Certificate Vault","🛰 Farm Boundary Upload","🌱 NDVI Crop Health","⛈️ Flash Weather Risk",
        "📡 Transmit to Portals","🌱 Carbon Tracking","🗺 Origin Map",
        "📈 KPI Dashboard","🔑 Invite Codes","👥 My Team","🗑 Demo Reset",
    ],
    "admin_livestock": [
        "📊 Farm Overview","🐄 Animal Registry","🌡 Temperature Entry",
        "📋 Daily Symptom Log","🧪 Disease Probability","🚨 Clinical Alerts",
        "🌍 My Animals","🌡 Health Alerts","💰 My Earnings",
        "🔧 Hardware Registry","🔑 Invite Codes","👥 My Team","🗑 Demo Reset",
    ],
    "diaspora_owner": [
        "🌍 My Animals","🌡 Health Alerts","📋 Vet Reports",
        "💳 Payments & Commissions","🆘 Support",
    ],
    "veterinarian": [
        "🚨 Clinical Alerts","🐄 Animal Registry","📋 Patient History",
        "🧪 Disease Probability","📋 Daily Symptom Log","💰 My Earnings",
        "🔧 Hardware Registry","🆘 Support",
    ],
    "herdsman": ["📋 Daily Symptom Log","🐄 My Herd","🌡 Temperature Entry"],
    "farm_manager": [
        "📊 Farm Overview","🐄 Animal Registry","🌡 Temperature Entry",
        "📋 Daily Symptom Log","🌡 Health Monitoring","🔧 Hardware Registry",
        "💰 Cost of Production","🥛 Milk Tracker","📈 Farm P&L",
        "🏢 Company Profile","👥 My Team","🆘 Support",
    ],
}

# ── Auth state ─────────────────────────────────────────────────────────────
for key, val in [("authenticated",False),("user_profile",None),("auth_page","login"),("reg_module",None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Restore session from cookie (survives page refresh) ────────────────────
if not st.session_state["authenticated"]:
    _cookie_username = get_valid_username_from_cookie()
    if _cookie_username:
        _restored_user = get_user(_cookie_username)
        if _restored_user:
            st.session_state["authenticated"] = True
            st.session_state["user_profile"] = {
                k: v for k, v in _restored_user.items()
                if k not in ("password", "salt")
            }

# ── Auth wall ──────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.markdown("<div style='text-align:center;margin-top:60px'>", unsafe_allow_html=True)
    st.markdown("<div class='auth-logo'>▸ VERIPATH AFRICA</div>", unsafe_allow_html=True)
    st.markdown("<div class='auth-tagline'>Kenya Agricultural Intelligence Infrastructure</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    col_l, col_r = st.columns(2)
    with col_l:
        if st.button("🔑 Sign In", use_container_width=True):
            st.session_state["auth_page"] = "login"
            st.rerun()
    with col_r:
        if st.button("📝 Register", use_container_width=True):
            st.session_state["auth_page"] = "register"
            st.rerun()
    st.markdown("---")

    if st.session_state["auth_page"] == "login":
        st.markdown("### Sign In to VeriPath")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="your username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit   = st.form_submit_button("Sign In →", use_container_width=True)
        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password.")
            else:
                ok, msg, profile = login_user(username, password)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_profile"]  = profile
                    _token = create_session(profile["username"])
                    set_session_cookie(_token)
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        st.markdown("<br><small style='color:#64748b'>No account? Click Register above.</small>", unsafe_allow_html=True)

    else:
        st.markdown("### Create Your Account")
        st.markdown("<div class='section-header'>STEP 1 — CHOOSE YOUR MODULE</div>", unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("""
            <div class='module-card module-card-crops'>
                <div style='font-size:2rem'>🌿</div>
                <div style='font-family:Space Mono,monospace;font-size:0.9rem;color:#4ade80;margin:8px 0'>VERIPATH CROPS</div>
                <div style='font-size:0.78rem;color:#94a3b8'>Export compliance & EUDR traceability</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select Crops Module", use_container_width=True, key="btn_crops"):
                st.session_state["reg_module"] = "🌿 VeriPath Crops"
                st.rerun()
        with col_m2:
            st.markdown("""
            <div class='module-card module-card-live'>
                <div style='font-size:2rem'>🐄</div>
                <div style='font-family:Space Mono,monospace;font-size:0.9rem;color:#fbbf24;margin:8px 0'>VERIPATH LIVESTOCK</div>
                <div style='font-size:0.78rem;color:#94a3b8'>Diaspora animal health & biosecurity</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select Livestock Module", use_container_width=True, key="btn_live"):
                st.session_state["reg_module"] = "🐄 VeriPath Livestock"
                st.rerun()

        selected_module = st.session_state.get("reg_module", None)

        if selected_module:
            mod_cfg = MODULE_ROLES[selected_module]
            bg    = mod_cfg['badge_bg']
            color = mod_cfg['badge_color']
            st.markdown(
                f"<div style=\"background:{bg};border:1px solid {color};"
                f"border-radius:20px;padding:4px 16px;font-size:0.8rem;color:{color};"
                f"font-family:Space Mono,monospace;display:inline-block;margin:12px 0 20px 0\">"
                f"✓ {selected_module} selected</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div class='section-header'>STEP 2 — YOUR DETAILS</div>", unsafe_allow_html=True)
            # Filter out herdsman from registration — field role only
            reg_roles = [r for r in mod_cfg["roles"] if r != "herdsman"]

            with st.form("register_form"):
                col1, col2 = st.columns(2)
                with col1:
                    full_name = st.text_input("Full Name *", placeholder="Joseph Memusi")
                    username  = st.text_input("Username *",  placeholder="josephm")
                with col2:
                    role = st.selectbox("Role", reg_roles)
                    # Farmers are individuals — no company
                    is_farmer = role == "farmer"
                    if is_farmer:
                        company = full_name.strip() or "Individual"
                        st.markdown(
                            "<small style='color:#64748b'>Farmers register as individuals "
                            "— no company needed.</small>",
                            unsafe_allow_html=True
                        )
                    else:
                        company = st.text_input("Company *", placeholder="VeriPath Africa")

                invite_code = st.text_input(
                    "Invite Code *",
                    placeholder=f"{mod_cfg['invite_prefixes'][0]}-XXXX"
                )
                password  = st.text_input("Password *",         type="password", placeholder="Min. 10 chars · Upper · Lower · Number · Special (@#$!)")
                password2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
                st.markdown("""
                <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                            padding:12px 16px;margin:8px 0;font-size:0.82rem;color:#94a3b8'>
                    By registering, you agree to VeriPath Africa's
                    <a href='https://veripath.co.ke/terms.html'
                       target='_blank' style='color:#38bdf8;text-decoration:underline'>
                       Terms &amp; Conditions</a>
                    and confirm compliance with Kenya's
                    <a href='https://www.odpc.go.ke/data-protection-act/'
                       target='_blank' style='color:#38bdf8;text-decoration:underline'>
                       Data Protection Act (ODPC)</a>.
                    Your farm and farmer data is processed lawfully under your authority
                    as the data controller.
                </div>
                """, unsafe_allow_html=True)
                agree_tnc  = st.checkbox("I have read and agree to the Terms & Conditions *")
                agree_odpc = st.checkbox(
                    "I confirm I have lawful authority over the farmer/farm data "
                    "I will upload and comply with Kenya's Data Protection Act *"
                )
                submit = st.form_submit_button("Create Account →", use_container_width=True)

            if submit:
                # For farmers, company = their name
                if role == "farmer":
                    company = full_name.strip() or "Individual"
                errors = []
                if not full_name.strip():              errors.append("Full Name is required")
                if not username.strip():               errors.append("Username is required")
                if not company.strip():                errors.append("Company is required")
                if not invite_code.strip():            errors.append("Invite code is required")
                if not password:                       errors.append("Password is required")
                if password != password2:              errors.append("Passwords do not match")
                if not agree_tnc:                      errors.append("You must agree to the Terms & Conditions")
                if not agree_odpc:                     errors.append("You must confirm ODPC data protection compliance")
                if errors:
                    for e in errors: st.error(f"❌ {e}")
                else:
                    ok, msg = register_user(
                        username, password, full_name, company,
                        role, invite_code, module=selected_module
                    )
                    if ok:
                        st.success(f"✅ {msg} You can now sign in.")
                        st.session_state.pop("reg_module", None)
                        st.session_state["auth_page"] = "login"
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.markdown("""
            <div style='background:#0d1224;border:1px dashed #1e3a5f;border-radius:12px;
                        padding:32px;text-align:center;margin-top:16px'>
                <div style='font-size:1.5rem'>👆</div>
                <div style='color:#64748b;margin-top:8px;font-size:0.9rem'>Select a module above to continue</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("← Back to Sign In", key="back_to_login"):
            st.session_state["auth_page"] = "login"
            st.session_state.pop("reg_module", None)
            st.rerun()

    st.stop()

# ── Ledger state ───────────────────────────────────────────────────────────
if "ledger_data" not in st.session_state:
    saved = load_consignments()
    if saved:
        df_saved = pd.DataFrame(saved)
        st.session_state["ledger_data"] = df_saved[[c for c in LEDGER_COLS if c in df_saved.columns]]
    else:
        st.session_state["ledger_data"] = pd.DataFrame(columns=LEDGER_COLS)

def validate_kra_pin(pin):
    pin = pin.strip().upper()
    if not pin or pin in ("PENDING","N/A",""):
        return False, "Missing"
    return (True, pin) if KRA_PIN_PATTERN.match(pin) else (False, pin)

def get_hs_code(crop):
    return HS_CODE_MAP.get(crop, "UNKNOWN")

# ── Sidebar ────────────────────────────────────────────────────────────────
profile = st.session_state["user_profile"]
role    = profile.get("role","record_keeper")
module  = profile.get("module") or (
    "🐄 VeriPath Livestock"
    if role in ("diaspora_owner","veterinarian","herdsman","farm_manager")
    else "🌿 VeriPath Crops"
)

st.sidebar.markdown("## 🏗 VeriPath Enterprise")
st.sidebar.markdown(
    f"<div class='user-pill'>👤 {profile['full_name']}<br>"
    f"<span style='color:#64748b;font-size:0.7rem'>{profile['company']} · {role}</span></div>",
    unsafe_allow_html=True
)

# Module badge
_mod_cfg = MODULE_ROLES.get(module, MODULE_ROLES["🌿 VeriPath Crops"])
st.sidebar.markdown(
    f"<div style='background:{_mod_cfg['badge_bg']};border:1px solid {_mod_cfg['badge_color']};"
    f"border-radius:10px;padding:5px 12px;font-size:0.72rem;color:{_mod_cfg['badge_color']};"
    f"font-family:Space Mono,monospace;margin-bottom:8px;text-align:center'>{module}</div>",
    unsafe_allow_html=True
)

# Module switcher for admin
if role == "admin":
    switched = st.sidebar.radio(
        "Switch module",
        ["🌿 VeriPath Crops","🐄 VeriPath Livestock"],
        index=0 if module == "🌿 VeriPath Crops" else 1,
        key="module_switcher"
    )
    if switched != module:
        st.session_state["user_profile"]["module"] = switched
        st.rerun()
    module = switched

# Pages based on role + module
if role == "admin" and module == "🐄 VeriPath Livestock":
    pages = ROLE_PAGES["admin_livestock"]
else:
    pages = ROLE_PAGES.get(role, ["📦 Packhouse Intake"])

st.sidebar.markdown("---")
page = st.sidebar.radio("", pages)
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<small style='color:#64748b'>Role: <b style='color:#38bdf8'>{role}</b></small>",
    unsafe_allow_html=True
)
st.sidebar.markdown("---")
render_container_tracker(profile["username"], module="livestock" if "Livestock" in module else "crops", role=role)

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    clear_session()
    for k in ["authenticated","user_profile","auth_page","audit_result",
              "batch_approved","intake_rows","ingestion_entries","reg_module"]:
        st.session_state.pop(k, None)
    st.rerun()

# ── Save to ledger helper ──────────────────────────────────────────────────
def save_to_ledger(new_entries):
    company = profile.get("company","")
    for e in new_entries:
        record = {
            "company":     company,
            "session_id":  e.get("Consignment_ID",""),
            "farmer_id":   e.get("Farmer_ID",""),
            "farmer_name": e.get("Farmer_Name",""),
            "county":      e.get("Origin_County",""),
            "gps":         e.get("GPS",""),
            "crop":        e.get("Crop_Type",""),
            "hs_code":     e.get("HS_Code",""),
            "weight_kg":   e.get("Net_Weight_KG", 0),
            "eudr_risk":   e.get("EUDR_Risk",""),
            "notes":       e.get("Notes",""),
            "kra_pin":     e.get("KRA_PIN",""),
            "fob_value_usd": float(e.get("FOB_Value_USD", 0) or 0),
            "packhouse":   e.get("Packhouse",""),
            "intake_date": datetime.date.today().isoformat(),
            "day_of_week": datetime.date.today().strftime("%A"),
            "timestamp":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status":      "pending",
            "source":      e.get("Source",""),
        }
        save_ledger_record(record)
    st.session_state["ledger_data"] = pd.DataFrame(load_ledger(company))


# ── Trial banner ───────────────────────────────────────────────────────────
render_trial_banner(profile["username"], role=profile.get("role","exporter"), module="livestock" if "Livestock" in module else "crops")
render_floating_support_button(profile)

# ══════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════

# ── CROPS PAGES ───────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.markdown("# 📊 VeriPath Dashboard")
    st.markdown("<p style='color:#64748b'>Real-time supply chain intelligence — 🌿 Crops Module</p>", unsafe_allow_html=True)
    from ledger_db import load_ledger as _ll
    _company = profile.get("company","") if role != "admin" else ""
    _ledger  = _ll(_company)
    df = pd.DataFrame(_ledger) if _ledger else pd.DataFrame(columns=LEDGER_COLS)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>TOTAL CONSIGNMENTS</div>
            <div class='metric-value'>{len(df)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        tw = df["weight_kg"].astype(float).sum() if not df.empty and "weight_kg" in df.columns else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>TOTAL WEIGHT (KG)</div>
            <div class='metric-value'>{tw:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        tf = df["FOB_Value_USD"].astype(float).sum() if not df.empty and "FOB_Value_USD" in df.columns else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>FOB VALUE (USD) 🇺🇸</div>
            <div class='metric-value' style='color:#4ade80'>${tf:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        vp = df[df["PIN_Valid"]=="✅ Valid"].shape[0] if not df.empty and "PIN_Valid" in df.columns else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>VERIFIED KRA PINs</div>
            <div class='metric-value'>{vp}</div>
        </div>""", unsafe_allow_html=True)
    if not df.empty:
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("<div class='section-header'>CONSIGNMENTS BY CROP</div>", unsafe_allow_html=True)
            crop_col = "crop" if "crop" in df.columns else "Crop_Type" if "Crop_Type" in df.columns else None
            if crop_col:
                cc = df[crop_col].value_counts().reset_index()
                cc.columns = ["Crop","Count"]
                st.bar_chart(cc.set_index("Crop"))
        with col_b:
            st.markdown("<div class='section-header'>WEIGHT BY COUNTY</div>", unsafe_allow_html=True)
            county_col = "county" if "county" in df.columns else "Origin_County" if "Origin_County" in df.columns else None
            if county_col and "weight_kg" in df.columns:
                cf = df.groupby(county_col)["weight_kg"].sum().reset_index()
                cf.columns = ["County","Weight_KG"]
                st.bar_chart(cf.set_index("County"))
    else:
        st.info("No data yet. Use Packhouse Intake to add records.")

elif page == "📥 Data Ingestion":
    render_data_ingestion_page(save_callback=save_to_ledger)

elif page == "📑 Consignment Ledger":
    st.markdown("# 📑 Global Consignment Ledger")
    from ledger_db import load_ledger as _ll2
    _company2 = profile.get("company","") if role != "admin" else ""
    _ledger2  = _ll2(_company2)
    df = pd.DataFrame(_ledger2) if _ledger2 else pd.DataFrame(columns=LEDGER_COLS)
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(df))
        col2.metric("Weight (KG)", f"{df['weight_kg'].astype(float).sum():,.0f}" if 'weight_kg' in df.columns else "0")
        col3.metric("FOB Value",   f"${df['FOB_Value_USD'].astype(float).sum():,.2f}" if 'FOB_Value_USD' in df.columns else "$0.00")
        st.markdown("---")
        with st.expander("🔍 Filter"):
            fc1, fc2 = st.columns(2)
            _crop_col   = "crop" if "crop" in df.columns else "Crop_Type" if "Crop_Type" in df.columns else None
            _county_col = "county" if "county" in df.columns else "Origin_County" if "Origin_County" in df.columns else None
            crop_filter   = fc1.multiselect("Crop",   options=df[_crop_col].unique().tolist() if _crop_col else [])
            county_filter = fc2.multiselect("County", options=df[_county_col].unique().tolist() if _county_col else [])
        display_df = df.copy()
        if crop_filter and _crop_col:     display_df = display_df[display_df[_crop_col].isin(crop_filter)]
        if county_filter and _county_col: display_df = display_df[display_df[_county_col].isin(county_filter)]
        st.markdown(f"<div class='section-header'>UNIFIED REGULATORY TABLE — {len(display_df)} RECORDS</div>", unsafe_allow_html=True)
        st.dataframe(display_df.drop(columns=["_error"], errors="ignore"), use_container_width=True)
        st.download_button("⬇ Export CSV",
            data=display_df.to_csv(index=False).encode("utf-8"),
            file_name=f"veripath_ledger_{datetime.date.today()}.csv", mime="text/csv")
    else:
        st.warning("Ledger is empty.")

elif page == "🌿 Outgrower Registry":
    render_qr_page(profile=profile)

elif page == "📦 Packhouse Intake":
    render_packhouse_page(profile=profile)

elif page == "📅 Daily Batch Reports":
    render_daily_batch_page(profile=profile)

elif page == "🔍 Pre-Audit Gate":
    render_pre_audit_page(profile)

elif page == "🧪 Quarantine Desk":
    render_quarantine_desk_page(profile)

elif page == "🌍 EUDR Risk Scorer":
    render_eudr_page()

elif page == "📄 Compliance PDF":
    render_compliance_pdf_page(profile=profile)

elif page == "🔐 Certificate Vault":
    render_certificate_vault_page(profile)

elif page == "🛰 Farm Boundary Upload":
    render_farm_boundary_upload_page(profile)

elif page == "🌱 NDVI Crop Health":
    render_ndvi_dashboard_page(profile)

elif page == "⛈️ Flash Weather Risk":
    render_weather_risk_dashboard_page(profile)

elif page == "📡 Transmit to Portals":
    st.markdown("# 📡 Transmit to Government Portals")

    if not st.session_state.get("batch_approved"):
        st.markdown("""
        <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:12px;
                    padding:24px;text-align:center;margin:20px 0'>
            <div style='font-size:1.2rem;font-weight:700;color:#f87171'>🔒 SUBMISSION LOCKED</div>
            <div style='color:#94a3b8;margin-top:8px'>
                Batch must pass <b>🔍 Pre-Audit Gate</b> before portal submission unlocks.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Demo / Live toggle ─────────────────────────────────────────
        st.markdown("<div class='section-header'>TRANSMISSION MODE</div>",
                    unsafe_allow_html=True)
        col_tog1, col_tog2 = st.columns(2)
        with col_tog1:
            if st.button("⚙ DEMO MODE",
                         use_container_width=True,
                         type="secondary" if get_bridge_mode()=="real" else "primary"):
                set_bridge_mode("simulation")
                st.rerun()
        from supabase_db import get_client as _gc
        try:
            _live_setting = _gc().table("platform_settings").select("setting_value").eq(
                "setting_key", "live_transmission_enabled"
            ).execute().data
            _live_enabled = _live_setting[0]["setting_value"] == "true" if _live_setting else False
        except Exception:
            _live_enabled = False

        with col_tog2:
            if _live_enabled:
                if st.button("🟢 LIVE MODE",
                             use_container_width=True,
                             type="primary" if get_bridge_mode()=="real" else "secondary"):
                    set_bridge_mode("real")
                    st.rerun()
            else:
                st.button("🔒 LIVE MODE (Locked)", use_container_width=True, disabled=True,
                           help="Live portal submission is locked until official integration approval is confirmed by VeriPath admin.")

        mode = get_bridge_mode()
        if mode == "simulation":
            st.markdown("""
            <div style='background:#1c2a3a;border:1px solid #1e3a5f;border-radius:10px;
                        padding:12px 16px;margin:12px 0'>
                <span class='mode-badge-sim'>⚙ SIMULATION MODE</span>
                <span style='color:#64748b;font-size:0.82rem;margin-left:12px'>
                    Safe for demos — no real portal submissions
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#071a0f;border:1px solid #16a34a;border-radius:10px;
                        padding:12px 16px;margin:12px 0'>
                <span class='mode-badge-real'>🟢 LIVE MODE</span>
                <span style='color:#4ade80;font-size:0.82rem;margin-left:12px'>
                    Real submissions to KenTrade · KEPHIS · AFA IMIS
                </span>
            </div>
            """, unsafe_allow_html=True)

            # ── Credential input for Live mode ─────────────────────────
            cred_status = get_credential_status()
            missing_creds = [p for p, ok in cred_status.items() if not ok]
            if missing_creds:
                st.markdown("---")
                st.markdown("<div class='section-header'>PORTAL CREDENTIALS</div>",
                            unsafe_allow_html=True)
                st.markdown(
                    "<small style='color:#94a3b8'>Enter credentials for selected portals. "
                    "Not stored permanently — session only.</small>",
                    unsafe_allow_html=True
                )
                for portal in missing_creds:
                    with st.expander(f"🔐 {portal} credentials"):
                        u = st.text_input(f"{portal} Username",
                                          key=f"cred_u_{portal}",
                                          placeholder=f"Your {portal} login")
                        p = st.text_input(f"{portal} Password",
                                          type="password",
                                          key=f"cred_p_{portal}",
                                          placeholder="••••••••")
                        if st.button(f"💾 Save {portal} credentials",
                                     key=f"save_cred_{portal}"):
                            if u and p:
                                set_portal_credentials(portal, u, p)
                                st.success(f"✅ {portal} credentials set for this session.")
                                st.rerun()
                            else:
                                st.error("Both username and password required.")

        st.markdown("---")
        approved       = st.session_state.get("approved_records", [])

        # ── Shipment Header (once per batch) ────────────────────────────
        st.markdown("### 📦 Shipment Header")
        hdr_col1, hdr_col2, hdr_col3 = st.columns(3)
        with hdr_col1:
            consignee_name = st.text_input("Consignee Name", key="shipment_consignee_name")
        with hdr_col2:
            consignee_address = st.text_input("Consignee Address", key="shipment_consignee_address")
        with hdr_col3:
            point_of_exit = st.selectbox(
                "Point of Exit",
                ["JKIA - Nairobi", "Mombasa Port", "Namanga", "Busia", "Malaba"],
                key="shipment_point_of_exit"
            )

        header_complete = bool(
            consignee_name.strip() and consignee_address.strip() and point_of_exit
        )
        if approved and not header_complete:
            st.warning("⚠ Complete the Shipment Header above to enable submission.")

        # ── Per-record packing detail + HS-code hard block ───────────────
        if approved and header_complete:
            st.markdown("### 📋 Per-Record Packing Details")
            pkg_df = pd.DataFrame([
                {
                    "Consignment_ID":     r.get("session_id", "—"),
                    "Farmer_Name":        r.get("farmer_name", "—"),
                    "Crop":               r.get("crop", "—"),
                    "Weight_KG":          r.get("weight_kg", 0),
                    "Package_Type":       r.get("package_type", "Carton"),
                    "Number_of_Packages": r.get("number_of_packages", 1),
                }
                for r in approved
            ])
            edited_pkg_df = st.data_editor(
                pkg_df,
                column_config={
                    "Package_Type": st.column_config.SelectboxColumn(
                        "Package_Type", options=["Carton", "Crate", "Pallet", "Bag", "Box"]
                    ),
                    "Number_of_Packages": st.column_config.NumberColumn(
                        "Number_of_Packages", min_value=1, step=1
                    ),
                },
                disabled=["Consignment_ID", "Farmer_Name", "Crop", "Weight_KG"],
                use_container_width=True,
                hide_index=True,
                key="packing_editor",
            )
            pkg_lookup = edited_pkg_df.set_index("Consignment_ID").to_dict("index")
            enriched = [
                {
                    **r,
                    "consignee_name":     consignee_name.strip(),
                    "consignee_address":  consignee_address.strip(),
                    "point_of_exit":      point_of_exit,
                    "package_type":       pkg_lookup.get(r.get("session_id", "—"), {}).get("Package_Type", "Carton"),
                    "number_of_packages": pkg_lookup.get(r.get("session_id", "—"), {}).get("Number_of_Packages", 1),
                }
                for r in approved
            ]

            # HARD BLOCK: records missing hs_code cannot be transmitted, even if
            # they reached approved_records via the pre-audit "Override & Approve
            # Anyway" path (which bypasses REQUIRED_FIELDS). Clean records in the
            # same batch are unaffected.
            hs_missing = [r for r in enriched if not str(r.get("hs_code","")).strip()
                          or str(r.get("hs_code","")).strip().upper() == "UNKNOWN"]
            hs_ready   = [r for r in enriched if r not in hs_missing]

            if hs_missing:
                names = "\n".join(
                    f"- {r.get('farmer_name','—')} · {r.get('crop','—')} · {r.get('session_id','—')}"
                    for r in hs_missing
                )
                st.error(f"🛑 {len(hs_missing)} record(s) BLOCKED — missing HS code:\n\n{names}")
                st.caption("These likely came through the pre-audit override path. Fix the HS code in the ledger and re-run pre-audit before resubmitting.")

            approved = hs_ready
        elif not header_complete:
            approved = []

        st.markdown("---")
        portal_options = st.multiselect(
            "Target portals",
            ["KenTrade","KEPHIS","AFA IMIS"],
            default=["KenTrade","KEPHIS","AFA IMIS"]
        )
        st.markdown(f"**{len(approved)} approved records ready**")

        if approved and portal_options:
            btn_label = (f"🚀 LIVE SUBMIT — {len(approved)} records to {len(portal_options)} portal(s)"
                         if mode == "real"
                         else f"⚙ DEMO RUN — {len(approved)} records to {len(portal_options)} portal(s)")
            if st.button(btn_label, use_container_width=True, type="primary"):
                all_results  = []
                fallback_csv = {}
                progress     = st.progress(0)
                total        = len(approved) * len(portal_options)
                done         = 0
                for record in approved:
                    with st.spinner(f"Transmitting {record.get('farmer_name','—')}..."):
                        results = transmit_consignment(
                            record, portal_options,
                            all_records=approved
                        )
                        for r in results:
                            if r.get("fallback_csv"):
                                fallback_csv[r["portal"]] = {
                                    "csv":      r["fallback_csv"],
                                    "filename": r.get("fallback_filename","fallback.csv"),
                                }
                        all_results.extend(results)
                        done += len(portal_options)
                        progress.progress(done / total)

                _batch_ref = f"{st.session_state.get('audit_result',{}).get('run_at','')[:10]}_{profile.get('company','')}"
                _allowed_keys = {"company", "consignment", "portal", "status", "message", "submitted_at"}
                _clean_results = [
                    {k: v for k, v in _r.items() if k in _allowed_keys} | {"batch_reference": _batch_ref}
                    for _r in all_results
                ]
                save_transmission_log_db(_clean_results, company=profile.get("company",""))

                # ── Create real consignment records for successfully
                # transmitted batches (previously never wired in —
                # consignments table stayed empty regardless of submission)
                from db import add_consignment
                submitted_consignment_ids = {
                    r.get("consignment") for r in all_results if r["status"] == "submitted"
                }
                for record in approved:
                    if record.get("session_id") in submitted_consignment_ids:
                        add_consignment({
                            "consignment_id": record.get("session_id", ""),
                            "farmer_name":     record.get("farmer_name", ""),
                            "crop_type":       record.get("crop", ""),
                            "kra_pin":         record.get("kra_pin", ""),
                            "pin_valid":       "valid" if record.get("kra_pin") else "unknown",
                            "hs_code":         record.get("hs_code", ""),
                            "origin_county":   record.get("county", ""),
                            "net_weight_kg":   record.get("weight_kg", 0),
                            "fob_value_usd":   record.get("fob_value_usd", 0.0),
                            "source":          "transmit_to_portals",
                        }, company=profile.get("company",""))

                # ── Results display ────────────────────────────────────
                success = [r for r in all_results if r["status"] == "submitted"]
                timeout = [r for r in all_results if r["status"] == "timeout"]
                errors  = [r for r in all_results if r["status"] == "error"]

                if success:
                    st.success(f"✅ {len(success)} submission(s) successful.")
                if timeout:
                    st.warning(f"⏱ {len(timeout)} portal(s) timed out — CSV fallback ready below.")
                if errors:
                    st.error(f"❌ {len(errors)} error(s) — CSV fallback ready below.")

                # ── Fallback CSV downloads ─────────────────────────────
                if fallback_csv:
                    st.markdown("---")
                    st.markdown("""
                    <div style='background:#1a0f00;border:2px solid #d97706;
                                border-radius:12px;padding:16px 20px;margin:12px 0'>
                        <div style='font-family:Space Mono,monospace;color:#fbbf24;
                                    font-weight:700;margin-bottom:8px'>
                            ⚠️ PORTAL FALLBACK — MANUAL UPLOAD REQUIRED
                        </div>
                        <div style='color:#94a3b8;font-size:0.85rem'>
                            Download the CSV below and upload directly to the portal.
                            This file is pre-formatted to match exact portal specifications.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    for portal, data in fallback_csv.items():
                        st.download_button(
                            label=f"⬇ Download {portal} Fallback CSV",
                            data=data["csv"],
                            file_name=data["filename"],
                            mime="text/csv",
                            key=f"dl_{portal}",
                            use_container_width=True,
                        )

                st.session_state.pop("batch_approved", None)
                st.session_state.pop("approved_records", None)

        # ── Always available: manual CSV export ────────────────────────
        st.markdown("---")
        with st.expander("📥 Manual Fallback — Export CSV for Portal Upload"):
            st.markdown(
                "<small style='color:#64748b'>Use this if you prefer to upload manually "
                "or if portals are unavailable.</small>",
                unsafe_allow_html=True
            )
            col_csv1, col_csv2 = st.columns(2)
            with col_csv1:
                if st.button("Generate KenTrade CSV", use_container_width=True):
                    approved = st.session_state.get("approved_records", [])
                    if approved:
                        csv_data = generate_kentrade_csv(approved)
                        st.download_button(
                            "⬇ Download KenTrade CSV",
                            data=csv_data,
                            file_name=f"kentrade_upload_{datetime.date.today()}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No approved records. Run Pre-Audit Gate first.")
            with col_csv2:
                if st.button("Generate KEPHIS CSV", use_container_width=True):
                    approved = st.session_state.get("approved_records", [])
                    if approved:
                        csv_data = generate_kephis_csv(approved)
                        st.download_button(
                            "⬇ Download KEPHIS CSV",
                            data=csv_data,
                            file_name=f"kephis_upload_{datetime.date.today()}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No approved records. Run Pre-Audit Gate first.")

        log = load_transmission_log_db(company=profile.get("company",""))
        if log:
            st.markdown("---")
            st.markdown("<div class='section-header'>TRANSMISSION LOG</div>",
                        unsafe_allow_html=True)
            log_df = pd.DataFrame(log)
            if "batch_reference" in log_df.columns:
                batch_options = ["All Batches"] + sorted(
                    [b for b in log_df["batch_reference"].dropna().unique() if b], reverse=True
                )
                selected_batch = st.selectbox("Filter by batch", batch_options)
                if selected_batch != "All Batches":
                    log_df = log_df[log_df["batch_reference"] == selected_batch]
            st.dataframe(log_df, use_container_width=True)

elif page == "🌱 Carbon Tracking":
    st.markdown("# 🌱 Sustainability & Carbon Metrics")
    from supabase_db import load_ledger_db as _load_ledger_db
    _company = profile.get("company","")
    df = pd.DataFrame(_load_ledger_db(_company))
    tw = df["weight_kg"].astype(float).sum() if not df.empty and "weight_kg" in df.columns else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Estimated Carbon Footprint", f"{round(tw*0.0021,3)} MT CO₂")
    col2.metric("Total Produce Tracked (KG)", f"{tw:,.0f}")
    col3.metric("Consignments", len(df))
    st.markdown("---")
    st.markdown("**Carbon Method:** 2.1g CO₂ per kg tracked.\n\n**Coming:** NASA POWER API climate flags · ESP32 IoT.")

elif page == "📈 KPI Dashboard":
    render_kpi_dashboard(profile)

elif page == "🔑 Invite Codes":
    st.markdown("# 🔑 Invite Code Manager")
    st.markdown("<p style='color:#64748b'>Generate and track invite codes for new users</p>", unsafe_allow_html=True)
    if profile.get("role") != "admin":
        st.error("🔒 Admin only.")
        st.stop()
    st.markdown("---")
    st.markdown("### Generate New Code")
    col_m, col_r, col_g = st.columns([2,2,1])
    with col_m:
        mod_filter = st.selectbox("Module", ["All"] + list(MODULE_ROLE_MAP.keys()))
    with col_r:
        role_options = list(ROLE_PREFIXES.keys()) if mod_filter == "All" else MODULE_ROLE_MAP[mod_filter]
        new_role = st.selectbox("Role", role_options)
    with col_g:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Generate Code", use_container_width=True, type="primary"):
            code = generate_invite_code(new_role, created_by=profile["username"])
            st.success("✅ New code generated:")
            st.code(code, language=None)
    st.markdown("---")
    st.markdown("### All Invite Codes")
    codes_list = list_invite_codes()
    if codes_list:
        st.dataframe(pd.DataFrame(codes_list), use_container_width=True, hide_index=True)
    else:
        st.info("No codes generated yet.")

elif page == "🏢 Company Profile":
    render_company_profile_page(profile)

elif page == "👥 My Team":
    from my_team import render_my_team
    render_my_team(profile)

elif page == "🗑 Demo Reset":
    st.markdown("# 🗑 Demo Reset")
    st.markdown("<p style='color:#64748b'>Wipe your company data for a clean demo</p>", unsafe_allow_html=True)
    if profile.get("role") not in ("exporter","admin","agronomist","record_keeper"):
        st.error("🔒 Access restricted.")
        st.stop()
    company = profile.get("company","")
    st.markdown("---")
    st.markdown(f"""
    <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:12px;
                padding:20px 24px;margin-bottom:20px'>
        <div style='font-size:1rem;font-weight:700;color:#f87171'>⚠ DANGER ZONE</div>
        <div style='color:#94a3b8;margin-top:6px;font-size:0.9rem'>
            This will permanently delete all consignment and ledger records for
            <b style='color:#e8eaf0'>{company}</b>.<br>
            Farmer registrations and user accounts are NOT deleted.
        </div>
    </div>
    """, unsafe_allow_html=True)
    confirm = st.text_input(f"Type your company name to confirm: **{company}**")
    if st.button("🗑 Delete All Company Data", use_container_width=True):
        if confirm.strip().lower() == company.strip().lower():
            from ledger_db import clear_company_ledger
            from db import clear_company_consignments
            n1 = clear_company_ledger(company)
            n2 = clear_company_consignments(company)
            if "ledger_data" in st.session_state:
                del st.session_state["ledger_data"]
            st.success(f"✅ Deleted {n1} ledger + {n2} consignment records. Ready for demo.")
            st.rerun()
        else:
            st.error("❌ Company name does not match. No data deleted.")

elif page == "🆘 Support":
    render_support_page(profile)

elif page == "🗺 Origin Map":
    st.markdown("# 🗺 Produce Origin Map")
    from supabase_db import load_ledger_db as _load_ledger_db
    _company = profile.get("company","")
    df = pd.DataFrame(_load_ledger_db(_company))
    if not df.empty:
        import random
        map_data = []
        for _, row in df.iterrows():
            _c = row.get("county", row.get("Origin_County",""))
            coords = COUNTY_COORDS.get(_c,(-0.0236,37.9062))
            map_data.append({
                "lat": coords[0] + random.uniform(-0.05,0.05),
                "lon": coords[1] + random.uniform(-0.05,0.05)
            })
        st.map(pd.DataFrame(map_data), zoom=5)
        st.markdown("---")
        _grp_county = "county" if "county" in df.columns else "Origin_County" if "Origin_County" in df.columns else None
        _grp_id     = "session_id" if "session_id" in df.columns else "Consignment_ID" if "Consignment_ID" in df.columns else None
        _grp_weight = "weight_kg" if "weight_kg" in df.columns else "Net_Weight_KG" if "Net_Weight_KG" in df.columns else None
        if _grp_county and _grp_id and _grp_weight:
            county_summary = df.groupby(_grp_county).agg(
                Consignments=(_grp_id,"count"),
                Total_Weight=(_grp_weight,"sum"),
            ).reset_index()
            if not county_summary.empty:
                st.dataframe(county_summary, use_container_width=True)
    else:
        st.info("No data yet.")
        st.map(pd.DataFrame({"lat":[-0.0236],"lon":[37.9062]}), zoom=5)

elif page == "📸 Farm Activities":
    st.markdown("# 📸 Farm Activities")
    st.info("Farmer mobile view — coming soon.")

# ── LIVESTOCK PAGES ────────────────────────────────────────────────────────
elif page == "📊 Farm Overview":
    render_admin_overview(profile)

elif page == "🐄 Animal Registry":
    render_animal_registry(profile)

elif page == "🐄 My Herd":
    render_animal_registry(profile)

elif page == "🌡 Temperature Entry":
    render_temp_monitoring(profile)

elif page == "🌡 Health Monitoring":
    render_temp_monitoring(profile)

elif page == "📋 Daily Symptom Log":
    render_symptom_log(profile)

elif page == "📋 Daily Reports":
    render_symptom_log(profile)

elif page == "🧪 Disease Probability":
    render_disease_engine(profile)

elif page == "🚨 Clinical Alerts":
    render_vet_dashboard(profile)

elif page == "📋 Patient History":
    render_vet_dashboard(profile)

elif page == "📋 Vet Reports":
    render_vet_dashboard(profile)

elif page == "🌍 My Animals":
    render_diaspora_dashboard(profile)

elif page == "🌡 Health Alerts":
    render_alert_centre(profile)

elif page == "💰 My Earnings":
    render_vet_earnings(profile)

elif page == "💳 Payments & Commissions":
    render_vet_earnings(profile)

elif page == "🔧 Hardware Registry":
    render_hardware_registry(profile)

elif page == "💰 Cost of Production":
    render_cost_entry(profile)

elif page == "🥛 Milk Tracker":
    render_milk_tracker(profile)

elif page == "📈 Farm P&L":
    render_pnl_dashboard(profile)
