"""
Attacker's-eye audit: with ONLY the public anon key, try to read every
table/view and list callable RPC functions. Any table returning rows
(other than the intentionally public ones) is a leak.
Run before AND after every schema change.
"""
import os, sys, requests
from dotenv import load_dotenv
load_dotenv()

URL = os.environ["SUPABASE_URL"].rstrip("/")
ANON = os.environ.get("SUPABASE_ANON_KEY")
if not ANON:
    sys.exit("Set SUPABASE_ANON_KEY in .env first (Supabase > Project Settings > API).")

H = {"apikey": ANON, "Authorization": f"Bearer {ANON}"}
ALLOWED_PUBLIC = {"public_farm_profiles", "public_listings"}

KNOWN = [
    "users", "invite_codes", "password_reset_codes", "user_sessions", "companies",
    "company_contacts", "company_documents", "animals", "animal_costs", "animal_temps",
    "alert_log", "bolus_installations", "device_registry", "hardware_registry",
    "disease_assessments", "symptom_logs", "vet_consultations", "milk_records",
    "growth_records", "feed_input_records", "output_records", "muzzle_registry",
    "farmers", "farmer_activities", "farm_boundaries", "consignments", "ledger",
    "export_regulatory_vault", "auction_lot_traceability", "ndvi_readings",
    "ndvi_stress_alerts", "weather_risk_events", "payments", "platform_settings",
    "kpi_overrides", "security_audit_log", "support_tickets", "transmission_log",
    "profiles", "crop_reference", "animal_adg", "animal_cost_per_kg_gained",
    "animal_fcr", "public_farm_links", "public_listing_links",
    "public_farm_profiles", "public_listings",
]

names, rpcs = set(KNOWN), []
try:
    r = requests.get(f"{URL}/rest/v1/", headers=H, timeout=20)
    if r.ok:
        for p in r.json().get("paths", {}):
            if p.startswith("/rpc/"):
                rpcs.append(p[5:])
            elif p.count("/") == 1 and p != "/":
                names.add(p.strip("/"))
    else:
        print(f"(OpenAPI listing unavailable: HTTP {r.status_code}; using known list only)")
except Exception as e:
    print(f"(OpenAPI listing failed: {e}; using known list only)")

leaks, blocked, empty, missing = [], [], [], []
public_seen = {}
for n in sorted(names):
    r = requests.get(f"{URL}/rest/v1/{n}?select=*&limit=1", headers=H, timeout=20)
    if r.status_code == 404:
        missing.append(n)
    elif r.status_code in (401, 403):
        blocked.append(n)
    elif r.status_code == 200:
        if r.json():
            if n in ALLOWED_PUBLIC:
                public_seen[n] = r.json()
            else:
                leaks.append(n)
        else:
            empty.append(n)
    else:
        print(f"  ? {n}: HTTP {r.status_code}")

print("\n=== LEAK AUDIT (anon key) ===")
print(f"BLOCKED (permission denied): {len(blocked)}")
print(f"NO ROWS VISIBLE (blocked by RLS OR genuinely empty): {len(empty)}")
print(f"  {', '.join(empty) or '-'}")
print(f"NOT FOUND (no such table): {len(missing)}")
print(f"\n!!! LEAKS (anon can read rows): {len(leaks)}")
for n in leaks:
    print(f"  LEAK -> {n}")
if rpcs:
    print("\nREVIEW: functions callable via the public API (check each is safe):")
    for f in rpcs:
        print(f"  rpc/{f}")
print("\nNote: 'no rows visible' on an EMPTY table proves nothing yet; re-run once it has data.")
print("\nINTENDED-PUBLIC tables (rows visible to anon, limit 1):")
for n in sorted(ALLOWED_PUBLIC):
    rows = public_seen.get(n)
    if rows:
        print(f"  {n}: columns = {sorted(rows[0].keys())}")
        bad = {"animal_tag", "company"} & set(rows[0].keys())
        if bad:
            print(f"  !!! {n} EXPOSES PRIVATE COLUMNS: {sorted(bad)}")
    else:
        print(f"  {n}: no rows visible")

sys.exit(1 if leaks else 0)
