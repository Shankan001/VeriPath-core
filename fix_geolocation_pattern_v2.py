with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

old_block = '''        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("📍 Capture Point", type="primary", use_container_width=True):
                loc = get_geolocation()
                if loc and "coords" in loc:
                    lat = loc["coords"]["latitude"]
                    lon = loc["coords"]["longitude"]
                    accuracy = loc["coords"].get("accuracy", None)
                    st.session_state["boundary_points"].append({"lat": lat, "lon": lon, "accuracy": accuracy})
                    st.success(f"✅ Point {len(st.session_state['boundary_points'])} captured")
                    st.rerun()
                else:
                    st.error("❌ Could not get GPS location. Allow location access in your browser.")
        with col_b:'''

new_block = '''        # Fetch location unconditionally every rerun — calling get_geolocation()
        # only inside a button's if-block is a known broken pattern with this library.
        current_loc = get_geolocation(key=f"geo_{len(st.session_state['boundary_points'])}")

        if current_loc and "error" in current_loc:
            err_code = current_loc["error"].get("code")
            err_msg = current_loc["error"].get("message", "Unknown error")
            if err_code == 1:
                st.error("❌ Location permission denied. Check site permissions in your browser settings.")
            else:
                st.warning(f"⚠️ GPS error: {err_msg}")
        elif current_loc and "coords" in current_loc:
            lat = current_loc["coords"]["latitude"]
            lon = current_loc["coords"]["longitude"]
            accuracy = current_loc["coords"].get("accuracy")
            st.info(f"📡 Current reading: {lat:.6f}, {lon:.6f}" + (f" (±{accuracy:.0f}m)" if accuracy else ""))
        else:
            st.info("📡 Waiting for GPS signal...")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("📍 Capture This Point", type="primary", use_container_width=True):
                if current_loc and "coords" in current_loc:
                    lat = current_loc["coords"]["latitude"]
                    lon = current_loc["coords"]["longitude"]
                    accuracy = current_loc["coords"].get("accuracy")
                    st.session_state["boundary_points"].append({"lat": lat, "lon": lon, "accuracy": accuracy})
                    st.success(f"✅ Point {len(st.session_state['boundary_points'])} captured")
                    st.rerun()
                else:
                    st.error("❌ No GPS reading available yet — wait for the location above to appear, then tap again.")
        with col_b:'''

if old_block not in content:
    print("ERROR: old_block not found — no changes made. Paste file content again to debug.")
else:
    content = content.replace(old_block, new_block)
    with open("farm_boundary_upload.py", "w") as f:
        f.write(content)
    print("Patched successfully this time.")
