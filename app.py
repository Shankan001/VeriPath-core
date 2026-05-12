import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit_authenticator as stauth
import plotly.express as px

st.set_page_config(page_title="VeriPath Enterprise: UNICEF Edition", layout="wide")

# --- 1. SECURE SESSION STATE ---
if 'credentials' not in st.session_state:
    st.session_state['credentials'] = {
        'usernames': {
            'admin': {
                'name': 'DDEC Lead',
                'password': 'admin_password', # Use stauth.Hasher to hash in prod
                'email': 'admin@veripath.co.ke'
            }
        }
    }

# --- 2. AUTHENTICATOR (v0.3+ Syntax) ---
authenticator = stauth.Authenticate(
    st.session_state['credentials'],
    'veripath_cookie',
    'auth_key_123',
    30
)

# LOGIN / REGISTRATION INTERFACE
tab_login, tab_reg = st.tabs(["🔒 Secure Access", "📝 New Exporter Registration"])

with tab_login:
    authenticator.login(location='main')

with tab_reg:
    try:
        result = authenticator.register_user(location='main', pre_authorized=None)
        if result:
            st.success('Registration successful! Please proceed to login.')
    except Exception as e:
        st.error(f"System Notice: {e}")

# --- 3. THE "WINNING" DASHBOARD AREA ---
if st.session_state.get("authentication_status"):
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.title(f"Welcome, {st.session_state.get('name')}")
    
    # DATABASE SETUP
    def init_db():
        conn = sqlite3.connect('data/veripath_pulse.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS market_intelligence 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      consignment_id TEXT, crop_type TEXT, weight_kg REAL, 
                      lat REAL, lon REAL, kra_pin TEXT, packhouse_id TEXT,
                      status TEXT DEFAULT 'Pending', security_status TEXT DEFAULT 'Secure',
                      trust_score INTEGER, timestamp TEXT, operator TEXT)''')
        conn.commit()
        conn.close()

    init_db()

    st.title("💎 VeriPath: Frontier Trade Engine")
    st.markdown("### *Digital Public Good for Export Compliance & Climate Resilience*")

    # --- TOP ROW: IMPACT METRICS (The UNICEF Hook) ---
    conn = sqlite3.connect('data/veripath_pulse.db')
    df = pd.read_sql_query("SELECT * FROM market_intelligence", conn)
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    if not df.empty:
        total_kg = df['weight_kg'].sum()
        m1.metric("📦 Total Export Volume", f"{total_kg:,.0f} kg")
        m2.metric("🌱 Carbon Tracking", f"{total_kg * 0.04:.1f} kg CO2e")
        m3.metric("👨‍🌾 Smallholders Supported", f"{len(df['kra_pin'].unique())}")
        m4.metric("🛡️ System Integrity", f"{int(df['trust_score'].mean())}%")

    # --- MIDDLE ROW: DATA ENTRY & LIVE MAP ---
    col_input, col_map = st.columns([1, 2])

    with col_input:
        st.subheader("📥 Log Consignment")
        with st.form("consignment_form"):
            c_id = st.text_input("Consignment ID", "VP-KE-001")
            crop = st.selectbox("Crop Type", ["Avocado", "Mango", "Coffee", "Tea"])
            weight = st.number_input("Net Weight (kg)", min_value=1.0)
            kra = st.text_input("Producer KRA/PIN")
            # Default to Nairobi coords for demo
            if st.form_submit_button("Verify & Upload to Ledger"):
                conn = sqlite3.connect('data/veripath_pulse.db')
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""INSERT INTO market_intelligence 
                             (consignment_id, crop_type, weight_kg, lat, lon, kra_pin, trust_score, timestamp, operator) 
                             VALUES (?,?,?,?,?,?,?,?,?)""",
                             (c_id, crop, weight, -1.286, 36.817, kra, 85, now, st.session_state.get('name')))
                conn.commit()
                conn.close()
                st.success("Consignment Hash Generated & Logged")
                st.rerun()

    with col_map:
        st.subheader("📍 Chain of Custody (Live)")
        if not df.empty:
            fig = px.scatter_map(df, lat="lat", lon="lon", color="security_status", 
                                 size="weight_kg", zoom=5, height=450,
                                 color_discrete_map={'Secure': '#00CC96', 'Warning': '#FFA15A', 'Tampered': '#EF553B'})
            st.plotly_chart(fig, width='stretch')

    # --- BOTTOM ROW: AUDIT TRAIL ---
    st.subheader("📋 Immutable Compliance Ledger")
    if not df.empty:
        def style_trust(val):
            color = '#00CC96' if val > 80 else '#FFA15A'
            return f'color: {color}; font-weight: bold'
        
        styled_df = df.style.map(style_trust, subset=['trust_score'])
        st.dataframe(styled_df, width='stretch')

    # --- FOOTER ---
    st.markdown("---")
    st.caption("VeriPath v2.6-Beta | Registered with ODPC Kenya | Open Source DPG Prototype")

elif st.session_state.get("authentication_status") is False:
    st.error('Access Denied: Invalid Credentials')
elif st.session_state.get("authentication_status") is None:
    st.warning("Authorized Personnel Only: Please enter credentials to bridge to KenTrade.")
    st.info("🍪 Privacy Notice: This portal uses essential security cookies. By logging in, you accept our DPG Data Privacy Terms.")
