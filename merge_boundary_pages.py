with open("farm_boundary_upload.py", "r") as f:
    upload_content = f.read()


# Extract the imports we need from recorder (geolocation) that upload doesn't have
merged = '''"""
VeriPath — Farm Boundary Registration
Two ways to register a farm boundary: upload a GeoJSON/KML file from a
survey app, or walk the boundary and tap to capture each corner's GPS point.
"""

import streamlit as st
import json
import xml.etree.ElementTree as ET
import pandas as pd
from streamlit_js_eval import get_geolocation
from supabase_db import get_client


def parse_kml_polygon(kml_bytes: bytes) -> dict:
    try:
        root = ET.fromstring(kml_bytes)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        coords_elem = root.find(".//kml:Polygon//kml:coordinates", ns)
        if coords_elem is None:
            coords_elem = root.find(".//Polygon//coordinates")

        if coords_elem is None or not coords_elem.text:
            return {"success": False, "geojson": None, "error": "No Polygon coordinates found in KML file."}

        raw_coords = coords_elem.text.strip().split()
        ring = []
        for point in raw_coords:
            parts = point.split(",")
            lon, lat = float(parts[0]), float(parts[1])
            ring.append([lon, lat])

        geojson = {"type": "Polygon", "coordinates": [ring]}
        return {"success": True, "geojson": geojson, "error": None}

    except Exception as e:
        return {"success": False, "geojson": None, "error": f"Could not parse KML: {str(e)}"}


def parse_geojson_polygon(geojson_bytes: bytes) -> dict:
    try:
        data = json.loads(geojson_bytes)

        if data.get("type") == "Polygon":
            geometry = data
        elif data.get("type") == "Feature":
            geometry = data.get("geometry")
        elif data.get("type") == "FeatureCollection":
            features = data.get("features", [])
            if not features:
                return {"success": False, "geojson": None, "error": "FeatureCollection has no features."}
            geometry = features[0].get("geometry")
        else:
            return {"success": False, "geojson": None, "error": f"Unsupported GeoJSON type: {data.get('type')}"}

        if not geometry or geometry.get("type") != "Polygon":
            return {"success": False, "geojson": None, "error": "No Polygon geometry found in file."}

        return {"success": True, "geojson": geometry, "error": None}

    except Exception as e:
        return {"success": False, "geojson": None, "error": f"Could not parse GeoJSON: {str(e)}"}


def get_scoped_farmers(supabase, profile):
    company = profile.get("company", "") if profile.get("role") != "admin" else ""
    try:
        q = supabase.table("farmers").select("farmer_id, name, phone, company")
        farmers_result = q.order("name").execute().data
        if company:
            company_norm = company.strip().lower()
            farmers_result = [
                f for f in farmers_result
                if f.get("company", "").strip().lower() == company_norm
            ]
    except Exception:
        farmers_result = []
    return farmers_result


def check_duplicate(supabase, farmer_id, farm_name):
    try:
        existing = supabase.table("farm_boundaries").select("id").eq(
            "farmer_id", farmer_id
        ).eq("farm_name", farm_name).execute().data
    except Exception:
        existing = []
    return bool(existing)


def save_boundary(supabase, farm_name, farmer_id, outgrower_block_id, geojson_dict):
    geojson_str = json.dumps(geojson_dict)
    try:
        result = supabase.rpc("insert_farm_boundary", {
            "p_farm_name": farm_name,
            "p_farmer_id": farmer_id,
            "p_outgrower_block_id": outgrower_block_id or None,
            "p_geojson": geojson_str,
        }).execute()
        return result.data
    except Exception as e:
        return {"success": False, "error": str(e)}


def render_farm_boundary_upload_page(profile: dict):
    st.markdown("# 🛰 Farm Boundary Registration")
    st.markdown(
        "<p style='color:#64748b'>Register a farm boundary by uploading a surveyed file, "
        "or by walking the perimeter and capturing GPS points directly.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    supabase = get_client()
    farmers_result = get_scoped_farmers(supabase, profile)

    tab_upload, tab_walk = st.tabs(["📁 Upload File", "📍 Walk the Boundary"])

    # ── TAB 1: Upload File ──────────────────────────────────────────────
    with tab_upload:
        col1, col2 = st.columns(2)
        with col1:
            farm_name_u = st.text_input("Farm name", key="farm_name_upload")
            outgrower_block_id_u = st.text_input(
                "Outgrower block ID", key="block_id_upload",
                help="Same block ID used in the Certificate Vault — links this boundary to MRL red-listing."
            )
        with col2:
            if not farmers_result:
                st.warning("No registered farmers found for your company. Register the farmer first.")
                selected_farmer_id_u = None
            else:
                farmer_options = {
                    f"{f['name']} ({f['phone']}) — {f['farmer_id']}": f["farmer_id"]
                    for f in farmers_result
                }
                selected_label_u = st.selectbox("Owner / farmer", options=list(farmer_options.keys()), key="farmer_upload")
                selected_farmer_id_u = farmer_options[selected_label_u]

        uploaded = st.file_uploader("Boundary file", type=["geojson", "json", "kml"])

        if uploaded is not None and st.button("📍 Save Boundary", type="primary", use_container_width=True, key="save_upload"):
            if not farm_name_u:
                st.error("❌ Farm name is required.")
                st.stop()
            if not selected_farmer_id_u:
                st.error("❌ No farmer selected — register the farmer first.")
                st.stop()
            if check_duplicate(supabase, selected_farmer_id_u, farm_name_u):
                st.error(f"❌ **{farm_name_u}** already has a saved boundary for this farmer. Use a different farm name.")
                st.stop()

            file_bytes = uploaded.getvalue()
            if uploaded.name.lower().endswith(".kml"):
                parse_result = parse_kml_polygon(file_bytes)
            else:
                parse_result = parse_geojson_polygon(file_bytes)

            if not parse_result["success"]:
                st.error(f"❌ {parse_result['error']}")
                st.stop()

            response = save_boundary(supabase, farm_name_u, selected_farmer_id_u, outgrower_block_id_u, parse_result["geojson"])
            if response.get("success"):
                area = response.get("area_hectares")
                st.success(f"✅ Boundary saved for **{farm_name_u}** — computed area: **{area:.2f} hectares**")
                st.rerun()
            else:
                st.error(f"❌ {response.get('error')}")

    # ── TAB 2: Walk the Boundary ─────────────────────────────────────────
    with tab_walk:
        st.markdown(
            "<p style='color:#64748b;font-size:0.85rem'>Stand at each corner of the farm and tap "
            "'Capture Point'. Once every corner is marked, tap 'Finish Boundary'.</p>",
            unsafe_allow_html=True
        )

        if "boundary_points" not in st.session_state:
            st.session_state["boundary_points"] = []

        col1, col2 = st.columns(2)
        with col1:
            farm_name_w = st.text_input("Farm name", key="farm_name_walk")
            outgrower_block_id_w = st.text_input(
                "Outgrower block ID", key="block_id_walk",
                help="Same block ID used in the Certificate Vault — links this boundary to MRL red-listing."
            )
        with col2:
            if not farmers_result:
                st.warning("No registered farmers found for your company. Register the farmer first.")
                selected_farmer_id_w = None
            else:
                farmer_options = {
                    f"{f['name']} ({f['phone']}) — {f['farmer_id']}": f["farmer_id"]
                    for f in farmers_result
                }
                selected_label_w = st.selectbox("Owner / farmer", options=list(farmer_options.keys()), key="farmer_walk")
                selected_farmer_id_w = farmer_options[selected_label_w]

        col_a, col_b, col_c = st.columns(3)
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
        with col_b:
            if st.button("↩️ Undo Last Point", use_container_width=True):
                if st.session_state["boundary_points"]:
                    st.session_state["boundary_points"].pop()
                    st.rerun()
        with col_c:
            if st.button("🗑️ Clear All Points", use_container_width=True):
                st.session_state["boundary_points"] = []
                st.rerun()

        points = st.session_state["boundary_points"]
        st.markdown(f"**Points captured: {len(points)}** (minimum 3 required)")

        if points:
            display_rows = [{
                "#": i + 1,
                "Latitude": round(p["lat"], 6),
                "Longitude": round(p["lon"], 6),
                "Accuracy": f"±{p['accuracy']:.0f}m" if p.get("accuracy") else "—",
            } for i, p in enumerate(points)]
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

        if st.button("✅ Finish Boundary & Save", type="primary", use_container_width=True, key="save_walk"):
            if not farm_name_w:
                st.error("❌ Farm name is required.")
                st.stop()
            if not selected_farmer_id_w:
                st.error("❌ No farmer selected — register the farmer first.")
                st.stop()
            if len(points) < 3:
                st.error(f"❌ Need at least 3 points — you have {len(points)}.")
                st.stop()
            if check_duplicate(supabase, selected_farmer_id_w, farm_name_w):
                st.error(f"❌ **{farm_name_w}** already has a saved boundary for this farmer. Use a different farm name.")
                st.stop()

            ring = [[p["lon"], p["lat"]] for p in points]
            ring.append(ring[0])
            geojson = {"type": "Polygon", "coordinates": [ring]}

            response = save_boundary(supabase, farm_name_w, selected_farmer_id_w, outgrower_block_id_w, geojson)
            if response.get("success"):
                area = response.get("area_hectares")
                st.success(f"✅ Boundary saved for **{farm_name_w}** — computed area: **{area:.2f} hectares**")
                st.session_state["boundary_points"] = []
                st.rerun()
            else:
                st.error(f"❌ {response.get('error')}")

    st.markdown("---")
    st.markdown("<div class='section-header'>SAVED FARM BOUNDARIES</div>", unsafe_allow_html=True)

    try:
        farms = supabase.table("farm_boundaries").select(
            "id, farm_name, farmer_id, outgrower_block_id, area_hectares, created_at"
        ).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Could not load boundaries: {str(e)}")
        farms = []

    if not farms:
        st.info("No farm boundaries uploaded yet.")
    else:
        st.dataframe(pd.DataFrame(farms), use_container_width=True, hide_index=True)
'''

with open("farm_boundary_upload.py", "w") as f:
    f.write(merged)

print("Merged successfully into farm_boundary_upload.py")
