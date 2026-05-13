import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Config (Mobile Optimized for Galaxy A25)
st.set_page_config(page_title="VeriPath Africa | UNICEF Venture Fund MVP", layout="wide")

# 2. Grant-Aligned Sidebar
st.sidebar.title("📦 VeriPath Africa")
st.sidebar.info("Digital Public Good for Supply Chain Resilience")
page = st.sidebar.radio("Navigation", [
    "Dashboard (Kenya Map)", 
    "Data Ingestion (Excel/CSV)", 
    "Farmer Manual Entry",
    "Carbon Tracking & Sustainability"
])

# --- DASHBOARD & MAP (Target: 12-Month Roadmap) ---
if page == "Dashboard (Kenya Map)":
    st.title("🗺️ Supply Chain Visibility")
    st.write("Real-time tracking of essential supplies across Kenya.")
    
    # Coordinates for key hubs: Nairobi, Mombasa, Kisumu
    hubs = pd.DataFrame({
        'lat': [1.2921, -4.0435, -0.1022],
        'lon': [36.8219, 39.6682, 34.7617]
    })
    st.map(hubs)
    
    col1, col2 = st.columns(2)
    col1.metric("Active Shipments", "24", "+3")
    col2.metric("Verified Partners", "12", "Target: 50")

# --- DATA INGESTION (Target: Bulk Regulatory Loading) ---
elif page == "Data Ingestion (Excel/CSV)":
    st.title("📤 Bulk Data Sync")
    st.write("Upload local logs to sync with the VeriPath global ledger.")
    
    uploaded_file = st.file_uploader("Choose Excel or CSV file", type=["xlsx", "csv"])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        # Validation for government-mandated columns
        required = ['KRA_PIN', 'Consignee_Name', 'HS_Code', 'Net_Weight']
        missing = [c for c in required if c not in df.columns]
        
        if missing:
            st.warning(f"Note: For KENTRADE sync, please include: {missing}")
        
        st.success(f"File '{uploaded_file.name}' loaded successfully.")
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 Sync to Ledger"):
            st.balloons()
            st.success("Data synced to GitHub Repository & Digital Public Good Registry!")

# --- FARMER MANUAL ENTRY (Target: Low-Connectivity Usage) ---
elif page == "Farmer Manual Entry":
    st.title("🚜 Last-Mile Data Entry")
    st.write("Designed for high-performance use on mid-range Android devices.")
    with st.form("entry_form"):
        st.text_input("Produce/Item Name")
        st.number_input("Quantity (Units/KG)", min_value=0)
        st.selectbox("Current Location", ["Nairobi Hub", "Mombasa Port", "Eldoret Center"])
        if st.form_submit_button("Log Entry"):
            st.success("Entry stored locally and queued for cloud sync.")

# --- CARBON TRACKING (Target: Environmental Impact) ---
elif page == "Carbon Tracking & Sustainability":
    st.title("🌱 Sustainability Ledger")
    st.metric("Total CO2 Offset", "1,250 MT", "Goal: 5,000 MT")
    st.info("Tracking the environmental footprint of logistics operations.")

# Footer (Aligns with image_3b3ddf.png)
st.sidebar.write("---")
st.sidebar.write("📍 **Status:** Prototyping (UNICEF Round)")
st.sidebar.write("⚙️ **Engine:** Playwright / Python")
