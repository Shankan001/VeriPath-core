with open("kpi_dashboard.py", "r") as f:
    content = f.read()

# 1. Remove the hardcoded TIER_PRICES_KES dict entirely
old_dict = '''TIER_PRICES_KES = {
    "Starter":       2_500,
    "Growth":       20_000,
    "Enterprise":   65_000,
    "Green Channel":150_000,
    "trial":              0,
}'''
content = content.replace(old_dict, "")

# 2. Fix the MRR calculation to be module-aware
old_mrr = '''    mrr = sum(TIER_PRICES_KES.get(c.get("subscription_tier","trial"), 0)
              for c in companies.values())'''

new_mrr = '''    from trial import get_module_tiers, _get_company_module
    mrr = 0
    for c in companies.values():
        tier = c.get("subscription_tier", "trial")
        if tier in ("trial", "expired_paid"):
            continue
        company_name = c.get("company_name", "")
        module = _get_company_module(company_name)
        tiers = get_module_tiers(module)
        mrr += tiers.get(tier, {}).get("price_kes", 0)'''

content = content.replace(old_mrr, new_mrr)

with open("kpi_dashboard.py", "w") as f:
    f.write(content)

print("Patched MRR calculation to be module-aware.")
