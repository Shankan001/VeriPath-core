import streamlit as st
import pandas as pd
import datetime
import re
import io
from db            import load_consignments, save_consignments
from auth          import register_user, login_user
from eudr          import get_eudr_risk, score_dataframe, EUDR_REGULATED_CROPS
from bridge_engine import transmit_consignment, save_transmission_log, load_transmission_log, get_bridge_mode, get_credential_status

st.set_page_config(
    page_title="VeriPath Africa | Enterprise",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0e1a;
    color: #e8eaf0;
}
.stApp { background-color: #0a0e1a; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1224 0%, #111827 100%);
    border-right: 1px solid #1e2d45;
}
section[data-testid="stSidebar"] .stRadio label {
    font-family: 'DM Sans', sans-serif; font-size: 0.9rem;
    color: #94a3b8; padding: 6px 0;
}
section[data-testid="stSidebar"] .stRadio label:hover { color: #38bdf8; }
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #1a2540 100%);
    border: 1px solid #1e3a5f; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 12px; transition: border-color 0.2s;
}
.metric-card:hover { border-color: #38bdf8; }
.metric-label {
    font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.1em; color: #64748b;
    font-family: 'Space Mono', monospace;
}
.metric-value {
    font-size: 1.8rem; font-weight: 700; color: #38bdf8;
    font-family: 'Space Mono', monospace; margin-top: 4px;
}
.auth-logo {
    font-family: 'Space Mono', monospace; font-size: 1.6rem;
    color: #38bdf8; text-align: center; margin-bottom: 6px;
    letter-spacing: 0.1em;
}
.auth-tagline {
    text-align: center; color: #64748b; font-size: 0.85rem;
    margin-bottom: 32px;
}
.section-header {
    font-family: 'Space Mono', monospace; font-size: 1.1rem;
    color: #38bdf8; border-bottom: 1px solid #1e3a5f;
    padding-bottom: 8px; margin-bottom: 20px; letter-spacing: 0.05em;
}
.risk-card { border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; border: 1px solid; }
.risk-high   { background: #1a0a0a; border-color: #dc2626; }
.risk-medium { background: #1a1400; border-color: #d97706; }
.risk-low    { background: #071a0f; border-color: #16a34a; }
.risk-exempt { background: #0d1224; border-color: #334155; }
.portal-card {
    background: #0d1224; border: 1px solid #1e3a5f;
    border-radius: 12px; padding: 16px 20px; margin-bottom: 10px;
}
.portal-success { border-color: #16a34a; background: #071a0f; }
.portal-pending { border-color: #d97706; background: #1a1400; }
.portal-error   { border-color: #dc2626; background: #1a0a0a; }
.mode-badge-sim  { background:#1c2a3a; color:#38bdf8; border:1px solid #1e3a5f;
                   border-radius:20px; padding:3px 12px; font-size:0.75rem;
                   font-family:'Space Mono',monospace; }
.mode-badge-real { background:#071a0f; color:#4ade80; border:1px solid #16a34a;
                   border-radius:20px; padding:3px 12px; font-size:0.75rem;
                   font-family:'Space Mono',monospace; }
.stFileUploader { border: 2px dashed #1e3a5f !important; border-radius: 12px !important; background: #0d1224 !important; }
.stButton > button {
    background: linear-gradient(135deg, #0369a1, #0284c7);
    color: white; border: none; border-radius: 8px;
    font-family: 'Space Mono', monospace; font-size: 0.85rem;
    padding: 10px 24px; transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    transform: translateY(-1px); box-shadow: 0 4px 15px rgba(56,189,248,0.3);
}
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #111827 !important; border: 1px solid #1e3a5f !important;
    border-radius: 8px !important; color: #e8eaf0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stDataFrame { border-radius: 10px; overflow: hidden; }
.stSuccess { background: #052e16 !important; border-left: 4px solid #4ade80 !important; }
.stWarning { background: #1c1400 !important; border-left: 4px solid #fbbf24 !important; }
.stError   { background: #2d0a0a !important; border-left: 4px solid #f87171 !important; }
.user-pill {
    background: #0f2233; border: 1px solid #1e3a5f; border-radius: 20px;
    padding: 8px 14px; font-size: 0.8rem; color: #38bdf8;
    font-family: 'Space Mono', monospace; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

HS_CODE_MAP = {
    "Maize": "1005.90", "Coffee": "0901.11", "Tea": "0902.30",
    "Avocado": "0804.40", "French Beans": "0708.20", "Roses": "0603.11",
    "Macadamia Nuts": "0802.62", "Mango": "0804.50",
    "Pineapple": "0804.30", "Passion Fruit": "0810.90",
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
    "Nairobi": (-1.2921, 36.8219), "Mombasa": (-4.0435, 39.6682),
    "Kisumu": (-0.1022, 34.7617),  "Nakuru":  (-0.3031, 36.0800),
    "Eldoret": (0.5143, 35.2698),  "Kericho": (-0.3686, 35.2863),
    "Narok":  (-1.0836, 35.8716),  "Machakos":(-1.5177, 37.2634),
    "Meru":   (0.0467, 37.6490),   "Kakamega":(0.2827, 34.7519),
    "Nyeri":  (-0.4167, 36.9500),  "Kiambu":  (-1.1714, 36.8353),
    "Murang'a":(-0.7167, 37.1500), "Embu":    (-0.5333, 37.4500),
    "Kirinyaga":(-0.5594, 37.3347),"Nandi":   (0.1833, 35.1167),
    "Uasin Gishu":(0.5500, 35.2667),"Trans Nzoia":(1.0167, 34.9500),
    "Bungoma":(0.5635, 34.5606),   "Kilifi":  (-3.6305, 39.8499),
    "Kwale":  (-4.1740, 39.4520),  "Taita-Taveta":(-3.3167, 38.4833),
}
LEDGER_COLS = [
    'Consignment_ID','Timestamp','Farmer_Name','Crop_Type',
    'KRA_PIN','PIN_Valid','HS_Code','Origin_County',
    'Net_Weight_KG','FOB_Value_USD','Source'
]
KRA_PIN_PATTERN = re.compile(r'^[A-Z]\d{9}[A-Z]$')

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_profile'  not in st.session_state:
    st.session_state['user_profile']  = None
if 'auth_page'     not in st.session_state:
    st.session_state['auth_page']     = 'login'

if not st.session_state['authenticated']:
    st.markdown("<div style='text-align:center;margin-top:60px'>", unsafe_allow_html=True)
    st.markdown("<div class='auth-logo'>▸ VERIPATH AFRICA</div>", unsafe_allow_html=True)
    st.markdown("<div class='auth-tagline'>Kenya Export Compliance Infrastructure</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")
    col_l, col_r = st.columns(2)
    with col_l:
        if st.button("🔑 Sign In", use_container_width=True):
            st.session_state['auth_page'] = 'login'
    with col_r:
        if st.button("📝 Register", use_container_width=True):
            st.session_state['auth_page'] = 'register'
    st.markdown("---")
    if st.session_state['auth_page'] == 'login':
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
                    st.session_state['authenticated'] = True
                    st.session_state['user_profile']  = profile
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        st.markdown("<br><small style='color:#64748b'>No account? Click Register above.</small>", unsafe_allow_html=True)
    else:
        st.markdown("### Create Your Account")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *", placeholder="Joseph Memusi")
                username  = st.text_input("Username *",  placeholder="josephm")
            with col2:
                company   = st.text_input("Company *",   placeholder="VeriPath Africa")
                role      = st.selectbox("Role", ["exporter","agronomist","admin","auditor"])
            password  = st.text_input("Password *",         type="password", placeholder="Min. 8 characters")
            password2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
            submit    = st.form_submit_button("Create Account →", use_container_width=True)
        if submit:
            errors = []
            if not full_name.strip(): errors.append("Full Name is required")
            if not username.strip():  errors.append("Username is required")
            if not company.strip():   errors.append("Company is required")
            if not password:          errors.append("Password is required")
            if password != password2: errors.append("Passwords do not match")
            if errors:
                for e in errors: st.error(f"❌ {e}")
            else:
                ok, msg = register_user(username, password, full_name, company, role)
                if ok:
                    st.success(f"✅ {msg} You can now sign in.")
                    st.session_state['auth_page'] = 'login'
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        st.markdown("<br><small style='color:#64748b'>Already have an account? Click Sign In above.</small>", unsafe_allow_html=True)
    st.stop()

if 'ledger_data' not in st.session_state:
    saved = load_consignments()
    if saved:
        df_saved = pd.DataFrame(saved)
        st.session_state['ledger_data'] = df_saved[
            [c for c in LEDGER_COLS if c in df_saved.columns]
        ]
    else:
        st.session_state['ledger_data'] = pd.DataFrame(columns=LEDGER_COLS)

def validate_kra_pin(pin: str) -> tuple[bool, str]:
    pin = pin.strip().upper()
    if not pin or pin in ("PENDING", "N/A", ""):
        return False, "Missing"
    return (True, pin) if KRA_PIN_PATTERN.match(pin) else (False, pin)

def get_hs_code(crop: str) -> str:
    return HS_CODE_MAP.get(crop, "UNKNOWN")

def parse_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file), None
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file), None
        elif name.endswith(".docx"):
            try:
                import docx
                doc  = docx.Document(uploaded_file)
                rows = []
                for table in doc.tables:
                    headers = [c.text.strip() for c in table.rows[0].cells]
                    for row in table.rows[1:]:
                        rows.append({headers[i]: row.cells[i].text.strip()
                                     for i in range(len(headers))})
                return (pd.DataFrame(rows), None) if rows else (None, "No tables found.")
            except ImportError:
                return None, "python-docx not installed."
        else:
            return None, f"Unsupported: {name.split('.')[-1].upper()}"
    except Exception as e:
        return None, str(e)

def validate_and_append(df_new: pd.DataFrame, source: str):
    valid_rows, error_rows = [], []
    for _, row in df_new.iterrows():
        crop    = str(row.get("Crop_Type",     row.get("crop_type",     "Unknown"))).strip().title()
        pin_raw = str(row.get("KRA_PIN",       row.get("kra_pin",       "PENDING"))).strip()
        weight  = float(row.get("Net_Weight",  row.get("net_weight",    row.get("Net_Weight_KG", 0))) or 0)
        county  = str(row.get("Origin_County", row.get("origin_county", "Unknown"))).strip().title()
        farmer  = str(row.get("Farmer_Name",   row.get("farmer_name",   "Unknown"))).strip()
        pin_ok, pin_clean = validate_kra_pin(pin_raw)
        entry = {
            "Consignment_ID": f"VP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]}",
            "Timestamp":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Farmer_Name":    farmer,
            "Crop_Type":      crop,
            "KRA_PIN":        pin_clean,
            "PIN_Valid":      "✅ Valid" if pin_ok else "⚠ Pending",
            "HS_Code":        get_hs_code(crop),
            "Origin_County":  county,
            "Net_Weight_KG":  weight,
            "FOB_Value_USD":  round(weight * 1.5, 2),
            "Source":         source,
        }
        if not farmer or farmer == "Unknown":
            entry["_error"] = "Missing Farmer Name"
            error_rows.append(entry)
        else:
            valid_rows.append(entry)
    return valid_rows, error_rows

profile = st.session_state['user_profile']
st.sidebar.markdown("## 🏗 VeriPath Enterprise")
st.sidebar.markdown(
    f"<div class='user-pill'>👤 {profile['full_name']}<br>"
    f"<span style='color:#64748b;font-size:0.7rem'>{profile['company']} · {profile['role']}</span></div>",
    unsafe_allow_html=True
)
st.sidebar.markdown("---")
page = st.sidebar.radio("", [
    "📊 Dashboard",
    "📤 Data Ingestion",
    "📑 Consignment Ledger",
    "🚜 Farmer Manual Entry",
    "🌿 EUDR Risk Engine",
    "📡 Transmit to Portals",
    "🌱 Carbon Tracking",
    "🗺 Origin Map",
])
total_entries = len(st.session_state['ledger_data'])
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<small style='color:#64748b'>Ledger entries: <b style='color:#38bdf8'>{total_entries}</b></small>",
    unsafe_allow_html=True
)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state['authenticated'] = False
    st.session_state['user_profile']  = None
    st.session_state['auth_page']     = 'login'
    st.rerun()

if page == "📊 Dashboard":
    st.markdown("# 📊 VeriPath Dashboard")
    st.markdown("<p style='color:#64748b'>Real-time supply chain intelligence</p>", unsafe_allow_html=True)
    df = st.session_state['ledger_data']
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Consignments</div>
            <div class='metric-value'>{len(df)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        tw = df['Net_Weight_KG'].astype(float).sum() if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Weight (KG)</div>
            <div class='metric-value'>{tw:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        tf = df['FOB_Value_USD'].astype(float).sum() if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total FOB Value</div>
            <div class='metric-value'>${tf:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        vp = df[df['PIN_Valid'] == "✅ Valid"].shape[0] if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Verified PINs</div>
            <div class='metric-value'>{vp}</div>
        </div>""", unsafe_allow_html=True)
    if not df.empty:
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("<div class='section-header'>CONSIGNMENTS BY CROP</div>", unsafe_allow_html=True)
            cc = df['Crop_Type'].value_counts().reset_index()
            cc.columns = ['Crop', 'Count']
            st.bar_chart(cc.set_index('Crop'))
        with col_b:
            st.markdown("<div class='section-header'>FOB VALUE BY COUNTY</div>", unsafe_allow_html=True)
            cf = df.groupby('Origin_County')['FOB_Value_USD'].sum().reset_index()
            cf.columns = ['County', 'FOB_USD']
            st.bar_chart(cf.set_index('County'))
    else:
        st.info("No data yet. Add entries via Farmer Manual Entry or Data Ingestion.")

elif page == "📤 Data Ingestion":
    st.markdown("# 📤 Bulk Data Ingestion")
    uploaded_file = st.file_uploader("Drop file here", type=["csv","xlsx","xls","docx"])
    if uploaded_file:
        st.markdown(f"**File:** `{uploaded_file.name}` ({uploaded_file.size/1024:.1f} KB)")
        df_raw, err = parse_uploaded_file(uploaded_file)
        if err:
            st.error(f"❌ {err}")
        elif df_raw is not None and not df_raw.empty:
            st.markdown("#### Preview (raw)")
            st.dataframe(df_raw.head(10), use_container_width=True)
            if st.button("✅ Validate & Import to Ledger"):
                valid_rows, error_rows = validate_and_append(df_raw, f"Upload:{uploaded_file.name}")
                if valid_rows:
                    new_df = pd.DataFrame(valid_rows)
                    st.session_state['ledger_data'] = pd.concat(
                        [st.session_state['ledger_data'], new_df], ignore_index=True
                    )
                    save_consignments(st.session_state['ledger_data'].to_dict('records'))
                    st.success(f"✅ {len(valid_rows)} records imported and saved.")
                if error_rows:
                    st.warning(f"⚠ {len(error_rows)} rows skipped:")
                    st.dataframe(pd.DataFrame(error_rows)[['Farmer_Name','Crop_Type','_error']], use_container_width=True)
        else:
            st.warning("File appears empty.")

elif page == "📑 Consignment Ledger":
    st.markdown("# 📑 Global Consignment Ledger")
    df = st.session_state['ledger_data']
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Consignments", len(df))
        col2.metric("Total Weight (KG)", f"{df['Net_Weight_KG'].astype(float).sum():,.0f}")
        col3.metric("Total FOB Value",   f"${df['FOB_Value_USD'].astype(float).sum():,.2f}")
        st.markdown("---")
        with st.expander("🔍 Filter Ledger"):
            fc1, fc2 = st.columns(2)
            with fc1:
                crop_filter   = st.multiselect("Crop Type",     options=df['Crop_Type'].unique().tolist())
            with fc2:
                county_filter = st.multiselect("Origin County", options=df['Origin_County'].unique().tolist())
        display_df = df.copy()
        if crop_filter:   display_df = display_df[display_df['Crop_Type'].isin(crop_filter)]
        if county_filter: display_df = display_df[display_df['Origin_County'].isin(county_filter)]
        st.markdown(f"<div class='section-header'>UNIFIED REGULATORY TABLE — {len(display_df)} RECORDS</div>", unsafe_allow_html=True)
        st.dataframe(display_df.drop(columns=['_error'], errors='ignore'), use_container_width=True)
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇ Export as CSV", data=csv_data,
                           file_name=f"veripath_ledger_{datetime.date.today()}.csv", mime="text/csv")
    else:
        st.warning("Ledger is empty.")

elif page == "🚜 Farmer Manual Entry":
    st.markdown("# 🚜 Field Data Entry")
    with st.form("farmer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_name   = st.text_input("Farmer Name *")
            f_crop   = st.selectbox("Produce Type *", list(HS_CODE_MAP.keys()))
            f_weight = st.number_input("Net Weight (KG) *", min_value=0.0, step=0.5)
        with col2:
            f_county = st.selectbox("Origin County *", KENYAN_COUNTIES)
            f_pin    = st.text_input("KRA PIN", placeholder="e.g. A123456789B")
            f_phone  = st.text_input("Farmer Phone (Optional)", placeholder="+254...")
        st.markdown("---")
        submitted = st.form_submit_button("📋 Validate & Log to Ledger", use_container_width=True)
    if submitted:
        errors = []
        if not f_name.strip(): errors.append("Farmer Name is required")
        if f_weight <= 0:      errors.append("Net Weight must be greater than 0")
        pin_ok, pin_clean = validate_kra_pin(f_pin)
        if errors:
            for e in errors: st.error(f"❌ {e}")
        else:
            hs   = get_hs_code(f_crop)
            fob  = round(f_weight * 1.5, 2)
            eudr = get_eudr_risk(f_crop, f_county)
            new_entry = {
                "Consignment_ID": f"VP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                "Timestamp":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Farmer_Name":    f_name.strip(),
                "Crop_Type":      f_crop,
                "KRA_PIN":        pin_clean,
                "PIN_Valid":      "✅ Valid" if pin_ok else "⚠ Pending",
                "HS_Code":        hs,
                "Origin_County":  f_county,
                "Net_Weight_KG":  f_weight,
                "FOB_Value_USD":  fob,
                "Source":         f"Manual Entry — {profile['username']}",
            }
            st.session_state['ledger_data'] = pd.concat(
                [st.session_state['ledger_data'], pd.DataFrame([new_entry])],
                ignore_index=True
            )
            save_consignments(st.session_state['ledger_data'].to_dict('records'))
            st.balloons()
            st.success(f"✅ Entry logged for **{f_name}** — {f_crop} from {f_county}")
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"**HS Code:** {hs}")
            c2.info(f"**FOB Value:** ${fob:,.2f}")
            c3.info(f"**PIN:** {'✅ Verified' if pin_ok else '⚠ Pending'}")
            c4.info(f"**EUDR:** {eudr['badge']}")

elif page == "🌿 EUDR Risk Engine":
    st.markdown("# 🌿 EUDR Risk Engine")
    st.markdown("<p style='color:#64748b'>EU Deforestation Regulation (2023/1115) compliance scoring</p>", unsafe_allow_html=True)
    df = st.session_state['ledger_data']
    if df.empty:
        st.warning("No consignments to score. Add entries first.")
    else:
        scored_df    = score_dataframe(df)
        high_count   = (scored_df['EUDR_Risk'].str.contains('High',   na=False)).sum()
        medium_count = (scored_df['EUDR_Risk'].str.contains('Medium', na=False)).sum()
        low_count    = (scored_df['EUDR_Risk'].str.contains('Low',    na=False)).sum()
        exempt_count = (scored_df['EUDR_Risk'].str.contains('Exempt', na=False)).sum()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class='metric-card' style='border-color:#dc2626'>
                <div class='metric-label'>High Risk</div>
                <div class='metric-value' style='color:#f87171'>{high_count}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class='metric-card' style='border-color:#d97706'>
                <div class='metric-label'>Medium Risk</div>
                <div class='metric-value' style='color:#fbbf24'>{medium_count}</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class='metric-card' style='border-color:#16a34a'>
                <div class='metric-label'>Low Risk</div>
                <div class='metric-value' style='color:#4ade80'>{low_count}</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Exempt</div>
                <div class='metric-value' style='color:#94a3b8'>{exempt_count}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div class='section-header'>QUICK CONSIGNMENT SCANNER</div>", unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        with sc1:
            scan_crop   = st.selectbox("Crop",   list(HS_CODE_MAP.keys()), key="scan_crop")
        with sc2:
            scan_county = st.selectbox("County", KENYAN_COUNTIES,          key="scan_county")
        result     = get_eudr_risk(scan_crop, scan_county)
        risk_class = {"High":"risk-high","Medium":"risk-medium","Low":"risk-low","Exempt":"risk-exempt"}.get(result["risk_level"],"risk-low")
        st.markdown(f"""
        <div class='risk-card {risk_class}'>
            <div style='font-size:1.4rem;font-weight:700;font-family:Space Mono,monospace'>{result['badge']}</div>
            <div style='color:#94a3b8;font-size:0.85rem;margin-top:6px'>{result['explanation']}</div>
            <div style='color:#e8eaf0;font-size:0.9rem;margin-top:10px'>⚡ <b>Required action:</b> {result['action']}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div class='section-header'>FULL RISK ASSESSMENT TABLE</div>", unsafe_allow_html=True)
        risk_filter  = st.multiselect("Filter by risk level",
            options=["🔴 High Risk","🟡 Medium Risk","🟢 Low Risk","⚪ Exempt"], default=[])
        display_cols = ['Consignment_ID','Farmer_Name','Crop_Type','Origin_County',
                        'Net_Weight_KG','EUDR_Risk','EUDR_Score','EUDR_Action']
        show_df = scored_df[[c for c in display_cols if c in scored_df.columns]]
        if risk_filter:
            show_df = show_df[show_df['EUDR_Risk'].isin(risk_filter)]
        st.dataframe(show_df, use_container_width=True)
        csv_eudr = show_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇ Export EUDR Report", data=csv_eudr,
            file_name=f"veripath_eudr_{datetime.date.today()}.csv", mime="text/csv")

elif page == "📡 Transmit to Portals":
    st.markdown("# 📡 Transmit to Government Portals")
    st.markdown("<p style='color:#64748b'>Submit consignment data to KenTrade, KEPHIS, and AFA IMIS</p>", unsafe_allow_html=True)

    # ── Mode banner
    mode       = get_bridge_mode()
    cred_status = get_credential_status()
    if mode == "simulation":
        st.markdown("<span class='mode-badge-sim'>⚙ SIMULATION MODE — no real submissions</span>", unsafe_allow_html=True)
        st.markdown("<small style='color:#64748b'>To enable real submissions: copy `.env.example` to `.env` and add credentials, then set `BRIDGE_MODE=real`</small>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='mode-badge-real'>🟢 LIVE MODE — real portal submissions active</span>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Credential status
    with st.expander("🔑 Portal Credential Status"):
        for portal, loaded in cred_status.items():
            icon = "✅" if loaded else "⚠️"
            color = "#4ade80" if loaded else "#fbbf24"
            st.markdown(f"<span style='color:{color}'>{icon} {portal} — {'Credentials loaded' if loaded else 'No credentials — simulation only'}</span>", unsafe_allow_html=True)

    st.markdown("---")

    df = st.session_state['ledger_data']
    if df.empty:
        st.warning("No consignments in ledger. Add entries first.")
    else:
        st.markdown("<div class='section-header'>SELECT CONSIGNMENT TO TRANSMIT</div>", unsafe_allow_html=True)
        consignment_options = df['Consignment_ID'].tolist()
        selected_ids = st.multiselect(
            "Select consignments",
            options=consignment_options,
            default=[consignment_options[-1]] if consignment_options else []
        )
        portal_options = st.multiselect(
            "Target portals",
            options=["KenTrade", "KEPHIS", "AFA IMIS"],
            default=["KenTrade", "KEPHIS", "AFA IMIS"]
        )
        st.markdown("---")

        if selected_ids and portal_options:
            selected_rows = df[df['Consignment_ID'].isin(selected_ids)]
            st.markdown("**Selected consignments:**")
            st.dataframe(
                selected_rows[['Consignment_ID','Farmer_Name','Crop_Type','Origin_County','Net_Weight_KG']],
                use_container_width=True
            )
            st.markdown("---")

            if st.button(f"📡 Transmit {len(selected_ids)} Consignment(s) to {len(portal_options)} Portal(s)", use_container_width=True):
                all_results = []
                progress = st.progress(0)
                total    = len(selected_ids) * len(portal_options)
                done     = 0
                for _, row in selected_rows.iterrows():
                    consignment = row.to_dict()
                    with st.spinner(f"Transmitting {consignment['Consignment_ID']}..."):
                        results = transmit_consignment(consignment, portal_options)
                        all_results.extend(results)
                        for r in results:
                            done += 1
                            progress.progress(done / total)
                save_transmission_log(all_results)
                st.markdown("### Transmission Results")
                for r in all_results:
                    status_class = {
                        "submitted": "portal-success",
                        "pending":   "portal-pending",
                        "error":     "portal-error",
                    }.get(r.get("status",""), "portal-card")
                    mode_label = "🔵 SIM" if r.get("mode") == "simulation" else "🟢 LIVE"
                    st.markdown(f"""
                    <div class='portal-card {status_class}'>
                        <b style='font-family:Space Mono,monospace'>{r['portal']}</b>
                        <span style='float:right;font-size:0.75rem;color:#64748b'>{mode_label}</span><br>
                        <span style='color:#94a3b8;font-size:0.8rem'>Ref: {r.get('reference','—')}</span><br>
                        <span style='font-size:0.9rem'>{r.get('message','')}</span><br>
                        <span style='color:#64748b;font-size:0.75rem'>{r.get('submitted_at','')}</span>
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("Select at least one consignment and one portal.")

    st.markdown("---")
    st.markdown("<div class='section-header'>TRANSMISSION LOG</div>", unsafe_allow_html=True)
    log = load_transmission_log()
    if log:
        log_df = pd.DataFrame(log)[['consignment','portal','mode','status','reference','submitted_at']]
        st.dataframe(log_df, use_container_width=True)
        csv_log = log_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇ Export Transmission Log", data=csv_log,
            file_name=f"veripath_transmissions_{datetime.date.today()}.csv", mime="text/csv")
    else:
        st.info("No transmissions yet.")

elif page == "🌱 Carbon Tracking":
    st.markdown("# 🌱 Sustainability & Carbon Metrics")
    df = st.session_state['ledger_data']
    tw = df['Net_Weight_KG'].astype(float).sum() if not df.empty else 0
    carbon_est = round(tw * 0.0021, 3)
    col1, col2, col3 = st.columns(3)
    col1.metric("Estimated Carbon Footprint", f"{carbon_est} MT CO₂")
    col2.metric("Total Produce Tracked (KG)", f"{tw:,.0f}")
    col3.metric("Green-Light Ready", f"{len(df)} consignments")
    st.markdown("---")
    st.markdown("""
**Carbon Calculation Method:** Emissions estimated at **2.1g CO₂ per kg** tracked.

**Coming Soon:** NASA POWER API climate flags · ESP32 IoT integration · EUDR deforestation scoring
    """)

elif page == "🗺 Origin Map":
    st.markdown("# 🗺 Produce Origin Map")
    df = st.session_state['ledger_data']
    if not df.empty:
        import random
        map_data = []
        for _, row in df.iterrows():
            coords = COUNTY_COORDS.get(row['Origin_County'], (-0.0236, 37.9062))
            map_data.append({
                "lat": coords[0] + random.uniform(-0.05, 0.05),
                "lon": coords[1] + random.uniform(-0.05, 0.05),
            })
        st.map(pd.DataFrame(map_data), zoom=5)
        st.markdown("---")
        county_summary = df.groupby('Origin_County').agg(
            Consignments=('Consignment_ID','count'),
            Total_Weight=('Net_Weight_KG','sum'),
            Total_FOB=('FOB_Value_USD','sum')
        ).reset_index()
        st.markdown("<div class='section-header'>COUNTY SUMMARY</div>", unsafe_allow_html=True)
        st.dataframe(county_summary, use_container_width=True)
    else:
        st.info("No data yet.")
        st.map(pd.DataFrame({'lat': [-0.0236], 'lon': [37.9062]}), zoom=5)
