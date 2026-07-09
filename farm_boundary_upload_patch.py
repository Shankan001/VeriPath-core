import re

with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

# 1. Replace the free-text owner field with a real farmer dropdown
old_block = '''    with col2:
        owner_username = st.text_input("Owner/farmer username", value=username)'''

new_block = '''    with col2:
        try:
            farmers_result = supabase.table("farmers").select(
                "farmer_id, name, phone"
            ).order("name").execute().data
        except Exception:
            farmers_result = []

        if not farmers_result:
            st.warning("No registered farmers found. Register the farmer first before uploading a boundary.")
            selected_farmer_id = None
            owner_username = username
        else:
            farmer_options = {
                f"{f['name']} ({f['phone']}) — {f['farmer_id']}": f["farmer_id"]
                for f in farmers_result
            }
            selected_label = st.selectbox("Owner / farmer", options=list(farmer_options.keys()))
            selected_farmer_id = farmer_options[selected_label]
            owner_username = selected_label'''

content = content.replace(old_block, new_block)

# 2. Pass p_farmer_id through to the RPC call
old_rpc = '''            result = supabase.rpc("insert_farm_boundary", {
                "p_farm_name": farm_name,
                "p_owner_username": owner_username,
                "p_outgrower_block_id": outgrower_block_id or None,
                "p_geojson": geojson_str,
            }).execute()'''

new_rpc = '''            result = supabase.rpc("insert_farm_boundary", {
                "p_farm_name": farm_name,
                "p_owner_username": owner_username,
                "p_outgrower_block_id": outgrower_block_id or None,
                "p_geojson": geojson_str,
                "p_farmer_id": selected_farmer_id,
            }).execute()'''

content = content.replace(old_rpc, new_rpc)

# 3. Guard: don't allow save if no farmer selected
old_guard = '''        if not farm_name:
            st.error("❌ Farm name is required.")
            st.stop()'''

new_guard = '''        if not farm_name:
            st.error("❌ Farm name is required.")
            st.stop()

        if not selected_farmer_id:
            st.error("❌ No farmer selected — register the farmer first.")
            st.stop()'''

content = content.replace(old_guard, new_guard)

with open("farm_boundary_upload.py", "w") as f:
    f.write(content)

print("Patched successfully.")
