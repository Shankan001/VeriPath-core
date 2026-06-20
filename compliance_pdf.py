import streamlit as st
from datetime import datetime
from io import BytesIO
from ledger_db import load_ledger

def build_pdf_bytes(entry, exporter_name, exporter_pin):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.units import mm
    except ImportError:
        return None, "reportlab not installed"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        topMargin=20*mm, bottomMargin=20*mm,
        leftMargin=20*mm, rightMargin=20*mm)

    GREEN       = colors.HexColor("#1a6b3c")
    LIGHT_GREEN = colors.HexColor("#e8f5e9")
    AMBER       = colors.HexColor("#f9a825")
    RED_C       = colors.HexColor("#c62828")
    RISK_COLOR  = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED_C}
    risk        = entry.get("eudr_risk","GREEN")

    title_s   = ParagraphStyle("t",  fontSize=18, textColor=GREEN,
                                spaceAfter=4,  fontName="Helvetica-Bold")
    sub_s     = ParagraphStyle("s",  fontSize=10, textColor=colors.grey, spaceAfter=12)
    section_s = ParagraphStyle("sec",fontSize=11, textColor=GREEN,
                                spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold")
    body_s    = ParagraphStyle("b",  fontSize=9.5, spaceAfter=4, leading=14)
    footer_s  = ParagraphStyle("f",  fontSize=7.5, textColor=colors.grey, alignment=1)

    story = []
    story.append(Paragraph("VeriPath Africa", title_s))
    story.append(Paragraph("Clean Bill of Compliance", sub_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN, spaceAfter=12))

    meta = [
        ["Document Ref:", entry.get("batch_ref","—"),
         "Issue Date:", datetime.now().strftime("%d %b %Y")],
        ["Farmer ID:", entry.get("farmer_id","—"),
         "Session:", entry.get("session_id","—")],
        ["Exporter:", exporter_name, "KRA PIN:", exporter_pin],
        ["Packhouse:", entry.get("packhouse","—"),
         "Timestamp:", str(entry.get("timestamp","—"))[:19]],
    ]
    t = Table(meta, colWidths=[38*mm,62*mm,38*mm,52*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("TEXTCOLOR",(0,0),(0,-1),GREEN),
        ("TEXTCOLOR",(2,0),(2,-1),GREEN),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,LIGHT_GREEN]),
        ("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t)
    story.append(Spacer(1,10))

    story.append(Paragraph("Outgrower Details", section_s))
    farmer_data = [
        ["Full Name",   entry.get("farmer_name","—"),
         "Phone",       entry.get("farmer_phone","—")],
        ["County",      entry.get("county","—"),
         "Sub-location",entry.get("sub_location","—")],
        ["Farm Size",   f"{entry.get('farm_size_ha','—')} ha",
         "GPS",         entry.get("gps","—")],
    ]
    ft = Table(farmer_data, colWidths=[38*mm,62*mm,38*mm,52*mm])
    ft.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f9f9f9")]),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(ft)
    story.append(Spacer(1,8))

    story.append(Paragraph("Consignment Details", section_s))
    consignment_data = [
        ["Crop / Product", entry.get("crop","—")],
        ["HS Code",        entry.get("hs_code","—")],
        ["Weight (kg)",    str(entry.get("weight_kg","—"))],
        ["Grade",          entry.get("grade","—")],
        ["Notes",          entry.get("notes","—") or "—"],
    ]
    ct = Table(consignment_data, colWidths=[60*mm,130*mm])
    ct.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.3,colors.lightgrey),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f9f9f9")]),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(ct)
    story.append(Spacer(1,10))

    story.append(Paragraph("EUDR Compliance Status", section_s))
    risk_color  = RISK_COLOR.get(risk, GREEN)
    risk_table  = Table([[f"EUDR Risk Rating:  {risk}"]], colWidths=[190*mm])
    risk_table.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),13),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,0),(-1,-1),risk_color),
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f0faf4")),
        ("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),12),
        ("BOX",(0,0),(-1,-1),1.5,risk_color),
    ]))
    story.append(risk_table)
    story.append(Spacer(1,10))

    story.append(Paragraph("Declaration", section_s))
    story.append(Paragraph(
        f"I, <b>{exporter_name}</b> (KRA PIN: <b>{exporter_pin}</b>), hereby declare that "
        f"the above consignment has been sourced from registered outgrower "
        f"<b>{entry.get('farmer_name','—')}</b> (VeriPath ID: <b>{entry.get('farmer_id','—')}</b>), "
        f"that all data is true and accurate, and that this consignment is compliant with "
        f"phytosanitary, KEPHIS, KenTrade, and EUDR requirements as of the date of issue.",
        body_s
    ))
    story.append(Spacer(1,16))
    story.append(HRFlowable(width="60%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "Authorized Signature &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Date", body_s))
    story.append(Spacer(1,20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Paragraph(
        f"Generated by VeriPath Africa · {datetime.now().strftime('%d %b %Y %H:%M')} · "
        f"System-generated — requires authorized signature to be valid.",
        footer_s
    ))
    doc.build(story)
    buf.seek(0)
    return buf, None

def render_compliance_pdf_page(profile: dict = None):
    company = profile.get("company","") if profile else ""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#4a148c 0%,#1a6b3c 100%);
                color:white;padding:20px 24px;border-radius:12px;margin-bottom:24px'>
        <h2 style='margin:0;font-size:1.4rem'>📄 Compliance PDF Generator</h2>
        <p style='margin:6px 0 0;opacity:0.85;font-size:0.9rem'>
            Clean Bill of Compliance per consignment — ready for KenTrade & KEPHIS</p>
    </div>
    """, unsafe_allow_html=True)

    ledger = load_ledger(company)
    if not ledger:
        st.warning("No ledger entries found for your company.")
        return

    col1, col2 = st.columns(2)
    with col1:
        exporter_name = st.text_input("Exporter / Company Name *",
                                       value=company,
                                       placeholder="e.g. Kakuzi PLC")
    with col2:
        exporter_pin  = st.text_input("KRA PIN *", placeholder="e.g. P051234567A")

    options = {
        f"{e['batch_ref']} | {e['farmer_name']} | {e['crop']} | "
        f"{e['weight_kg']}kg | {str(e['timestamp'])[:10]}": i
        for i, e in enumerate(ledger)
    }
    selected_label = st.selectbox("Choose ledger entry",
                                   ["— Select —"] + list(options.keys()))

    if selected_label != "— Select —" and exporter_name and exporter_pin:
        entry = ledger[options[selected_label]]
        col1, col2, col3 = st.columns(3)
        col1.metric("Farmer", entry.get("farmer_name","—"))
        col2.metric("Crop",   entry.get("crop","—"))
        col3.metric("Weight", f"{entry.get('weight_kg','—')} kg")

        if st.button("🖨 Generate PDF", use_container_width=True, type="primary"):
            pdf_buf, err = build_pdf_bytes(entry, exporter_name, exporter_pin)
            if err:
                st.error(f"PDF error: {err}. Run: pip install reportlab")
            else:
                fname = (f"VeriPath_Compliance_{entry.get('batch_ref','doc')}_"
                         f"{entry.get('farmer_id','')}.pdf")
                st.download_button(
                    "⬇ Download Clean Bill of Compliance (PDF)",
                    data=pdf_buf, file_name=fname,
                    mime="application/pdf", use_container_width=True
                )
                st.success("PDF ready.")
    elif selected_label != "— Select —":
        st.info("Fill in exporter name and KRA PIN to generate.")
