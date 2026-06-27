import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

EUDR_HIGH_RISK_CROPS = ["avocado", "coffee", "cocoa", "palm oil", "soya", "timber", "rubber"]

COUNTY_RISK = {
    "Meru": "Amber", "Kirinyaga": "Amber", "Murang'a": "Amber",
    "Nyeri": "Green", "Kiambu": "Green", "Nakuru": "Green",
    "Trans Nzoia": "Amber", "Uasin Gishu": "Green",
}

def score_batch(batch: dict) -> dict:
    crop = (batch.get("crop_type") or "").lower()
    county = batch.get("county") or ""
    deforestation_declared = batch.get("deforestation_declared", False)

    risk = "Green"

    if any(c in crop for c in EUDR_HIGH_RISK_CROPS):
        risk = "Amber"

    county_risk = COUNTY_RISK.get(county, "Green")
    if county_risk == "Amber" and risk == "Green":
        risk = "Amber"

    if deforestation_declared:
        risk = "Red"

    return {
        "farmer_id": batch.get("farmer_id"),
        "farmer_name": batch.get("farmer_name"),
        "crop_type": batch.get("crop_type"),
        "county": county,
        "eudr_risk": risk,
        "weight_kg": batch.get("weight_kg"),
        "batch_id": batch.get("id"),
    }

def get_eudr_scores(company_id: str):
    result = supabase.table("ledger") \
        .select("*") \
        .eq("company_id", company_id) \
        .execute()
    
    rows = result.data or []
    scored = [score_batch(row) for row in rows]
    return scored

