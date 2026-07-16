with open("trial.py", "r") as f:
    content = f.read()

old = '''def _get_module(username: str) -> str:'''

new = '''def _get_company_module(company_name: str) -> str:
    """Determine a company's module by checking any of its users' module field."""
    try:
        from supabase_db import get_client
        rows = get_client().table("users").select("module").eq(
            "company", company_name
        ).limit(1).execute().data
        if rows and rows[0].get("module"):
            return "livestock" if "Livestock" in rows[0]["module"] else "crops"
    except Exception:
        pass
    return "crops"


def _get_module(username: str) -> str:'''

content = content.replace(old, new)

with open("trial.py", "w") as f:
    f.write(content)

print("Added _get_company_module helper.")
