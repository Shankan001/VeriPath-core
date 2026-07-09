"""
VeriPath — NDVI Crop Stress Tracker
Pulls NDVI (via Sentinel Hub Statistical API) for every registered farm
boundary, stores the reading, and flags a Drought/Disease Stress Alert
if greenness has dropped >=15% over the last 2 weeks.

Run this on a schedule (e.g. every 14 days) via cron / Railway scheduled job.
"""

import os
import json
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
from supabase import create_client, Client

# ---- Config ----
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SENTINEL_HUB_CLIENT_ID = os.environ["SENTINEL_HUB_CLIENT_ID"]
SENTINEL_HUB_CLIENT_SECRET = os.environ["SENTINEL_HUB_CLIENT_SECRET"]

SENTINEL_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
SENTINEL_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

DROP_THRESHOLD_PCT = 15.0   # trigger alert if NDVI falls 15%+ over 2 weeks
LOOKBACK_DAYS = 14

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_sentinel_token() -> str:
    resp = requests.post(
        SENTINEL_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": SENTINEL_HUB_CLIENT_ID,
            "client_secret": SENTINEL_HUB_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_all_farm_boundaries():
    """Fetch every farm boundary row (id + name), then pull its GeoJSON via RPC."""
    result = supabase.table("farm_boundaries").select("id, farm_name").execute()
    return result.data


def get_boundary_geojson(farm_boundary_id: str):
    result = supabase.rpc(
        "get_farm_boundary_geojson", {"p_farm_boundary_id": farm_boundary_id}
    ).execute()
    return result.data


def classify_ndvi(ndvi_mean: float) -> str:
    if ndvi_mean >= 0.5:
        return "green"
    elif ndvi_mean >= 0.3:
        return "yellow"
    else:
        return "red"


def fetch_ndvi_stats(token: str, geometry: dict, start: date, end: date):
    """
    Calls Sentinel Hub Statistical API for NDVI mean/min/max + cloud cover
    over the given polygon and date range (Sentinel-2 L2A).
    """
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
        output: [
          { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
          { id: "dataMask", bands: 1 }
        ]
      };
    }
    function evaluatePixel(s) {
      let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04);
      return { ndvi: [ndvi], dataMask: [s.dataMask] };
    }
    """

    payload = {
        "input": {
            "bounds": {
                "geometry": geometry,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {"maxCloudCoverage": 60}
            }]
        },
        "aggregation": {
            "timeRange": {
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{end.isoformat()}T23:59:59Z"
            },
            "aggregationInterval": {"of": "P14D"},
            "evalscript": evalscript,
            "resx": 10,
            "resy": 10
        }
    }

    resp = requests.post(
        SENTINEL_STATS_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def parse_stats_response(stats_json: dict):
    """Extract ndvi mean/min/max and cloud cover from the Statistical API response."""
    data = stats_json.get("data", [])
    if not data:
        return None

    latest = data[-1]  # most recent interval
    ndvi_stats = latest["outputs"]["ndvi"]["bands"]["B0"]["stats"]

    return {
        "ndvi_mean": round(ndvi_stats["mean"], 3),
        "ndvi_min": round(ndvi_stats["min"], 3),
        "ndvi_max": round(ndvi_stats["max"], 3),
        "cloud_cover_pct": None,  # populate if SCL band stats added later
        "raw_response": stats_json,
    }


def get_previous_reading(farm_boundary_id: str, before_date: date):
    """Get the most recent ndvi_readings row before `before_date` for this farm."""
    result = (
        supabase.table("ndvi_readings")
        .select("ndvi_mean, reading_date")
        .eq("farm_boundary_id", farm_boundary_id)
        .lt("reading_date", before_date.isoformat())
        .order("reading_date", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def insert_ndvi_reading(farm_boundary_id: str, reading_date: date, stats: dict):
    supabase.table("ndvi_readings").insert({
        "farm_boundary_id": farm_boundary_id,
        "reading_date": reading_date.isoformat(),
        "ndvi_mean": stats["ndvi_mean"],
        "ndvi_min": stats["ndvi_min"],
        "ndvi_max": stats["ndvi_max"],
        "cloud_cover_pct": stats["cloud_cover_pct"],
        "source": "sentinel_hub",
        "raw_response": stats["raw_response"],
    }).execute()


def maybe_create_stress_alert(farm_boundary_id: str, previous_ndvi: float, current_ndvi: float):
    if previous_ndvi <= 0:
        return
    percent_drop = round(((previous_ndvi - current_ndvi) / previous_ndvi) * 100, 2)
    if percent_drop >= DROP_THRESHOLD_PCT:
        supabase.table("ndvi_stress_alerts").insert({
            "farm_boundary_id": farm_boundary_id,
            "previous_ndvi": previous_ndvi,
            "current_ndvi": current_ndvi,
            "percent_drop": percent_drop,
            "alert_type": "drought_disease_stress",
        }).execute()
        print(f"  -> ALERT: {percent_drop}% NDVI drop for farm {farm_boundary_id}")


def run():
    print("Fetching Sentinel Hub token...")
    token = get_sentinel_token()

    today = date.today()
    window_start = today - timedelta(days=LOOKBACK_DAYS)

    farms = get_all_farm_boundaries()
    print(f"Found {len(farms)} farm boundaries.")

    for farm in farms:
        farm_id = farm["id"]
        farm_name = farm.get("farm_name", "unknown")
        print(f"Processing {farm_name} ({farm_id})...")

        geojson = get_boundary_geojson(farm_id)
        if not geojson:
            print(f"  -> No boundary geometry found, skipping.")
            continue

        try:
            stats_json = fetch_ndvi_stats(token, geojson, window_start, today)
            stats = parse_stats_response(stats_json)
        except Exception as e:
            print(f"  -> Sentinel Hub error: {e}")
            continue

        if stats is None:
            print(f"  -> No NDVI data returned (likely cloud cover), skipping.")
            continue

        band = classify_ndvi(stats["ndvi_mean"])
        print(f"  -> NDVI mean {stats['ndvi_mean']} ({band})")

        previous = get_previous_reading(farm_id, today)

        insert_ndvi_reading(farm_id, today, stats)

        if previous:
            maybe_create_stress_alert(farm_id, previous["ndvi_mean"], stats["ndvi_mean"])

    print("Done.")


if __name__ == "__main__":
    run()
