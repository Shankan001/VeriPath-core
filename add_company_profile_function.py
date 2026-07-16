with open("supabase_db.py", "r") as f:
    content = f.read()

old = "def increment_company_containers(company_name: str) -> int:"

new = '''def update_company_profile(company_name: str, exporter_kra_pin: str = None,
                            afa_license_number: str = None) -> bool:
    try:
        key = _company_key(company_name)
        updates = {}
        if exporter_kra_pin is not None:
            updates["exporter_kra_pin"] = exporter_kra_pin.strip()
        if afa_license_number is not None:
            updates["afa_license_number"] = afa_license_number.strip()
        if not updates:
            return True
        get_client().table("companies").update(updates).eq("company_key", key).execute()
        return True
    except Exception as e:
        print(f"[DB] update_company_profile error: {e}")
        return False


def increment_company_containers(company_name: str) -> int:'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("supabase_db.py", "w") as f:
        f.write(content)
    print("Added update_company_profile function.")
