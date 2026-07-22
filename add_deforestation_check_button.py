with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

old = '''    st.markdown("<div class='section-header'>SAVED FARM BOUNDARIES</div>", unsafe_allow_html=True)'''

new = '''    st.markdown("<div class='section-header'>SAVED FARM BOUNDARIES</div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='color:#64748b;font-size:0.85rem'>Run a satellite deforestation check "
        "(FAO Whisp) on a saved boundary to generate real EUDR evidence for this farm.</p>",
        unsafe_allow_html=True
    )
    try:
        _boundaries_for_check = supabase.table("farm_boundaries").select(
            "id, farm_name, deforestation_checked_at"
        ).execute().data
    except Exception:
        _boundaries_for_check = []

    if _boundaries_for_check:
        _check_options = {f"{b['farm_name']} ({b['id'][:8]})": b["id"] for b in _boundaries_for_check}
        _selected_check_label = st.selectbox("Select farm to check", list(_check_options.keys()), key="deforestation_check_select")
        _selected_check_id = _check_options[_selected_check_label]

        if st.button("🌳 Check Deforestation Risk (FAO Whisp)", use_container_width=True):
            with st.spinner("Running satellite deforestation analysis — this may take up to a minute..."):
                try:
                    _geojson_result = supabase.rpc("get_farm_boundary_geojson", {"p_farm_boundary_id": _selected_check_id}).execute().data
                    from whisp_check import check_deforestation_risk
                    _whisp_result = check_deforestation_risk(_geojson_result)

                    if _whisp_result["success"]:
                        from datetime import datetime, timezone
                        supabase.table("farm_boundaries").update({
                            "deforestation_risk_perennial": _whisp_result["risk_perennial_crop"],
                            "deforestation_risk_annual": _whisp_result["risk_annual_crop"],
                            "deforestation_risk_timber": _whisp_result["risk_timber"],
                            "deforestation_tree_loss_after_2020_ha": _whisp_result["tree_cover_loss_after_2020_ha"],
                            "deforestation_checked_at": datetime.now(timezone.utc).isoformat(),
                            "deforestation_raw_result": _whisp_result["raw_result"],
                        }).eq("id", _selected_check_id).execute()
                        st.success(
                            f"✅ Deforestation check complete — "
                            f"Perennial: {_whisp_result['risk_perennial_crop']} · "
                            f"Annual: {_whisp_result['risk_annual_crop']} · "
                            f"Timber: {_whisp_result['risk_timber']}"
                        )
                        st.rerun()
                    else:
                        st.error(f"❌ Check failed: {_whisp_result['error']}")
                except Exception as e:
                    st.error(f"❌ Error running check: {str(e)}")

    st.markdown("---")

'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("farm_boundary_upload.py", "w") as f:
        f.write(content)
    print("Added deforestation check button.")
