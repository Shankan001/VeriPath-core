with open("kpi_dashboard.py","r") as f:
    content = f.read()

# Replace file-based loads with Supabase
old1 = '''def _load(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def _save_kpi_overrides(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KPI_FILE, "w") as f:
        json.dump(data, f, indent=2)'''

new1 = '''def _load_kpi_overrides_local():
    from supabase_db import load_kpi_overrides
    return load_kpi_overrides()

def _save_kpi_overrides(data):
    from supabase_db import save_kpi_overrides
    save_kpi_overrides(
        data.get("cac_kes", 5000),
        data.get("churn_rate_pct", 0.0)
    )'''

old2 = '''    companies = _load(COMPANIES_FILE)
    overrides = _load(KPI_FILE)'''
new2 = '''    from supabase_db import load_companies, load_users
    companies = load_companies()
    overrides = _load_kpi_overrides_local()'''

old3 = '''    users = _load(USERS_FILE)'''
new3 = '''    from supabase_db import load_users
    users = load_users()'''

old4 = '''    overrides = _load(KPI_FILE)'''
new4 = '''    overrides = _load_kpi_overrides_local()'''

for o, n, label in [
    (old1, new1, "load/save helpers"),
    (old2, new2, "compute_kpis companies"),
    (old3, new3, "compute_kpis users"),
    (old4, new4, "render overrides"),
]:
    if o in content:
        content = content.replace(o, n)
        print(f"✅ {label} patched")
    else:
        print(f"⚠️ {label} not found")

with open("kpi_dashboard.py","w") as f:
    f.write(content)
