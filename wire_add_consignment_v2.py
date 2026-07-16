with open("app.py", "r") as f:
    content = f.read()

old = '''                save_transmission_log(all_results)

                # ── Results display ────────────────────────────────────
                success = [r for r in all_results if r["status"] == "submitted"]'''

new = '''                save_transmission_log(all_results)

                # ── Create real consignment records for successfully
                # transmitted batches (previously never wired in —
                # consignments table stayed empty regardless of submission)
                from db import add_consignment
                submitted_farmer_names = {
                    r.get("farmer_name") for r in all_results if r["status"] == "submitted"
                }
                for record in approved:
                    if record.get("farmer_name") in submitted_farmer_names:
                        add_consignment({
                            "consignment_id": record.get("session_id", ""),
                            "farmer_name":     record.get("farmer_name", ""),
                            "crop_type":       record.get("crop", ""),
                            "kra_pin":         record.get("kra_pin", ""),
                            "pin_valid":       "valid" if record.get("kra_pin") else "unknown",
                            "hs_code":         record.get("hs_code", ""),
                            "origin_county":   record.get("county", ""),
                            "net_weight_kg":   record.get("weight_kg", 0),
                            "fob_value_usd":   record.get("fob_value_usd", 0.0),
                            "source":          "transmit_to_portals",
                        }, company=profile.get("company",""))

                # ── Results display ────────────────────────────────────
                success = [r for r in all_results if r["status"] == "submitted"]'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — add_consignment wired in, using real kra_pin/fob_value_usd columns.")
