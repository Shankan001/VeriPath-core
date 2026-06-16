import streamlit as st
import json
import os
from datetime import datetime
from io import BytesIO

LEDGER_DB = "ledger.json"

def load_ledger():
    if os.path.exists(LEDGER_DB):
        with open(LEDGER_DB, "r") as f:
            return json.load(f)
    return []

def build_pdf_bytes(entry, exporter_name, exporter_pin):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.units import mm
    except ImportError:
        return None, "reportlab not installed"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm)

    styles = getSampleStyleSheet()
    GREEN = colors.HexColor("#1a6b3c")
    LIGHT_GREEN = colors.HexColor("#e8f5e9")
    AMBER = colors.HexColor("#f9a825")
    RED_C = colors.HexColor("#c62828")

    RISK_COLOR = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED_C}
    risk = entry.get("eudr_risk", "GREEN")

    title_style = ParagraphStyle("title", fontSize=18, textColor=GREEN, spaceAfter=4, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("subtitle", fontSize=10, textColor=colors.grey, spaceAfter=12)
    section_style = ParagraphStyle("section", fontSize=11, textColor=GREEN, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold")
    body_style = ParagraphStyle("body", fontSize=9.5, spaceAfter=4, leading=14)

    story = []

    # Header
    story.append(Paragraph("VeriPath Africa", title_style))
    story.append(Paragraph("Clean Bill of Compliance", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN, spaceAfter=12))

    # Meta table
    meta = [
        ["Document Ref:", entry.get("batch_ref", "—"), "Issue Date:", datetime.now().strftime("%d %b %Y")],
        ["Farmer ID:", entry.get("farmer_id", "—"), "Session:", entry.get("session_id", "—")],
        ["Exporter:", exporter_name, "KRA PIN:", exporter_pin],
        ["Packhouse:", entry.get("packhouse", "—"), "Timestamp:", entry.get("timestamp", "—")[:19]],
    ]
    t = Table(meta, colWidths=[38*mm, 62*mm, 38*mm, 52*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("TEXTCOLOR", (0,0), (0,-1), GREEN),
        ("TEXTCOLOR", (2,0), (2,-1), GREEN),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GREEN),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GREEN]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Farmer section
    story.append(Paragraph("Outgrower Details", section_style))
    farmer_data = [
        ["Full Name", entry.get("farmer_name", "—"), "Phone", entry.get("farmer_phone", "—")],
        ["County", entry.get("county", "—"), "Sub-location", entry.get("sub_location", "—")],
        ["Farm Size", f"{entry.get('farm_size_ha','—')} ha", "GPS", entry.get("gps", "—")],
    ]
    ft = Table(farmer_data, colWidths=[38*mm, 62*mm, 38*mm, 52*mm])
    ft.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#333")),
        ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#333")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(ft)
    story.append(Spacer(1, 8))

    # Consignment section
    story.append(Paragraph("Consignment Details", section_style))
    consignment_data = [
        ["Crop / Product", entry.get("crop", "—")],
        ["HS Code", entry.get("hs_code", "—")],
        ["Weight (kg)", str(entry.get("weight_kg", "—"))],
        ["Grade", entry.get("grade", "—")],
        ["Notes", entry.get("notes", "—") or "—"],
    ]
    ct = Table(consignment_data, colWidths=[60*mm, 130*mm])
    ct.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(ct)
    story.append(Spacer(1, 10))

    # EUDR Risk block
    story.append(Paragraph("EUDR Compliance Status", section_style))
    risk_color = RISK_COLOR.get(risk, GREEN)
    risk_table = Table(
        [[f"EUDR Risk Rating:  {risk}"]],
        colWidths=[190*mm]
    )
    risk_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 13),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,0), (-1,-1), risk_color),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0faf4")),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("BOX", (0,0), (-1,-1), 1.5, risk_color),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 10))

    # Declaration
    story.append(Paragraph("Declaration", section_style))
    story.append(Paragraph(
        f"I, <b>{exporter_name}</b> (KRA PIN: <b>{exporter_pin}</b>), hereby declare that the above consignment "
        f"has been sourced from registered outgrower <b>{entry.get('farmer_name','—')}</b> (VeriPath ID: "
        f"<b>{entry.get('farmer_id','—')}</b>), that all data entered into this system is true and accurate "
        f"to the best of my knowledge, and that this consignment is compliant with applicable phytosanitary, "
        f"KEPHIS, KenTrade, and EUDR requirements as of the date of issue.",
        body_style
    ))
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="60%", thickness=0.5, color=colors.grey))
    story.append(Paragraph("Authorized Signature &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Date", body_style))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Paragraph(
        f"Generated by VeriPath Africa · {datetime.now().strftime('%d %b %Y %H:%M')} · This document is system-generated and requires authorized signature to be valid.",
        ParagraphStyle("footer", fontSize=7.5, textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    buf.seek(0)
    return buf, None

def render_compliance_pdf_page():
    st.markdown("""
    <style>
    .pdf-header {
        background: linear-gradient(135deg, #4a148c 0%, #1a6b3c 100%);
        color: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 24px;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="pdf-header">
        <h2 style="margin:0;font-size:1.4rem;">📄 Compliance PDF Generator</h2>
        <p style="margin:6px 0 0;opacity:0.85;font-size:0.9rem;">Generate a Clean Bill of Compliance per consignment — ready for KenTrade & KEPHIS</p>
    </div>
    """, unsafe_allow_html=True)

    ledger = load_ledger()
    if not ledger:
        st.warning("No ledger entries found. Complete packhouse intake first.")
        return

    st.markdown("### Exporter Details")
    col1, col2 = st.columns(2)
    with col1:
        exporter_name = st.text_input("Exporter / Company Name *", placeholder="e.g. Kakuzi PLC")
    with col2:
        exporter_pin = st.text_input("KRA PIN *", placeholder="e.g. P051234567A")

    st.markdown("### Select Consignment")
    options = {f"{e['batch_ref']} | {e['farmer_name']} | {e['crop']} | {e['weight_kg']}kg | {e['timestamp'][:10]}": i
               for i, e in enumerate(ledger)}
    selected_label = st.selectbox("Choose ledger entry", ["— Select —"] + list(options.keys()))

    if selected_label != "— Select —" and exporter_name and exporter_pin:
        entry = ledger[options[selected_label]]
        st.markdown("---")
        st.markdown("**Preview:**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Farmer", entry.get("farmer_name","—"))
        col2.metric("Crop", entry.get("crop","—"))
        col3.metric("Weight", f"{entry.get('weight_kg','—')} kg")

        if st.button("🖨️ Generate PDF", use_container_width=True, type="primary"):
            pdf_buf, err = build_pdf_bytes(entry, exporter_name, exporter_pin)
            if err:
                st.error(f"PDF generation failed: {err}. Run: pip install reportlab")
            else:
                fname = f"VeriPath_Compliance_{entry.get('batch_ref','doc')}_{entry.get('farmer_id','')}.pdf"
                st.download_button(
                    "⬇️ Download Clean Bill of Compliance (PDF)",
                    data=pdf_buf,
                    file_name=fname,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF ready. Download above.")
    elif selected_label != "— Select —":
        st.info("Fill in exporter name and KRA PIN to generate PDF.")
