with open("app.py", "r") as f:
    content = f.read()

# Remove any broken partial imports first
for bad in [
    "from trial           import render_trial_banner, render_container_tracker\n",
    "from kpi_dashboard   import render_kpi_dashboard\n",
    "from invite_codes    import generate_invite_code, list_invite_codes, ROLE_PREFIXES\n",
]:
    content = content.replace(bad, "")

# Add clean imports right after data_ingestion import
old = "from data_ingestion  import render_data_ingestion_page"
new = """from data_ingestion  import render_data_ingestion_page
from trial           import render_trial_banner, render_container_tracker
from kpi_dashboard   import render_kpi_dashboard
from invite_codes    import generate_invite_code, list_invite_codes, ROLE_PREFIXES"""

content = content.replace(old, new)

with open("app.py", "w") as f:
    f.write(content)

# Verify
if "render_container_tracker" in content and "render_kpi_dashboard" in content:
    print("✅ Imports fixed correctly.")
else:
    print("❌ Something still wrong — paste app.py lines 1-20")
