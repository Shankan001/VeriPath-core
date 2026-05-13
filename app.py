import streamlit as st
import pandas as pd
import datetime

# 1. Initialize Session State with a default structure if empty
if 'ledger_data' not in st.session_state:
    # Creating an empty DataFrame with the required government columns
    cols = ['Consignment_ID', 'Farmer_Name', 'Crop_Type', 'KRA_PIN', 'HS_Code', 'Origin_County', 'Net_Weight', 'FOB_Value']
    st.session_state['ledger_data'] = pd.DataFrame(columns=cols)

st.set_page_config(page_title="VeriPath Africa | Unified Ledger", layout="wide")

st.sidebar.title("🏗️ VeriPath Enterprise")
page = st.sidebar.radio("Mission Control", [
    "Infrastructure Map",
    "Data Ingestion", 
    "Consignment Ledger", 
    "Farmer Manual Entry",
    "Carbon Tracking"
])

# --- MODULE: INFRASTRUCTURE MAP ---
if page == "Infrastructure Map":
    st.title("🗺️ Logistics Visualization")
    hubs = pd.DataFrame({'lat': [1.2921, -4.0435, 0.5143], 'lon': [36.8219, 39.6682, 35.2698]})
    st.map(hubs)

# --- MODULE: DATA INGESTION ---
elif page == "Data Ingestion":
    st.title("📤 Bulk Regulatory Ingestion")
    uploaded_file = st.file_uploader("Upload Shipment CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        new_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        # Merge with existing data
        st.session_state['ledger_data'] = pd.concat([st.session_state['ledger_data'], new_df], ignore_index=True)
        st.success("✅ Bulk data appended to Ledger.")
        st.dataframe(new_df)

# --- MODULE: CONSIGNMENT LEDGER ---
elif page == "Consignment Ledger":
    st.title("📑 Global Consignment Ledger")
    df = st.session_state['ledger_data']
    
    if not df.empty:
        st.metric("Total System Value", f"$${df['FOB_Value'].astype(float).sum():,}")
        st.write("### Unified Regulatory Table (Manual + Bulk)")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Ledger is empty. Upload a file or use Manual Entry.")

# --- MODULE: FARMER MANUAL ENTRY (NOW CONNECTED TO LEDGER) ---
elif page == "Farmer Manual Entry":
    st.title("🚜 Field Data Entry")
    with st.form("farmer_form", clear_on_submit=True):
        f_name = st.text_input("Farmer Name")
        f_crop = st.selectbox("Produce", ["Maize", "Coffee", "Tea", "Avocado"])
        f_weight = st.number_input("Net Weight (KG)", min_value=0.0)
        f_county = st.text_input("Origin County")
        f_pin = st.text_input("KRA PIN (Optional for smallholders)")
        
        if st.form_submit_button("Log to Ledger"):
            # Create a new record
            new_entry = {
                'Consignment_ID': f"VP-{datetime.datetime.now().strftime('%M%S')}",
                'Farmer_Name': f_name,
                'Crop_Type': f_crop,
                'KRA_PIN': f_pin if f_pin else "PENDING",
                'HS_Code': "AUTO-GEN",
                'Origin_County': f_county,
                'Net_Weight': f_weight,
                'FOB_Value': f_weight * 150 # Mock valuation
            }
            # Append to session state
            st.session_state['ledger_data'] = pd.concat([st.session_state['ledger_data'], pd.DataFrame([new_entry])], ignore_index=True)
            st.balloons()
            st.success(f"Entry for {f_name} successfully synced to Ledger!")

# --- MODULE: CARBON TRACKING ---
elif page == "Carbon Tracking":
    st.title("🌱 Sustainability Metrics")
    st.metric("Carbon Offset", "1,250 MT")
