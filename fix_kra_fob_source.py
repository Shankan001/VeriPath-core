with open("app.py", "r") as f:
    content = f.read()

old = '''            "notes":       (e.get("Notes","") + f" | KRA:{e.get('KRA_PIN','')} FOB:${e.get('FOB_Value_USD','')}").strip(" |"),'''

new = '''            "notes":       e.get("Notes",""),
            "kra_pin":     e.get("KRA_PIN",""),
            "fob_value_usd": float(e.get("FOB_Value_USD", 0) or 0),'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — kra_pin and fob_value_usd now stored as real columns, notes stays clean.")
