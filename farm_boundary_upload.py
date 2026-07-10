"""
VeriPath NDVI System — Farm Boundary Upload
Lets field staff/exporters upload a real GPS-surveyed farm boundary
(GeoJSON or KML, exported from apps like Fields Area Measure) instead of
hand-drawing on a map — more accurate for actual field data collection.
"""
import streamlit as st
import json
import xml.etree.ElementTree as ET
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


def render_farm_boundary_upload_page(profile: dict):
    st.markdown("# 🛰 Farm Boundary Upload")
    st.markdown(
        "<p style='color:#64748b'>Upload a real GPS-surveyed farm boundary — export from "
        "Fields Area Measure, ODK, or similar field survey apps as GeoJSON or KML.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    supabase = get_client()
    username = profile.get("username", "")
    company = profile.get("company", "") if profile.get("role") != "admin" else ""

    col1, col2 = st.columns(2)
    with col1:
        farm_name = st.text_input("Farm name")
        outgrower_block_id = st.text_input(
            "Outgrower block ID",
            help="Same block ID used in the Certificate Vault — links this boundary to MRL red-listing."
        )
    with col2:
        try:
            q = supabase.table("farmers").select("farmer_id, name, phone, company")
            if company:
                q = q.eq("company", company.strip())
            farmers_result = q.order("name").execute().data
        except Exception:
            farmers_result = []

        if not farmers_result:
            st.warning("No registered farmers found. Register the farmer first before uploading a boundary.")
            selected_farmer_id = None
        else:
            farmer_options = {
                f"{f['name']} ({f['phone']}) — {f['farmer_id']}": f["farmer_id"]
                for f in farmers_result
            }
            selected_label = st.selectbox("Owner / farmer", options=list(farmer_options.keys()))
            selected_farmer_id = farmer_options[selected_label]

    uploaded = st.file_uploader("Boundary file", type=["geojson", "json", "kml"])

    if uploaded is not None and st.button("📍 Save Boundary", type="primary", use_container_width=True):
        if not farm_name:
            st.error("❌ Farm name is required.")
            st.stop()

        if not selected_farmer_id:
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
            st.stop()

        file_bytes = uploaded.getvalue()

        if uploaded.name.lower().endswith(".kml"):
            parse_result = parse_kml_polygon(file_bytes)
        else:
            parse_result = parse_geojson_polygon(file_bytes)

        if not parse_result["success"]:
            st.error(f"❌ {parse_result['error']}")
            st.stop()

        geojson_str = json.dumps(parse_result["geojson"])

        try:
            result = supabase.rpc("insert_farm_boundary", {
                "p_farm_name": farm_name,
                "p_farmer_id": selected_farmer_id,
                "p_outgrower_block_id": outgrower_block_id or None,
                "p_geojson": geojson_str,
            }).execute()

            response = result.data
            if response.get("success"):
                area = response.get("area_hectares")
                st.success(f"✅ Boundary saved for **{farm_name}** — computed area: **{area:.2f} hectares**")
                st.rerun()
            else:
                st.error(f"❌ {response.get('error')}")

        except Exception as e:
            st.error(f"❌ Save failed: {str(e)}")

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
        import pandas as pd
        st.dataframe(pd.DataFrame(farms), use_container_width=True, hide_index=True)
