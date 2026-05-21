import streamlit as st
import pandas as pd
import datetime
import re
import io

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VeriPath Africa | Enterprise",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0e1a;
    color: #e8eaf0;
}
.stApp { background-color: #0a0e1a; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1224 0%, #111827 100%);
    border-right: 1px solid #1e2d45;
}
section[data-testid="stSidebar"] .stRadio label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    color: #94a3b8;
    padding: 6px 0;
}
section[data-testid="stSidebar"] .stRadio label:hover { color: #38bdf8; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #1a2540 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #38bdf8; }
.metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    font-family: 'Space Mono', monospace;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #38bdf8;
    font-family: 'Space Mono', monospace;
    margin-top: 4px;
}

/* Status badges */
.badge-valid {
    background: #052e16;
    color: #4ade80;
    border: 1px solid #16a34a;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-family: 'Space Mono', monospace;
}
.badge-error {
    background: #2d0a0a;
    color: #f87171;
    border: 1px solid #dc2626;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-family: 'Space Mono', monospace;
}

/* Section headers */
.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    color: #38bdf8;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 8px;
    margin-bottom: 20px;
    letter-spacing: 0.05em;
}

/* Upload area */
.stFileUploader {
    border: 2px dashed #1e3a5f !important;
    border-radius: 12px !important;
    background: #0d1224 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0369a1, #0284c7);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    padding: 10px 24px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3);
}

