with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

# Add company scoping right after supabase/username are set
old_setup = '''    supabase = get_client()
    username = profile.get("username", "")'''

new_setup = '''    supabase = get_client()
    username = profile.get("username", "")
    company = profile.get("company", "") if profile.get("role") != "admin" else ""'''

content = content.replace(old_setup, new_setup)

# Filter the farmer dropdown query by company (unless admin, who sees all)
old_query = '''        try:
            farmers_result = supabase.table("farmers").select(
                "farmer_id, name, phone"
            ).order("name").execute().data
        except Exception:
            farmers_result = []'''

new_query = '''        try:
            q = supabase.table("farmers").select("farmer_id, name, phone, company")
            if company:
                q = q.eq("company", company.strip())
            farmers_result = q.order("name").execute().data
        except Exception:
            farmers_result = []'''

content = content.replace(old_query, new_query)

with open("farm_boundary_upload.py", "w") as f:
    f.write(content)

print("Patched company scoping successfully.")
