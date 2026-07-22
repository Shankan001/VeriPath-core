with open("eudr.py", "r") as f:
    content = f.read()

old = '''        has_gps = st.checkbox("Farm GPS polygon recorded?")
        has_dds = st.checkbox("Due Diligence Statement (DDS) prepared?")
        if crop != "— Select —":
            result = get_eudr_risk(crop)
            risk   = result["risk"]
            # Escalate AMBER → RED if going to EU without GPS/DDS
            if risk == "AMBER" and destination == "European Union" and (not has_gps or not has_dds):
                risk = "RED"'''

new = '''        from supabase_db import get_client as _eudr_gc
        try:
            _farms_for_eudr = _eudr_gc().table("farm_boundaries").select(
                "id, farm_name, deforestation_risk_perennial, deforestation_risk_annual, "
                "deforestation_risk_timber, deforestation_tree_loss_after_2020_ha, deforestation_checked_at"
            ).execute().data
        except Exception:
            _farms_for_eudr = []

        selected_farm_record = None
        if _farms_for_eudr:
            _farm_names_eudr = ["— None selected —"] + [f["farm_name"] for f in _farms_for_eudr]
            _selected_farm_name = st.selectbox("Farm (optional — for real satellite check)", _farm_names_eudr)
            if _selected_farm_name != "— None selected —":
                selected_farm_record = next((f for f in _farms_for_eudr if f["farm_name"] == _selected_farm_name), None)

        has_gps = bool(selected_farm_record) or st.checkbox("Farm GPS polygon recorded?")
        if selected_farm_record:
            st.caption("✅ GPS polygon confirmed — farm selected from registered boundaries.")

        has_dds = st.checkbox("Due Diligence Statement (DDS) prepared?")

        if crop != "— Select —":
            result = get_eudr_risk(crop)
            risk   = result["risk"]

            whisp_checked = selected_farm_record and selected_farm_record.get("deforestation_checked_at")
            if whisp_checked:
                _relevant_risk = selected_farm_record.get("deforestation_risk_perennial", "unknown")
                if _relevant_risk == "high":
                    risk = "RED"
                elif _relevant_risk == "low" and risk == "AMBER":
                    # Real satellite evidence of no deforestation — downgrade AMBER to GREEN
                    risk = "GREEN"

            # Escalate AMBER → RED if going to EU without GPS/DDS
            if risk == "AMBER" and destination == "European Union" and (not has_gps or not has_dds):
                risk = "RED"'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("eudr.py", "w") as f:
        f.write(content)
    print("Wired real Whisp deforestation data into EUDR risk logic.")