/* Form inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Validation messages */
.validate-ok { color: #4ade80; font-size: 0.8rem; font-family: 'Space Mono', monospace; }
.validate-err { color: #f87171; font-size: 0.8rem; font-family: 'Space Mono', monospace; }

/* Dataframe */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Alert boxes */
.stSuccess { background: #052e16 !important; border-left: 4px solid #4ade80 !important; }
.stWarning { background: #1c1400 !important; border-left: 4px solid #fbbf24 !important; }
.stError { background: #2d0a0a !important; border-left: 4px solid #f87171 !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
HS_CODE_MAP = {
    "Maize":          "1005.90",
    "Coffee":         "0901.11",
    "Tea":            "0902.30",
    "Avocado":        "0804.40",
    "French Beans":   "0708.20",
    "Roses":          "0603.11",
    "Macadamia Nuts": "0802.62",
    "Mango":          "0804.50",
    "Pineapple":      "0804.30",
    "Passion Fruit":  "0810.90",
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
    "Kisumu": (-0.1022, 34.7617), "Nakuru": (-0.3031, 36.0800),
    "Eldoret": (0.5143, 35.2698), "Kericho": (-0.3686, 35.2863),
    "Narok": (-1.0836, 35.8716), "Machakos": (-1.5177, 37.2634),
    "Meru": (0.0467, 37.6490), "Kakamega": (0.2827, 34.7519),
    "Nyeri": (-0.4167, 36.9500), "Kiambu": (-1.1714, 36.8353),
    "Murang'a": (-0.7167, 37.1500), "Embu": (-0.5333, 37.4500),
    "Kirinyaga": (-0.5594, 37.3347), "Nandi": (0.1833, 35.1167),
    "Uasin Gishu": (0.5500, 35.2667), "Trans Nzoia": (1.0167, 34.9500),
    "Bungoma": (0.5635, 34.5606), "Kilifi": (-3.6305, 39.8499),
    "Kwale": (-4.1740, 39.4520), "Taita-Taveta": (-3.3167, 38.4833),
}

KRA_PIN_PATTERN = re.compile(r'^[A-Z]\d{9}[A-Z]$')

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if 'ledger_data' not in st.session_state:
    cols = ['Consignment_ID','Timestamp','Farmer_Name','Crop_Type',
            'KRA_PIN','PIN_Valid','HS_Code','Origin_County',
            'Net_Weight_KG','FOB_Value_USD','Source']
    st.session_state['ledger_data'] = pd.DataFrame(columns=cols)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def validate_kra_pin(pin: str) -> tuple[bool, str]:
    pin = pin.strip().upper()
    if not pin or pin in ("PENDING", "N/A", ""):
        return False, "Missing"
    if KRA_PIN_PATTERN.match(pin):
        return True, pin
    return False, pin

def get_hs_code(crop: str) -> str:
    return HS_CODE_MAP.get(crop, "UNKNOWN")

def parse_uploaded_file(uploaded_file):
    """Parse CSV, Excel, or Word-exported files into a DataFrame."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file), None
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file), None
        elif name.endswith(".docx"):
            try:
                import docx
                doc = docx.Document(uploaded_file)
                rows = []
                for table in doc.tables:
                    headers = [c.text.strip() for c in table.rows[0].cells]
                    for row in table.rows[1:]:
                        rows.append({headers[i]: row.cells[i].text.strip()
                                     for i in range(len(headers))})
                if rows:
                    return pd.DataFrame(rows), None
                return None, "No tables found in Word document."
            except ImportError:
                return None, "python-docx not installed. Add `python-docx` to requirements.txt."
        else:
            return None, f"Unsupported file type: {name.split('.')[-1].upper()}"
    except Exception as e:
        return None, str(e)

def validate_and_append(df_new: pd.DataFrame, source: str):
    """Validate incoming DataFrame rows and append to ledger."""
    valid_rows, error_rows = [], []
    for _, row in df_new.iterrows():
        crop = str(row.get("Crop_Type", row.get("crop_type", "Unknown"))).strip().title()
        pin_raw = str(row.get("KRA_PIN", row.get("kra_pin", "PENDING"))).strip()
        pin_ok, pin_clean = validate_kra_pin(pin_raw)
        weight = float(row.get("Net_Weight", row.get("net_weight", row.get("Net_Weight_KG", 0))) or 0)
        county = str(row.get("Origin_County", row.get("origin_county", "Unknown"))).strip().title()
        farmer = str(row.get("Farmer_Name", row.get("farmer_name", "Unknown"))).strip()
        entry = {
            "Consignment_ID": f"VP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:16]}",
            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Farmer_Name": farmer,
            "Crop_Type": crop,
            "KRA_PIN": pin_clean,
            "PIN_Valid": "✅ Valid" if pin_ok else "⚠️ Pending",
            "HS_Code": get_hs_code(crop),
            "Origin_County": county,
            "Net_Weight_KG": weight,
            "FOB_Value_USD": round(weight * 1.5, 2),
            "Source": source,
        }
        if not farmer or farmer == "Unknown":
            entry["_error"] = "Missing Farmer Name"
            error_rows.append(entry)
        else:
            valid_rows.append(entry)
    return valid_rows, error_rows

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🏗️ VeriPath Enterprise")
st.sidebar.markdown("<small style='color:#64748b'>Mission Control</small>", unsafe_allow_html=True)
st.sidebar.markdown("---")

page = st.sidebar.radio("", [
    "📊 Dashboard",
    "📤 Data Ingestion",
    "📑 Consignment Ledger",
    "🚜 Farmer Manual Entry",
    "🌱 Carbon Tracking",
    "🗺️ Origin Map",
])

total_entries = len(st.session_state['ledger_data'])
st.sidebar.markdown("---")
st.sidebar.markdown(f"<small style='color:#64748b'>Ledger entries: <b style='color:#38bdf8'>{total_entries}</b></small>", unsafe_allow_html=True)

# ── PAGE: DASHBOARD ───────────────────────────────────────────────────────────
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
        total_weight = df['Net_Weight_KG'].astype(float).sum() if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Weight (KG)</div>
            <div class='metric-value'>{total_weight:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        total_fob = df['FOB_Value_USD'].astype(float).sum() if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total FOB Value</div>
            <div class='metric-value'>${total_fob:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        valid_pins = df[df['PIN_Valid'] == "✅ Valid"].shape[0] if not df.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Verified PINs</div>
            <div class='metric-value'>{valid_pins}</div>
        </div>""", unsafe_allow_html=True)

    if not df.empty:
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("<div class='section-header'>CONSIGNMENTS BY CROP</div>", unsafe_allow_html=True)
            crop_counts = df['Crop_Type'].value_counts().reset_index()
            crop_counts.columns = ['Crop', 'Count']
            st.bar_chart(crop_counts.set_index('Crop'))
        with col_b:
            st.markdown("<div class='section-header'>FOB VALUE BY COUNTY</div>", unsafe_allow_html=True)
            county_fob = df.groupby('Origin_County')['FOB_Value_USD'].sum().reset_index()
            county_fob.columns = ['County', 'FOB_USD']
            st.bar_chart(county_fob.set_index('County'))
    else:
        st.info("No data yet. Add entries via Farmer Manual Entry or Data Ingestion.")

# ── PAGE: DATA INGESTION ──────────────────────────────────────────────────────
elif page == "📤 Data Ingestion":
    st.markdown("# 📤 Bulk Data Ingestion")
    st.markdown("<p style='color:#64748b'>Upload CSV, Excel (.xlsx/.xls), or Word (.docx) files</p>", unsafe_allow_html=True)

    st.markdown("""
    **Supported formats:**
    - 📄 **CSV** — standard comma-separated
    - 📊 **Excel** — .xlsx or .xls (WPS Spreadsheets export to .xlsx)
    - 📝 **Word / WPS Writer** — .docx with data tables

    **Required columns:** `Farmer_Name`, `Crop_Type`, `Net_Weight`, `Origin_County`, `KRA_PIN` *(optional)*
    """)

    uploaded_file = st.file_uploader(
        "Drop file here or click to browse",
        type=["csv", "xlsx", "xls", "docx"]
    )

    if uploaded_file:
        st.markdown(f"**File:** `{uploaded_file.name}` ({uploaded_file.size / 1024:.1f} KB)")
        df_raw, err = parse_uploaded_file(uploaded_file)

        if err:
            st.error(f"❌ Could not read file: {err}")
        elif df_raw is not None and not df_raw.empty:
            st.markdown("#### Preview (raw)")
            st.dataframe(df_raw.head(10), use_container_width=True)

            if st.button("✅ Validate & Import to Ledger"):
                valid_rows, error_rows = validate_and_append(df_raw, source=f"Upload:{uploaded_file.name}")
                if valid_rows:
                    new_df = pd.DataFrame(valid_rows)
                    st.session_state['ledger_data'] = pd.concat(
                        [st.session_state['ledger_data'], new_df], ignore_index=True
                    )
                    st.success(f"✅ {len(valid_rows)} records imported to Ledger.")
                if error_rows:
                    st.warning(f"⚠️ {len(error_rows)} records had issues and were skipped:")
                    st.dataframe(pd.DataFrame(error_rows)[['Farmer_Name','Crop_Type','_error']], use_container_width=True)
        else:
            st.warning("File appears empty or could not be parsed.")

# ── PAGE: CONSIGNMENT LEDGER ──────────────────────────────────────────────────
elif page == "📑 Consignment Ledger":
    st.markdown("# 📑 Global Consignment Ledger")
    df = st.session_state['ledger_data']

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Consignments", len(df))
        col2.metric("Total Weight (KG)", f"{df['Net_Weight_KG'].astype(float).sum():,.0f}")
        col3.metric("Total FOB Value", f"${df['FOB_Value_USD'].astype(float).sum():,.2f}")

        st.markdown("---")

        # Filters
        with st.expander("🔍 Filter Ledger"):
            fc1, fc2 = st.columns(2)
            with fc1:
                crop_filter = st.multiselect("Crop Type", options=df['Crop_Type'].unique().tolist())
            with fc2:
                county_filter = st.multiselect("Origin County", options=df['Origin_County'].unique().tolist())

        display_df = df.copy()
        if crop_filter:
            display_df = display_df[display_df['Crop_Type'].isin(crop_filter)]
        if county_filter:
            display_df = display_df[display_df['Origin_County'].isin(county_filter)]

        st.markdown(f"<div class='section-header'>UNIFIED REGULATORY TABLE — {len(display_df)} RECORDS</div>", unsafe_allow_html=True)
        st.dataframe(display_df.drop(columns=['_error'], errors='ignore'), use_container_width=True)

        # Export
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Export Ledger as CSV", data=csv_data,
                           file_name=f"veripath_ledger_{datetime.date.today()}.csv",
                           mime="text/csv")
    else:
        st.warning("Ledger is empty. Upload a file or use Farmer Manual Entry.")

# ── PAGE: FARMER MANUAL ENTRY ─────────────────────────────────────────────────
elif page == "🚜 Farmer Manual Entry":
    st.markdown("# 🚜 Field Data Entry")
    st.markdown("<p style='color:#64748b'>Log produce at source — validated before ledger entry</p>", unsafe_allow_html=True)

    with st.form("farmer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_name = st.text_input("Farmer Name *")
            f_crop = st.selectbox("Produce Type *", list(HS_CODE_MAP.keys()))
            f_weight = st.number_input("Net Weight (KG) *", min_value=0.0, step=0.5)
        with col2:
            f_county = st.selectbox("Origin County *", KENYAN_COUNTIES)
            f_pin = st.text_input("KRA PIN", placeholder="e.g. A123456789B")
            f_phone = st.text_input("Farmer Phone (Optional)", placeholder="+254...")

        st.markdown("---")
        submitted = st.form_submit_button("📋 Validate & Log to Ledger", use_container_width=True)

    if submitted:
        errors = []
        if not f_name.strip():
            errors.append("Farmer Name is required")
        if f_weight <= 0:
            errors.append("Net Weight must be greater than 0")

        pin_ok, pin_clean = validate_kra_pin(f_pin)

        if errors:
            for e in errors:
                st.error(f"❌ {e}")
        else:
            hs = get_hs_code(f_crop)
            fob = round(f_weight * 1.5, 2)
            new_entry = {
                "Consignment_ID": f"VP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Farmer_Name": f_name.strip(),
                "Crop_Type": f_crop,
                "KRA_PIN": pin_clean,
                "PIN_Valid": "✅ Valid" if pin_ok else "⚠️ Pending",
                "HS_Code": hs,
                "Origin_County": f_county,
                "Net_Weight_KG": f_weight,
                "FOB_Value_USD": fob,
                "Source": "Manual Entry",
            }
            st.session_state['ledger_data'] = pd.concat(
                [st.session_state['ledger_data'], pd.DataFrame([new_entry])],
                ignore_index=True
            )
            st.balloons()
            st.success(f"✅ Entry logged for **{f_name}** — {f_crop} from {f_county}")

            col1, col2, col3 = st.columns(3)
            col1.info(f"**HS Code:** {hs}")
            col2.info(f"**FOB Value:** ${fob:,.2f}")
            col3.info(f"**PIN Status:** {'✅ Verified' if pin_ok else '⚠️ Pending Verification'}")

# ── PAGE: CARBON TRACKING ─────────────────────────────────────────────────────
elif page == "🌱 Carbon Tracking":
    st.markdown("# 🌱 Sustainability & Carbon Metrics")
    df = st.session_state['ledger_data']

    total_weight = df['Net_Weight_KG'].astype(float).sum() if not df.empty else 0
    carbon_est = round(total_weight * 0.0021, 3)

    col1, col2, col3 = st.columns(3)
    col1.metric("Estimated Carbon Footprint", f"{carbon_est} MT CO₂")
    col2.metric("Total Produce Tracked (KG)", f"{total_weight:,.0f}")
    col3.metric("Green-Light Ready", f"{len(df)} consignments")

    st.markdown("---")
    st.markdown("""
    **Carbon Calculation Method:**
    Agricultural transport emissions estimated at **2.1g CO₂ per kg** of produce tracked.
    This baseline will be refined with route-specific data as the IoT layer is integrated.

    **Coming Soon:**
    - 🌍 Live climate risk flags by county via NASA POWER API
    - 📡 ESP32 IoT sensor integration for real-time transit monitoring
    - 🌿 EUDR deforestation compliance scoring per consignment
    """)

# ── PAGE: ORIGIN MAP ──────────────────────────────────────────────────────────
elif page == "🗺️ Origin Map":
    st.markdown("# 🗺️ Produce Origin Map")
    st.markdown("<p style='color:#64748b'>Geographic distribution of tracked consignments</p>", unsafe_allow_html=True)

    df = st.session_state['ledger_data']

    if not df.empty:
        map_data = []
        for _, row in df.iterrows():
            county = row['Origin_County']
            coords = COUNTY_COORDS.get(county)
            if not coords:
                # Approximate center of Kenya if county not in lookup
                coords = (-0.0236, 37.9062)
            # Add slight jitter to avoid overlap
            import random
            map_data.append({
                "lat": coords[0] + random.uniform(-0.05, 0.05),
                "lon": coords[1] + random.uniform(-0.05, 0.05),
            })
        map_df = pd.DataFrame(map_data)
        st.map(map_df, zoom=5)

        st.markdown("---")
        county_summary = df.groupby('Origin_County').agg(
            Consignments=('Consignment_ID', 'count'),
            Total_Weight=('Net_Weight_KG', 'sum'),
            Total_FOB=('FOB_Value_USD', 'sum')
        ).reset_index()
        st.markdown("<div class='section-header'>COUNTY SUMMARY</div>", unsafe_allow_html=True)
        st.dataframe(county_summary, use_container_width=True)
    else:
        st.info("No data yet. Add entries to see the origin map.")
        # Show default Kenya map
        default = pd.DataFrame({'lat': [-0.0236], 'lon': [37.9062]})
        st.map(default, zoom=5)
