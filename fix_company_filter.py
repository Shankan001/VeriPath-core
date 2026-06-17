with open("trial.py", "r") as f:
    content = f.read()

old = '''def list_all_companies() -> list[dict]:
    companies = _load_companies()
    result = []
    for key, rec in companies.items():
        result.append({
            "Company":     rec.get("company_name", key),
            "Tier":        rec.get("subscription_tier", "trial"),
            "Trial Start": rec.get("trial_started_at", "")[:10],
            "Expires":     rec.get("tier_expires_at", "")[:10] if rec.get("tier_expires_at") else "—",
            "Containers":  rec.get("containers_used", 0),
        })
    return sorted(result, key=lambda x: x["Company"])'''

new = '''def list_all_companies(exporters_only: bool = False) -> list[dict]:
    companies  = _load_companies()
    users      = _load_users()

    # Build set of companies that have at least one exporter registered
    exporter_companies = {
        _normalize_company(u.get("company", ""))
        for u in users.values()
        if u.get("role") == "exporter"
    }

    result = []
    for key, rec in companies.items():
        if exporters_only and key not in exporter_companies:
            continue
        result.append({
            "Company":     rec.get("company_name", key),
            "Tier":        rec.get("subscription_tier", "trial"),
            "Trial Start": rec.get("trial_started_at", "")[:10],
            "Expires":     rec.get("tier_expires_at", "")[:10] if rec.get("tier_expires_at") else "—",
            "Containers":  rec.get("containers_used", 0),
        })
    return sorted(result, key=lambda x: x["Company"])'''

content = content.replace(old, new)

with open("trial.py", "w") as f:
    f.write(content)

print("✅ list_all_companies patched — exporters_only filter added")
