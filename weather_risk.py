"""
VeriPath — Flash Weather Risk Model
Pulls current + forecast weather for every farm boundary's centroid via
OpenWeatherMap, checks for extreme heat / flash flood / unseasonal rainfall,
and sends an SMS alert via Africa's Talking 48 hours ahead when triggered.

Run this on a schedule (e.g. every 6-12 hours) via cron / Railway scheduled job.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from phone_utils import normalize_kenyan_phone

load_dotenv()

# ---- Config ----
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
AT_API_KEY = os.environ["AT_API_KEY"]
AT_USERNAME = os.environ["AT_USERNAME"]  # "sandbox" until you go live

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/forecast"
AT_SMS_URL = (
    "https://api.sandbox.africastalking.com/version1/messaging"
    if AT_USERNAME == "sandbox"
    else "https://api.africastalking.com/version1/messaging"
)

# Thresholds
EXTREME_HEAT_C = 35.0
FLASH_FLOOD_RAIN_MM_3H = 30.0     # heavy rain in a 3h forecast bucket
UNSEASONAL_RAIN_MM_3H = 15.0      # placeholder threshold until seasonal calendar exists

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_all_farm_centroids():
    """
    Fetch every farm boundary's centroid lat/lng using PostGIS ST_Centroid,
    via a raw SQL query (Supabase Python client can't do ST_ functions directly).
    """
    result = supabase.rpc("get_farm_centroids").execute()
    return result.data


def fetch_weather_forecast(lat: float, lon: float):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    resp = requests.get(OPENWEATHER_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def evaluate_risk(forecast_json: dict):
    """
    Look at the next ~48 hours of 3-hour forecast buckets (16 entries) and
    flag the first risk condition found. Returns a list of risk dicts
    (a farm could have multiple risks in the window).
    """
    risks = []
    buckets = forecast_json.get("list", [])[:16]  # ~48h of 3h buckets

    for bucket in buckets:
        dt_txt = bucket.get("dt_txt")
        temp = bucket.get("main", {}).get("temp")
        rain_3h = bucket.get("rain", {}).get("3h", 0.0)

        if temp is not None and temp >= EXTREME_HEAT_C:
            risks.append({
                "risk_type": "extreme_heat",
                "severity": "warning" if temp >= EXTREME_HEAT_C + 3 else "watch",
                "forecast_value": temp,
                "recommended_action": "Increase irrigation frequency; shade young plants; reschedule fieldwork to early morning/evening.",
                "forecast_time": dt_txt,
            })

        if rain_3h >= FLASH_FLOOD_RAIN_MM_3H:
            risks.append({
                "risk_type": "flash_flood",
                "severity": "warning",
                "forecast_value": rain_3h,
                "recommended_action": "Clear drainage channels; move harvested produce to higher ground; delay pesticide/fertilizer application.",
                "forecast_time": dt_txt,
            })
        elif rain_3h >= UNSEASONAL_RAIN_MM_3H:
            risks.append({
                "risk_type": "unseasonal_rainfall",
                "severity": "watch",
                "forecast_value": rain_3h,
                "recommended_action": "Delay spraying operations; check for waterlogging in low-lying plots.",
                "forecast_time": dt_txt,
            })

        if risks:
            break  # first risk found in the 48h window is enough to alert on

    return risks


def get_field_team_contacts(farm_id: str):
    """
    Looks up the real farmer(s) linked to this farm boundary via
    farm_boundaries.farmer_id -> farmers.farmer_id, and returns their
    phone number(s) normalized to E.164 for SMS delivery.

    Falls back to TEST_ALERT_PHONE_NUMBER only if no valid contact is found,
    so alerts never silently go nowhere during testing.
    """
    try:
        boundary = (
            supabase.table("farm_boundaries")
            .select("farmer_id, farm_name")
            .eq("id", farm_id)
            .single()
            .execute()
            .data
        )
    except Exception as e:
        print(f"  -> Could not look up farm_boundaries.farmer_id for farm {farm_id}: {e}")
        boundary = None

    if not boundary or not boundary.get("farmer_id"):
        print(f"  -> No farmer linked to farm {farm_id}, using test fallback number.")
        test_number = os.environ.get("TEST_ALERT_PHONE_NUMBER", "+254700000000")
        return [test_number]

    try:
        farmer = (
            supabase.table("farmers")
            .select("name, phone")
            .eq("farmer_id", boundary["farmer_id"])
            .single()
            .execute()
            .data
        )
    except Exception as e:
        print(f"  -> Could not look up farmer {boundary['farmer_id']}: {e}")
        farmer = None

    if not farmer or not farmer.get("phone"):
        print(f"  -> Farmer {boundary['farmer_id']} has no phone on file, using test fallback number.")
        test_number = os.environ.get("TEST_ALERT_PHONE_NUMBER", "+254700000000")
        return [test_number]

    normalized = normalize_kenyan_phone(farmer["phone"])
    if not normalized:
        print(f"  -> Could not normalize phone '{farmer['phone']}' for {farmer.get('name', 'unknown')}, skipping.")
        return []

    return [normalized]


def send_sms_alert(phone_numbers: list, message: str):
    headers = {
        "apiKey": AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    payload = {
        "username": AT_USERNAME,
        "to": ",".join(phone_numbers),
        "message": message,
    }
    resp = requests.post(AT_SMS_URL, data=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def log_weather_event(farm_id: str, risk: dict, sms_sent: bool, raw_response: dict):
    supabase.table("weather_risk_events").insert({
        "farm_id": farm_id,
        "risk_type": risk["risk_type"],
        "severity": risk["severity"],
        "forecast_value": risk["forecast_value"],
        "forecast_window_hours": 48,
        "recommended_action": risk["recommended_action"],
        "sms_sent": sms_sent,
        "raw_response": raw_response,
    }).execute()


def run():
    farms = get_all_farm_centroids()
    print(f"Found {len(farms)} farm centroids.")

    for farm in farms:
        farm_id = farm["farm_boundary_id"]
        farm_name = farm.get("farm_name", "unknown")
        lat, lon = farm["lat"], farm["lon"]

        print(f"Checking weather for {farm_name} ({lat}, {lon})...")

        try:
            forecast = fetch_weather_forecast(lat, lon)
        except Exception as e:
            print(f"  -> OpenWeatherMap error: {e}")
            continue

        risks = evaluate_risk(forecast)
        if not risks:
            print("  -> No risk detected.")
            continue

        for risk in risks:
            print(f"  -> RISK: {risk['risk_type']} ({risk['severity']}) at {risk['forecast_time']}")

            contacts = get_field_team_contacts(farm_id)
            message = (
                f"VeriPath Alert [{risk['severity'].upper()}]: {farm_name} — "
                f"{risk['risk_type'].replace('_', ' ').title()} expected around {risk['forecast_time']}. "
                f"Action: {risk['recommended_action']}"
            )

            sms_sent = False
            sms_response = {}
            try:
                sms_response = send_sms_alert(contacts, message)
                sms_sent = True
                print(f"  -> SMS sent to {contacts}")
            except Exception as e:
                print(f"  -> Africa's Talking error: {e}")

            log_weather_event(farm_id, risk, sms_sent, {"forecast": forecast, "sms_response": sms_response})

    print("Done.")


if __name__ == "__main__":
    run()
