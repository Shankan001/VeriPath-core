import streamlit as st
import streamlit.components.v1 as components
import json
import os
import datetime as dt
from ledger_db import load_ledger, save_full_ledger, load_farmers, save_farmers, clear_company_ledger

CROP_HS_CODES = {
    "Avocado": "0804.40", "French Beans": "0708.20", "Roses": "0603.11",
    "Carnations": "0603.12", "Mango": "0804.50", "Passion Fruit": "0810.90",
    "Macadamia Nuts": "0802.62", "Tea": "0902.30", "Coffee": "0901.11",
    "Spinach": "0709.70", "Kale": "0704.99", "Capsicum": "0709.60",
    "Tomato": "0702.00", "Snow Peas": "0710.21", "Pineapple": "0804.30",
    "Maize": "1005.90",
}

EUDR_RISK = {
    "Coffee": "AMBER", "Tea": "AMBER", "Maize": "AMBER",
    "Avocado": "GREEN", "Mango": "GREEN", "Macadamia Nuts": "GREEN",
    "French Beans": "GREEN", "Snow Peas": "GREEN", "Roses": "GREEN",
    "Carnations": "GREEN", "Passion Fruit": "GREEN", "Spinach": "GREEN",
    "Kale": "GREEN", "Capsicum": "GREEN", "Tomato": "GREEN",
    "Pineapple": "GREEN",
}

def render_packhouse_page(profile: dict = None):
    company = profile.get("company","") if profile else ""
    role    = profile.get("role","record_keeper") if profile else "record_keeper"

    tab1, tab2 = st.tabs(["📦 New Intake Session", "📝 My Records (Edit)"])

    with tab1:
        _render_intake(company, role)

    with tab2:
        _render_record_keeper_edit(company)

