# ── EUDR Risk Engine ──────────────────────────────────────────
# EU Deforestation Regulation (2023/1115) compliance scoring
# Risk is based on crop sensitivity + county forest cover data
# Source: Kenya Forest Service + EU JRC Global Forest Watch data

# Crops covered under EUDR (must prove no deforestation post-2020)
EUDR_REGULATED_CROPS = {
    "Coffee":         "high",    # Top EU concern — full traceability required
    "Avocado":        "high",    # Kenya's #1 EU export — high scrutiny
    "Tea":            "medium",  # Covered but lower deforestation link
    "Maize":          "medium",  # Covered under soy/feed chain rules
    "Macadamia Nuts": "medium",  # Tree crop — requires plot-level data
    "Mango":          "low",     # Covered but low EU import volume
    "Pineapple":      "low",
    "Passion Fruit":  "low",
    "French Beans":   "low",     # Vegetable — lower EUDR risk
    "Roses":          "exempt",  # NOT covered under EUDR
}

# County-level deforestation risk index (0.0 - 1.0)
# Based on Kenya Forest Service 2023 report + Global Forest Watch data
# High = significant forest loss recorded post-2020
COUNTY_DEFORESTATION_INDEX = {
    "Murang'a":       0.82,  # High — Aberdare encroachment
    "Kirinyaga":      0.78,  # High — Mt Kenya forest edge
    "Nyeri":          0.75,  # High — Mt Kenya/Aberdare corridor
    "Meru":           0.72,  # High — Mt Kenya northern slopes
    "Embu":           0.70,  # High — Mt Kenya southern slopes
    "Kericho":        0.65,  # Medium-High — tea belt clearing
    "Bomet":          0.63,
    "Nandi":          0.60,
    "Kakamega":       0.58,  # Medium — Western Kenya deforestation
    "Bungoma":        0.55,
    "Trans Nzoia":    0.52,
    "Kiambu":         0.50,
    "Laikipia":       0.45,
    "Nakuru":         0.42,
    "Uasin Gishu":    0.38,
    "Narok":          0.35,
    "Machakos":       0.28,
    "Makueni":        0.25,
    "Kitui":          0.22,
    "Kajiado":        0.20,
    "Nairobi":        0.10,
    "Mombasa":        0.08,
    "Kisumu":         0.15,
    "Kilifi":         0.18,
    "Kwale":          0.22,
    "Taita-Taveta":   0.30,
}
DEFAULT_DEFORESTATION_INDEX = 0.40  # For counties not in the list

def get_eudr_risk(crop: str, county: str) -> dict:
    """
    Score a single consignment for EUDR compliance risk.
    Returns a dict with risk_level, risk_score, badge, and explanation.
    """
    crop_risk  = EUDR_REGULATED_CROPS.get(crop, "low")
    forest_idx = COUNTY_DEFORESTATION_INDEX.get(county, DEFAULT_DEFORESTATION_INDEX)

    # Exempt crops skip scoring
    if crop_risk == "exempt":
        return {
            "risk_level":   "Exempt",
            "risk_score":   0.0,
            "badge":        "⚪ Exempt",
            "explanation":  f"{crop} is not regulated under EUDR.",
            "action":       "No due diligence required.",
        }

    # Weighted score: 60% crop sensitivity, 40% county forest loss
    crop_weight = {"high": 1.0, "medium": 0.5, "low": 0.2}.get(crop_risk, 0.2)
    risk_score  = round((crop_weight * 0.6) + (forest_idx * 0.4), 3)

    if risk_score >= 0.65:
        risk_level  = "High"
        badge       = "🔴 High Risk"
        action      = "Full geo-location & plot mapping required before EU export."
    elif risk_score >= 0.35:
        risk_level  = "Medium"
        badge       = "🟡 Medium Risk"
        action      = "Supplier declaration + county-level forest check required."
    else:
        risk_level  = "Low"
        badge       = "🟢 Low Risk"
        action      = "Standard due diligence sufficient. No blocking risk."

    return {
        "risk_level":   risk_level,
        "risk_score":   risk_score,
        "badge":        badge,
        "explanation":  f"{crop} ({crop_risk} sensitivity) from {county} (forest index: {forest_idx})",
        "action":       action,
    }

def score_dataframe(df):
    """
    Add EUDR_Risk and EUDR_Score columns to a consignment DataFrame.
    Returns the updated DataFrame.
    """
    import pandas as pd
    if df.empty:
        return df
    results = df.apply(
        lambda row: get_eudr_risk(
            str(row.get("Crop_Type", "")),
            str(row.get("Origin_County", ""))
        ),
        axis=1
    )
    df = df.copy()
    df["EUDR_Risk"]  = results.apply(lambda r: r["badge"])
    df["EUDR_Score"] = results.apply(lambda r: r["risk_score"])
    df["EUDR_Action"]= results.apply(lambda r: r["action"])
    return df

if __name__ == "__main__":
    tests = [
        ("Avocado",      "Murang'a"),
        ("Coffee",       "Nyeri"),
        ("French Beans", "Nairobi"),
        ("Roses",        "Kiambu"),
        ("Tea",          "Kericho"),
    ]
    print(f"{'Crop':<16} {'County':<14} {'Badge':<18} {'Score':<8} Action")
    print("-" * 80)
    for crop, county in tests:
        r = get_eudr_risk(crop, county)
        print(f"{crop:<16} {county:<14} {r['badge']:<18} {r['risk_score']:<8} {r['action'][:40]}")
