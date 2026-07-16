with open("app.py", "r") as f:
    content = f.read()

old = '''                            "kra_pin":         record.get("notes", "").split("FOB:")[0].replace("KRA:","").strip() if "KRA:" in record.get("notes","") else "",
                            "pin_valid":       "valid" if "KRA:" in record.get("notes","") else "unknown",
                            "hs_code":         record.get("hs_code", ""),
                            "origin_county":   record.get("county", ""),
                            "net_weight_kg":   record.get("weight_kg", 0),
                            "fob_value_usd":   float(record.get("notes","").split("FOB:$")[1]) if "FOB:$" in record.get("notes","") else 0.0,'''

new = '''                            "kra_pin":         record.get("kra_pin", ""),
                            "pin_valid":       "valid" if record.get("kra_pin") else "unknown",
                            "hs_code":         record.get("hs_code", ""),
                            "origin_county":   record.get("county", ""),
                            "net_weight_kg":   record.get("weight_kg", 0),
                            "fob_value_usd":   record.get("fob_value_usd", 0.0),'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — Transmit to Portals now uses real columns, no more text-parsing.")
