with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

old_guard = '''        if not selected_farmer_id:
            st.error("❌ No farmer selected — register the farmer first.")
            st.stop()'''

new_guard = '''        if not selected_farmer_id:
            st.error("❌ No farmer selected — register the farmer first.")
            st.stop()

        # Guard against accidental double-submit / duplicate boundary for the same farmer+name
        try:
            existing = supabase.table("farm_boundaries").select("id").eq(
                "farmer_id", selected_farmer_id
            ).eq("farm_name", farm_name).execute().data
        except Exception:
            existing = []

        if existing:
            st.error(
                f"❌ **{farm_name}** already has a saved boundary for this farmer. "
                f"Use a different farm name, or delete the existing boundary first if this is a correction."
            )
            st.stop()'''

content = content.replace(old_guard, new_guard)

with open("farm_boundary_upload.py", "w") as f:
    f.write(content)

print("Patched duplicate guard successfully.")
