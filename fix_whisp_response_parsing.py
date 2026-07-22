with open("whisp_check.py", "r") as f:
    content = f.read()

old = '''def check_deforestation_risk(polygon_geojson: dict) -> dict:
    """
    Full submit + poll flow. Returns:
    {
        "success": bool,
        "risk": "low" | "high" | "unknown",
        "raw_result": {...} | None,
        "error": str | None,
    }
    """
    submit_result = submit_polygon_for_analysis(polygon_geojson)
    if not submit_result["success"]:
        return {"success": False, "risk": "unknown", "raw_result": None, "error": submit_result["error"]}

    poll_result = poll_for_result(submit_result["token"])
    if not poll_result["success"]:
        return {"success": False, "risk": "unknown", "raw_result": None, "error": poll_result["error"]}

    result_data = poll_result["result"]

    # Extract risk classification from the result GeoJSON's feature properties.
    # NOTE: exact property key name needs confirming against a real response —
    # placeholder key used here, verify once we get a real test result.
    risk = "unknown"
    try:
        features = result_data.get("features", [])
        if features:
            props = features[0].get("properties", {})
            risk = props.get("whisp_risk", props.get("risk", "unknown"))
    except Exception:
        pass

    return {"success": True, "risk": risk, "raw_result": result_data, "error": None}'''

new = '''def check_deforestation_risk(polygon_geojson: dict) -> dict:
    """
    Submits a polygon and returns Whisp's risk classification. Whisp's
    /submit/geojson endpoint returns results synchronously (no polling
    needed) — this was confirmed against a real response on 2026-07-21.

    Returns:
    {
        "success": bool,
        "risk_perennial_crop": "low"|"high"|"unknown",
        "risk_annual_crop": "low"|"high"|"unknown",
        "risk_timber": "low"|"high"|"unknown",
        "area_ha": float | None,
        "tree_cover_loss_after_2020_ha": float | None,
        "raw_result": {...} | None,
        "error": str | None,
    }
    """
    if not WHISP_API_KEY:
        return {"success": False, "error": "WHISP_API_KEY not configured.",
                "risk_perennial_crop": "unknown", "risk_annual_crop": "unknown",
                "risk_timber": "unknown", "area_ha": None,
                "tree_cover_loss_after_2020_ha": None, "raw_result": None}

    if polygon_geojson.get("type") != "FeatureCollection":
        feature_collection = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": polygon_geojson}]
        }
    else:
        feature_collection = polygon_geojson

    try:
        resp = requests.post(
            f"{WHISP_BASE_URL}/submit/geojson",
            headers={"X-API-KEY": WHISP_API_KEY, "Content-Type": "application/json"},
            json=feature_collection,
            timeout=60,
        )
        resp.raise_for_status()
        response_data = resp.json()
    except Exception as e:
        return {"success": False, "error": str(e),
                "risk_perennial_crop": "unknown", "risk_annual_crop": "unknown",
                "risk_timber": "unknown", "area_ha": None,
                "tree_cover_loss_after_2020_ha": None, "raw_result": None}

    if response_data.get("code") != "analysis_completed":
        return {"success": False, "error": f"Unexpected response: {response_data}",
                "risk_perennial_crop": "unknown", "risk_annual_crop": "unknown",
                "risk_timber": "unknown", "area_ha": None,
                "tree_cover_loss_after_2020_ha": None, "raw_result": response_data}

    try:
        features = response_data["data"]["features"]
        props = features[0]["properties"]
    except (KeyError, IndexError):
        return {"success": False, "error": "Could not find feature properties in response.",
                "risk_perennial_crop": "unknown", "risk_annual_crop": "unknown",
                "risk_timber": "unknown", "area_ha": None,
                "tree_cover_loss_after_2020_ha": None, "raw_result": response_data}

    return {
        "success": True,
        "risk_perennial_crop": props.get("risk_pcrop", "unknown"),
        "risk_annual_crop": props.get("risk_acrop", "unknown"),
        "risk_timber": props.get("risk_timber", "unknown"),
        "area_ha": props.get("Area"),
        "tree_cover_loss_after_2020_ha": props.get("GFC_loss_after_2020"),
        "raw_result": response_data,
        "error": None,
    }'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("whisp_check.py", "w") as f:
        f.write(content)
    print("Patched — now correctly parsing the real synchronous Whisp response.")
