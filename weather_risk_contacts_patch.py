with open("weather_risk.py", "r") as f:
    content = f.read()

# 1. Import the phone normalizer
old_import = "from supabase import create_client, Client"
new_import = "from supabase import create_client, Client\nfrom phone_utils import normalize_kenyan_phone"
content = content.replace(old_import, new_import)

# 2. Replace the placeholder contacts function with a real query
old_func = '''def get_field_team_contacts(farm_id: str):
    """
    Placeholder until a real contacts/staff table exists.
    Returns a list of phone numbers (E.164 format) to notify for this farm.
    TODO: replace with a real query once client field-team contacts are onboarded,
    e.g. SELECT phone FROM field_contacts WHERE farm_boundary_id = farm_id
    """
    test_number = os.environ.get("TEST_ALERT_PHONE_NUMBER", "+254700000000")
    return [test_number]'''

new_func = '''def get_field_team_contacts(farm_id: str):
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

    return [normalized]'''

content = content.replace(old_func, new_func)

with open("weather_risk.py", "w") as f:
    f.write(content)

print("Patched get_field_team_contacts() successfully.")