def _render_intake(company: str, role: str):
    st.markdown("# 📦 Packhouse Intake")
    st.markdown("<p style='color:#64748b'>Scan farmer QR → select crop → enter weight → save</p>",
                unsafe_allow_html=True)

    farmers = load_farmers(company)

    st.markdown("### Step 1 — Scan or Enter Farmer ID")
    scan_method = st.radio("Input method",
                           ["📷 Camera Scan", "⌨ Type / Bluetooth Scanner"],
                           horizontal=True, key="ph_scan_method")

    scanned_id = ""
    if scan_method == "📷 Camera Scan":
        components.html("""
        <div id="scanner-container" style="width:100%;max-width:400px;margin:0 auto;">
            <video id="preview" style="width:100%;border-radius:12px;border:2px solid #1e3a5f;"></video>
            <div id="result-box" style="margin-top:12px;padding:12px 16px;
                background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                font-family:monospace;font-size:1rem;color:#38bdf8;min-height:40px;">
                Waiting for QR scan...</div>
            <button onclick="startCamera()" style="margin-top:10px;padding:10px 20px;
                background:linear-gradient(135deg,#0369a1,#0284c7);color:white;
                border:none;border-radius:8px;font-size:0.9rem;cursor:pointer;width:100%;">
                ▶ Start Camera</button>
            <button onclick="stopCamera()" style="margin-top:6px;padding:8px 20px;
                background:#1e3a5f;color:#94a3b8;border:none;border-radius:8px;
                font-size:0.85rem;cursor:pointer;width:100%;">■ Stop Camera</button>
        </div>
        <script src="https://unpkg.com/@zxing/library@latest/umd/index.min.js"></script>
        <script>
        let codeReader = null;
        function startCamera() {
            codeReader = new ZXing.BrowserQRCodeReader();
            codeReader.decodeFromVideoDevice(null, 'preview', (result, err) => {
                if (result) {
                    let text = result.getText();
                    document.getElementById('result-box').innerText = '✅ Scanned: ' + text;
                    try {
                        let data = JSON.parse(text);
                        let fid = data.id || text;
                        window.parent.postMessage({type:'streamlit:setComponentValue',value:fid},'*');
                    } catch(e) {
                        window.parent.postMessage({type:'streamlit:setComponentValue',value:text},'*');
                    }
                }
            });
        }
        function stopCamera() {
            if (codeReader) { codeReader.reset(); codeReader = null; }
            document.getElementById('result-box').innerText = 'Camera stopped.';
        }
        </script>
        """, height=420)
        scanned_id = st.text_input("Farmer ID from scan",
                                    placeholder="VP-XXXXXXXX", key="camera_id").strip().upper()
    else:
        scanned_id = st.text_input("Farmer ID",
                                    placeholder="VP-XXXXXXXX — bluetooth scanner auto-types here",
                                    key="manual_id").strip().upper()

    selected_id = None
    if scanned_id:
        if scanned_id in farmers:
            selected_id = scanned_id
        else:
            try:
                payload = json.loads(scanned_id)
                fid = payload.get("id","")
                if fid in farmers:
                    selected_id = fid
            except:
                pass
            if not selected_id:
                st.error(f"❌ Farmer ID `{scanned_id}` not found for {company}.")

    if not selected_id:
        if farmers:
            fallback = st.selectbox(
                "Or pick farmer by name",
                ["— Select —"] + [f"{v['name']} ({k})" for k, v in farmers.items()],
                key="fallback_select"
            )
            if fallback != "— Select —":
                selected_id = fallback.split("(")[-1].rstrip(")")
        else:
            st.warning("No farmers registered yet. Go to Outgrower Registry first.")
            return

    if not selected_id:
        return

    farmer = farmers[selected_id]
    st.markdown(f"""
    <div style='background:#071a0f;border:1.5px solid #16a34a;border-radius:12px;
                padding:16px 20px;margin:14px 0'>
        <div style='font-size:1.1rem;font-weight:700;color:#4ade80'>✅ {farmer["name"]}</div>
        <div style='color:#94a3b8;font-size:0.85rem;margin-top:4px'>
            ID: <code style='color:#38bdf8'>{selected_id}</code> &nbsp;|&nbsp;
            {farmer["county"]} &nbsp;|&nbsp; {farmer["farm_size_ha"]} ha
            &nbsp;|&nbsp; 📞 {farmer["phone"]}
        </div>
        <div style='color:#64748b;font-size:0.8rem;margin-top:4px'>
            GPS: {farmer.get("gps","—")} &nbsp;|&nbsp;
            Crops: {", ".join(farmer["crops"])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Step 2 — Session Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        packhouse_name = st.text_input("Packhouse Name *",
                                        placeholder="e.g. Kakuzi Thika", key="ph_name")
    with col2:
        batch_ref = st.text_input("Batch Ref (optional)",
                                   placeholder="e.g. BATCH-001", key="ph_batch")
    with col3:
        intake_date = st.date_input("Intake Date", value=dt.date.today(), key="ph_date")
    day_of_week = intake_date.strftime("%A")
    st.caption(f"📅 {day_of_week} — {intake_date.strftime('%d %b %Y')}")

    st.markdown("---")
    st.markdown("### Step 3 — Add Product Rows")
    st.caption("One row per crop. Multiple rows allowed per session.")

    if "intake_rows" not in st.session_state:
        st.session_state.intake_rows = []

    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        crop = st.selectbox("Crop *",
                             ["— Select —"] + list(CROP_HS_CODES.keys()), key="ph_crop")
    with col2:
        weight_kg = st.number_input("Weight (kg) *", min_value=0.1,
                                     max_value=99999.0, value=100.0,
                                     step=0.5, key="ph_weight")
    with col3:
        grade = st.selectbox("Grade",
                              ["Grade A","Grade B","Grade C","Mixed"], key="ph_grade")
    notes = st.text_input("Notes (optional)",
                           placeholder="e.g. Harvest Block 3", key="ph_notes")

    if crop != "— Select —":
        hs   = CROP_HS_CODES[crop]
        eudr = EUDR_RISK.get(crop,"GREEN")
        color = {"GREEN":"#4ade80","AMBER":"#fbbf24","RED":"#f87171"}.get(eudr)
        st.markdown(
            f"**HS:** `{hs}` &nbsp;|&nbsp; **EUDR:** "
            f"<span style='color:{color};font-weight:700'>{eudr}</span>",
            unsafe_allow_html=True)

    if st.button("➕ Add Product Row", use_container_width=True):
        if crop == "— Select —":
            st.error("Select a crop first.")
        else:
            st.session_state.intake_rows.append({
                "crop":      crop,
                "hs_code":   CROP_HS_CODES[crop],
                "weight_kg": weight_kg,
                "grade":     grade,
                "notes":     notes,
                "eudr_risk": EUDR_RISK.get(crop,"GREEN"),
            })
            st.rerun()

    if st.session_state.intake_rows:
        total_kg = sum(r["weight_kg"] for r in st.session_state.intake_rows)
        st.markdown(f"**{len(st.session_state.intake_rows)} row(s) — Total: {total_kg:,.1f} kg**")
        for i, row in enumerate(st.session_state.intake_rows):
            color = {"GREEN":"#4ade80","AMBER":"#fbbf24","RED":"#f87171"}.get(row["eudr_risk"],"#4ade80")
            c1, c2 = st.columns([6,1])
            with c1:
                st.markdown(f"""
                <div style='background:#111827;border:1px solid #1e3a5f;border-radius:8px;
                            padding:10px 14px;margin-bottom:6px;font-size:0.9rem'>
                    <b style='color:#e8eaf0'>{row["crop"]}</b>
                    &nbsp;·&nbsp; {row["weight_kg"]} kg &nbsp;·&nbsp; {row["grade"]}
                    &nbsp;·&nbsp; HS: <code>{row["hs_code"]}</code>
                    &nbsp;·&nbsp; EUDR: <span style='color:{color};font-weight:700'>{row["eudr_risk"]}</span>
                    {f'<br><span style="color:#64748b;font-size:0.8rem">{row["notes"]}</span>' if row["notes"] else ""}
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("🗑", key=f"del_{i}"):
                    st.session_state.intake_rows.pop(i)
                    st.rerun()

        st.markdown("---")
        if st.button("💾 Save Session to Ledger",
                     use_container_width=True, type="primary"):
            if not packhouse_name:
                st.error("Enter packhouse name before saving.")
            else:
                timestamp  = dt.datetime.now().isoformat()
                session_id = "SES-" + dt.datetime.now().strftime("%Y%m%d%H%M%S")
                all_records = []
                ledger_path = os.path.join("data","ledger.json")
                if os.path.exists(ledger_path):
                    with open(ledger_path) as f:
                        all_records = json.load(f)
                for row in st.session_state.intake_rows:
                    all_records.append({
                        "session_id":   session_id,
                        "batch_ref":    batch_ref or session_id,
                        "intake_date":  intake_date.isoformat(),
                        "day_of_week":  day_of_week,
                        "farmer_id":    selected_id,
                        "farmer_name":  farmer["name"],
                        "farmer_phone": farmer["phone"],
                        "county":       farmer["county"],
                        "sub_location": farmer.get("sub_location",""),
                        "gps":          farmer.get("gps",""),
                        "farm_size_ha": farmer["farm_size_ha"],
                        "crop":         row["crop"],
                        "hs_code":      row["hs_code"],
                        "weight_kg":    row["weight_kg"],
                        "grade":        row["grade"],
                        "eudr_risk":    row["eudr_risk"],
                        "notes":        row["notes"],
                        "packhouse":    packhouse_name,
                        "timestamp":    timestamp,
                        "status":       "pending_audit",
                        "audit_status": "unreviewed",
                        "company":      company,
                    })
                save_full_ledger(all_records)
                st.success(f"✅ {len(st.session_state.intake_rows)} rows saved — **{session_id}**")
                st.balloons()
                st.session_state.intake_rows = []
                st.rerun()
    else:
        st.info("No rows yet. Select a crop and click ➕ Add Product Row.")

def _render_record_keeper_edit(company: str):
    st.markdown("### 📝 Today's Records")
    st.markdown("<p style='color:#64748b'>View and fix typos in your intake entries</p>",
                unsafe_allow_html=True)

    import pandas as pd
    ledger = load_ledger(company)
    if not ledger:
        st.info("No records yet for your company.")
        return

    df = pd.DataFrame(ledger)
    if "intake_date" not in df.columns:
        st.info("No dated records found.")
        return

    today = dt.date.today().isoformat()
    available_dates = sorted(df["intake_date"].unique(), reverse=True)
    selected_date = st.selectbox(
        "Select Date",
        available_dates,
        format_func=lambda d: f"{'📅 TODAY — ' if d==today else ''}{d}"
    )

    day_records = [r for r in ledger if r.get("intake_date") == selected_date]
    if not day_records:
        st.info("No records for this date.")
        return

    st.markdown(f"**{len(day_records)} records — {selected_date}**")
    st.markdown("---")

    ledger_path = os.path.join("data","ledger.json")

    for idx, record in enumerate(day_records):
        with st.expander(
            f"{'🟡' if record.get('audit_status')=='unreviewed' else '✅'} "
            f"{record.get('farmer_name','—')} · {record.get('crop','—')} · "
            f"{record.get('weight_kg','—')} kg · {record.get('session_id','—')}"
        ):
            col1, col2, col3 = st.columns(3)
            new_weight = col1.number_input(
                "Weight (kg)", min_value=0.1, max_value=99999.0,
                value=float(record.get("weight_kg",100)),
                key=f"edit_weight_{idx}"
            )
            new_grade = col2.selectbox(
                "Grade",
                ["Grade A","Grade B","Grade C","Mixed"],
                index=["Grade A","Grade B","Grade C","Mixed"].index(
                    record.get("grade","Grade A")
                ) if record.get("grade") in ["Grade A","Grade B","Grade C","Mixed"] else 0,
                key=f"edit_grade_{idx}"
            )
            new_notes = col3.text_input(
                "Notes", value=record.get("notes",""),
                key=f"edit_notes_{idx}"
            )
            new_packhouse = st.text_input(
                "Packhouse", value=record.get("packhouse",""),
                key=f"edit_ph_{idx}"
            )

            if st.button("💾 Save Edit", key=f"save_edit_{idx}"):
                if os.path.exists(ledger_path):
                    with open(ledger_path) as f:
                        all_records = json.load(f)
                    company_lower = company.strip().lower()
                    session_id    = record.get("session_id")
                    row_crop      = record.get("crop")
                    for r in all_records:
                        if (r.get("session_id") == session_id
                                and r.get("crop") == row_crop
                                and r.get("company","").strip().lower() == company_lower):
                            r["weight_kg"]  = new_weight
                            r["grade"]      = new_grade
                            r["notes"]      = new_notes
                            r["packhouse"]  = new_packhouse
                            r["last_edited"] = dt.datetime.now().isoformat()
                            break
                    save_full_ledger(all_records)
                    st.success("✅ Record updated.")
                    st.rerun()
