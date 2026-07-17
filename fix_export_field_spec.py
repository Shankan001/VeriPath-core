with open("bridge_engine.py") as f:
    src = f.read()

OLD_KENTRADE = '''def generate_kentrade_csv(records: list) -> str:
    """Generate KenTrade-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Declaration_Reference", "Exporter_PIN", "Commodity_Description",
        "HS_Code", "Origin_County", "Net_Weight_KG", "FOB_Value_USD",
        "Farmer_Name", "Consignment_ID", "Submission_Date"
    ])
    for r in records:
        writer.writerow([
            r.get("Consignment_ID", r.get("session_id", "—")),
            r.get("KRA_PIN", r.get("kra_pin", "—")),
            r.get("Crop_Type", r.get("crop", "—")),
            r.get("HS_Code", r.get("hs_code", "0804.40")),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            r.get("FOB_Value_USD", r.get("fob_value_usd", 0)),
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Consignment_ID", r.get("session_id", "—")),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()'''

NEW_KENTRADE = '''def generate_kentrade_csv(records: list) -> str:
    """Generate KenTrade-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Declaration_Reference", "Exporter_PIN", "Commodity_Description",
        "HS_Code", "Origin_County", "Net_Weight_KG", "FOB_Value_USD",
        "Farmer_Name", "Consignment_ID", "Consignee_Name", "Consignee_Address",
        "Point_of_Exit", "Package_Type", "Number_of_Packages", "Submission_Date"
    ])
    for r in records:
        writer.writerow([
            r.get("Consignment_ID", r.get("session_id", "—")),
            r.get("KRA_PIN", r.get("kra_pin", "—")),
            r.get("Crop_Type", r.get("crop", "—")),
            r.get("HS_Code", r.get("hs_code") or "MISSING_HS_CODE"),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            r.get("FOB_Value_USD", r.get("fob_value_usd", 0)),
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Consignment_ID", r.get("session_id", "—")),
            r.get("consignee_name", "—"),
            r.get("consignee_address", "—"),
            r.get("point_of_exit", "—"),
            r.get("package_type", "—"),
            r.get("number_of_packages", 0),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()'''

OLD_KEPHIS = '''def generate_kephis_csv(records: list) -> str:
    """Generate KEPHIS-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Application_Reference", "Exporter_Name", "Commodity",
        "HS_Code", "Origin", "Quantity_KG", "Destination",
        "Consignment_ID", "Application_Date"
    ])
    for r in records:
        writer.writerow([
            f"KP-{r.get('Consignment_ID', r.get('session_id','VP'))[-6:]}",
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Crop_Type",   r.get("crop", "—")),
            r.get("HS_Code",     r.get("hs_code", "0804.40")),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            "EU",
            r.get("Consignment_ID", r.get("session_id", "—")),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()'''

NEW_KEPHIS = '''def generate_kephis_csv(records: list) -> str:
    """Generate KEPHIS-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Application_Reference", "Exporter_Name", "Commodity",
        "HS_Code", "Origin", "Quantity_KG", "Destination",
        "Consignment_ID", "Consignee_Name", "Consignee_Address",
        "Point_of_Exit", "Package_Type", "Number_of_Packages", "Application_Date"
    ])
    for r in records:
        writer.writerow([
            f"KP-{r.get('Consignment_ID', r.get('session_id','VP'))[-6:]}",
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Crop_Type",   r.get("crop", "—")),
            r.get("HS_Code",     r.get("hs_code") or "MISSING_HS_CODE"),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            "EU",
            r.get("Consignment_ID", r.get("session_id", "—")),
            r.get("consignee_name", "—"),
            r.get("consignee_address", "—"),
            r.get("point_of_exit", "—"),
            r.get("package_type", "—"),
            r.get("number_of_packages", 0),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()'''

assert OLD_KENTRADE in src, "generate_kentrade_csv anchor not found"
assert OLD_KEPHIS in src, "generate_kephis_csv anchor not found"

src = src.replace(OLD_KENTRADE, NEW_KENTRADE)
src = src.replace(OLD_KEPHIS, NEW_KEPHIS)

with open("bridge_engine.py", "w") as f:
    f.write(src)

print("✅ bridge_engine.py patched.")
