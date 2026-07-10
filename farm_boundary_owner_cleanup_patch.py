with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

# Remove the owner_username variable assignment left over in the farmer dropdown block
content = content.replace(
    '            selected_label = st.selectbox("Owner / farmer", options=list(farmer_options.keys()))\n            selected_farmer_id = farmer_options[selected_label]\n            owner_username = selected_label',
    '            selected_label = st.selectbox("Owner / farmer", options=list(farmer_options.keys()))\n            selected_farmer_id = farmer_options[selected_label]'
)
content = content.replace(
    '            selected_farmer_id = None\n            owner_username = username',
    '            selected_farmer_id = None'
)

# Update the RPC call to match new signature (p_farm_name, p_farmer_id, p_outgrower_block_id, p_geojson)
old_rpc = '''            result = supabase.rpc("insert_farm_boundary", {
                "p_farm_name": farm_name,
                "p_owner_username": owner_username,
                "p_outgrower_block_id": outgrower_block_id or None,
                "p_geojson": geojson_str,
                "p_farmer_id": selected_farmer_id,
            }).execute()'''

new_rpc = '''            result = supabase.rpc("insert_farm_boundary", {
                "p_farm_name": farm_name,
                "p_farmer_id": selected_farmer_id,
                "p_outgrower_block_id": outgrower_block_id or None,
                "p_geojson": geojson_str,
            }).execute()'''

content = content.replace(old_rpc, new_rpc)

# Update the "Saved Farm Boundaries" table to show farmer_id instead of owner_username
content = content.replace(
    '"id, farm_name, owner_username, outgrower_block_id, area_hectares, created_at"',
    '"id, farm_name, farmer_id, outgrower_block_id, area_hectares, created_at"'
)

with open("farm_boundary_upload.py", "w") as f:
    f.write(content)

print("Patched successfully.")
