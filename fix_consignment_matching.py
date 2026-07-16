with open("app.py", "r") as f:
    content = f.read()

old = '''                from db import add_consignment
                submitted_farmer_names = {
                    r.get("farmer_name") for r in all_results if r["status"] == "submitted"
                }
                for record in approved:
                    if record.get("farmer_name") in submitted_farmer_names:'''

new = '''                from db import add_consignment
                submitted_consignment_ids = {
                    r.get("consignment") for r in all_results if r["status"] == "submitted"
                }
                for record in approved:
                    if record.get("session_id") in submitted_consignment_ids:'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — now matching on consignment ID (session_id), not the non-existent farmer_name field.")
