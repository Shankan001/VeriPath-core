with open("compliance_pdf.py", "r") as f:
    content = f.read()

old = '''    story.append(risk_table)
    story.append(Spacer(1,10))
    story.append(Paragraph("Declaration", section_s))'''

new = '''    story.append(risk_table)
    story.append(Spacer(1,10))

    # ── Satellite Deforestation Assessment (FAO Whisp) ──────────────────
    farmer_id_for_pdf = entry.get("farmer_id", "")
    whisp_data = None
    if farmer_id_for_pdf:
        try:
            from supabase_db import get_client as _pdf_gc
            _rows = _pdf_gc().table("farm_boundaries").select(
                "deforestation_risk_perennial, deforestation_risk_annual, "
                "deforestation_risk_timber, deforestation_tree_loss_after_2020_ha, deforestation_checked_at"
            ).eq("farmer_id", farmer_id_for_pdf).execute().data
            if _rows and _rows[0].get("deforestation_checked_at"):
                whisp_data = _rows[0]
        except Exception:
            whisp_data = None

    story.append(Paragraph("Satellite Deforestation Assessment (FAO Whisp)", section_s))
    if whisp_data:
        _risk_label = {"low": "LOW", "high": "HIGH", "unknown": "UNKNOWN"}
        whisp_rows = [
            ["Perennial Crop Risk:", _risk_label.get(whisp_data.get("deforestation_risk_perennial"), "—")],
            ["Annual Crop Risk:", _risk_label.get(whisp_data.get("deforestation_risk_annual"), "—")],
            ["Timber Risk:", _risk_label.get(whisp_data.get("deforestation_risk_timber"), "—")],
            ["Tree Cover Loss After Dec 31 2020:", f"{whisp_data.get('deforestation_tree_loss_after_2020_ha', 0):.3f} ha"],
            ["Assessment Date:", str(whisp_data.get("deforestation_checked_at",""))[:10]],
        ]
        whisp_table = Table(whisp_rows, colWidths=[80*mm, 110*mm])
        whisp_table.setStyle(TableStyle([
            ("FONTSIZE",(0,0),(-1,-1),9),
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
            ("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ]))
        story.append(whisp_table)
        story.append(Paragraph(
            "This satellite assessment (source: FAO Open Foris Whisp) indicates the detected "
            "presence or absence of tree cover loss on the registered farm polygon since the "
            "EUDR reference date. This is one component of due diligence and does not by itself "
            "constitute full EUDR compliance, which also requires verification of legal land "
            "tenure, labor practices, and tax compliance.",
            body_s
        ))
    else:
        story.append(Paragraph(
            "No satellite deforestation assessment has been run for this farm. "
            "Run a check via Farm Boundary Registration before relying on this "
            "document for EUDR submission.",
            body_s
        ))
    story.append(Spacer(1,10))

    story.append(Paragraph("Declaration", section_s))'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("compliance_pdf.py", "w") as f:
        f.write(content)
    print("Added Whisp deforestation section to Compliance PDF.")
