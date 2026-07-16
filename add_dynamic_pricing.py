with open("trial.py", "r") as f:
    content = f.read()

# Add a function that overlays live prices from platform_settings onto the
# existing PRICING_TIERS structure (keeps cap/desc/color, swaps price_kes only)
old_get_module_tiers = '''def get_module_tiers(module: str = "crops") -> dict:
    return PRICING_TIERS.get(module, PRICING_TIERS["crops"])'''

new_get_module_tiers = '''def _slugify_tier_name(name: str) -> str:
    return name.lower().replace(" ", "_")


def get_module_tiers(module: str = "crops") -> dict:
    """
    Returns PRICING_TIERS for the given module, with price_kes overridden
    by live values from platform_settings (admin-editable), falling back
    to the hardcoded default if a setting row is missing.
    """
    base_tiers = PRICING_TIERS.get(module, PRICING_TIERS["crops"])
    try:
        from supabase_db import get_client
        rows = get_client().table("platform_settings").select(
            "setting_key, setting_value"
        ).execute().data
        price_lookup = {r["setting_key"]: r["setting_value"] for r in rows}
    except Exception:
        price_lookup = {}

    result = {}
    for tier_name, tier_data in base_tiers.items():
        key = f"price_{module}_{_slugify_tier_name(tier_name)}_kes"
        live_price = price_lookup.get(key)
        merged = dict(tier_data)
        if live_price is not None:
            try:
                merged["price_kes"] = float(live_price)
            except (ValueError, TypeError):
                pass  # keep hardcoded default if the stored value is invalid
        result[tier_name] = merged
    return result'''

content = content.replace(old_get_module_tiers, new_get_module_tiers)

with open("trial.py", "w") as f:
    f.write(content)

print("Patched get_module_tiers with live pricing support.")
