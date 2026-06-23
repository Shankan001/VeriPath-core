with open("app.py","r") as f:
    content = f.read()

fixes = [
    # Consignment Ledger metrics (line 339-340)
    ('''col2.metric("Weight (KG)", f"{df['Net_Weight_KG'].astype(float).sum():,.0f}")''',
     '''col2.metric("Weight (KG)", f"{df['weight_kg'].astype(float).sum():,.0f}" if 'weight_kg' in df.columns else "0")'''),

    ('''col3.metric("FOB Value",   f"${df['FOB_Value_USD'].astype(float).sum():,.2f}")''',
     '''col3.metric("FOB Value",   f"${df['FOB_Value_USD'].astype(float).sum():,.2f}" if 'FOB_Value_USD' in df.columns else "$0.00")'''),

    # Filters (line 344-348)
    ('''crop_filter   = fc1.multiselect("Crop",   options=df["Crop_Type"].unique().tolist())''',
     '''_crop_col = "crop" if "crop" in df.columns else "Crop_Type" if "Crop_Type" in df.columns else None
            crop_filter   = fc1.multiselect("Crop",   options=df[_crop_col].unique().tolist() if _crop_col else [])'''),

    ('''county_filter = fc2.multiselect("County", options=df["Origin_County"].unique().tolist())''',
     '''_county_col = "county" if "county" in df.columns else "Origin_County" if "Origin_County" in df.columns else None
            county_filter = fc2.multiselect("County", options=df[_county_col].unique().tolist() if _county_col else [])'''),

    ('''if crop_filter:   display_df = display_df[display_df["Crop_Type"].isin(crop_filter)]
        if county_filter: display_df = display_df[display_df["Origin_County"].isin(county_filter)]''',
     '''if crop_filter and _crop_col:     display_df = display_df[display_df[_crop_col].isin(crop_filter)]
        if county_filter and _county_col: display_df = display_df[display_df[_county_col].isin(county_filter)]'''),

    # Carbon tracking (line 428)
    ('''tw = df["Net_Weight_KG"].astype(float).sum() if not df.empty else 0''',
     '''tw = df["weight_kg"].astype(float).sum() if not df.empty and "weight_kg" in df.columns else (df["Net_Weight_KG"].astype(float).sum() if not df.empty and "Net_Weight_KG" in df.columns else 0)'''),

    # Origin map (line 558-568)
    ('''coords = COUNTY_COORDS.get(row["Origin_County"], (-0.0236, 37.9062))''',
     '''_c = row.get("county", row.get("Origin_County",""))
                coords = COUNTY_COORDS.get(_c, (-0.0236, 37.9062))'''),

    ('''county_summary = df.groupby("Origin_County").agg(
            Consignments=("Consignment_ID","count"),
            Total_Weight=("Net_Weight_KG","sum"),
            Total_FOB=("FOB_Value_USD","sum")
        ).reset_index()''',
     '''_grp_county = "county" if "county" in df.columns else "Origin_County" if "Origin_County" in df.columns else None
        _grp_id     = "session_id" if "session_id" in df.columns else "Consignment_ID" if "Consignment_ID" in df.columns else None
        _grp_weight = "weight_kg" if "weight_kg" in df.columns else "Net_Weight_KG" if "Net_Weight_KG" in df.columns else None
        if _grp_county and _grp_id and _grp_weight:
            county_summary = df.groupby(_grp_county).agg(
                Consignments=(_grp_id,"count"),
                Total_Weight=(_grp_weight,"sum"),
            ).reset_index()
        else:
            county_summary = pd.DataFrame()'''),

    ('''st.dataframe(county_summary, use_container_width=True)''',
     '''if not county_summary.empty:
            st.dataframe(county_summary, use_container_width=True)'''),
]

patched = 0
for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        patched += 1
        print(f"✅ Fixed: {old[:60]}...")
    else:
        print(f"⚠️  Not found: {old[:60]}...")

with open("app.py","w") as f:
    f.write(content)

print(f"\n{patched}/{len(fixes)} fixes applied.")
