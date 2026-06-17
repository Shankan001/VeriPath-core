with open("kpi_dashboard.py", "r") as f:
    content = f.read()

old = "companies_list = list_all_companies()"
new = "companies_list = list_all_companies(exporters_only=True)"

if old in content:
    content = content.replace(old, new)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("✅ kpi_dashboard.py patched — dropdown now shows exporter companies only")
else:
    print("❌ Target line not found — paste your kpi_dashboard.py list_all_companies call")
