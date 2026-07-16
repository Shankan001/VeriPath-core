with open("kpi_dashboard.py", "r") as f:
    content = f.read()

old = '''            price          = TIER_PRICES_KES.get(new_tier, 0) * months'''

new = '''            from trial import get_module_tiers, _get_company_module
            _module = _get_company_module(target_company)
            _tiers = get_module_tiers(_module)
            price = _tiers.get(new_tier, {}).get("price_kes", 0) * months'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("Patched upgrade form pricing.")
