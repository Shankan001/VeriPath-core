"""
VeriPath — EUDR Deforestation Risk Check via FAO Whisp API
Submits a farm's real polygon and returns Whisp's risk classification,
based on the "convergence of evidence" approach across multiple satellite
datasets, relative to the Dec 31 2020 EUDR cutoff.

Whisp results are ephemeral (not stored by FAO) — the caller is responsible
for persisting the result (see farm_boundaries.deforestation_* columns).
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

WHISP_API_KEY = os.environ.get("WHISP_API_KEY", "")
WHISP_BASE_URL = "https://whisp.openforis.org/api"

POLL_INTERVAL_SECONDS = 3
MAX_POLL_ATTEMPTS = 40  # ~2 minutes max wait


def submit_polygon_for_analysis(polygon_geojson: dict) -> dict:
    """
    Submits a single farm polygon to Whisp. Whisp expects a
    FeatureCollection, so we wrap a bare Polygon if needed.
    Returns {"success": True, "token": "..."} or {"success": False, "error": "..."}.
    """
    if not WHISP_API_KEY:
        return {"success": False, "error": "WHISP_API_KEY not configured."}

    if polygon_geojson.get("type") != "FeatureCollection":
        feature_collection = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": polygon_geojson,
            }]
        }
    else:
        feature_collection = polygon_geojson

    try:
        resp = requests.post(
            f"{WHISP_BASE_URL}/submit/geojson",
            headers={"X-API-KEY": WHISP_API_KEY, "Content-Type": "application/json"},
            json=feature_collection,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token")
        if not token:
            return {"success": False, "error": f"No token in response: {data}"}
        return {"success": True, "token": token}
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_for_result(token: str) -> dict:
    """
    Polls /status/{token} until the job completes or times out.
    Returns {"success": True, "result": {...}} or {"success": False, "error": "..."}.
    """
    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            resp = requests.get(
                f"{WHISP_BASE_URL}/status/{token}",
                headers={"X-API-KEY": WHISP_API_KEY},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "").lower()

            if status == "completed":
                return {"success": True, "result": data}
            elif status in ("failed", "error", "cancelled"):
                return {"success": False, "error": f"Job {status}: {data}"}
            # else still queued/running — wait and retry
            time.sleep(POLL_INTERVAL_SECONDS)
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Timed out waiting for Whisp analysis to complete."}


def check_deforestation_risk(polygon_geojson: dict) -> dict:
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
    }
