import streamlit as st
import streamlit.components.v1 as components
import json
import os
import datetime as dt

FARMERS_DB = "farmers.json"
LEDGER_DB  = "ledger.json"

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
    "Kale": "GREEN", "Capsicum": "GREEN", "Tomato": "GREEN", "Pineapple": "GREEN",
}

def load_farmers():
    if os.path.exists(FARMERS_DB):
        with open(FARMERS_DB, "r") as f:
            return json.load(f)
    return {}

def load_ledger():
    if os.path.exists(LEDGER_DB):
        with open(LEDGER_DB, "r") as f:
            return json.load(f)
    return []

def save_ledger(ledger):
    with open(LEDGER_DB, "w") as f:
        json.dump(ledger, f, indent=2)

def render_packhouse_page():
    st.markdown("# 📦 Packhouse Intake")
    st.markdown("<p style='color:#64748b'>Scan farmer QR → select crop → enter weight → save to ledger</p>", unsafe_allow_html=True)

    farmers = load_farmers()

    # ── QR Scanner (camera + bluetooth) ───────────────────────────────────
    st.markdown("### Step 1 — Scan or Enter Farmer ID")

    scan_method = st.radio("Input method", ["📷 Camera Scan", "⌨️ Type / Bluetooth Scanner"], horizontal=True)

    scanned_id = ""

    if scan_method == "📷 Camera Scan":
        st.markdown("<p style='color:#64748b;font-size:0.85rem'>Point camera at farmer QR card. Works on phone and tablet.</p>", unsafe_allow_html=True)
        components.html("""
        <div id="scanner-container" style="width:100%;max-width:400px;margin:0 auto;">
            <video id="preview" style="width:100%;border-radius:12px;border:2px solid #1e3a5f;"></video>
            <div id="result-box" style="
                margin-top:12px;padding:12px 16px;
                background:#0d1224;border:1px solid #1e3a5f;
                border-radius:8px;font-family:monospace;
                font-size:1rem;color:#38bdf8;min-height:40px;
                word-break:break-all;
            ">Waiting for QR scan...</div>
            <button onclick="startCamera()" style="
                margin-top:10px;padding:10px 20px;
                background:linear-gradient(135deg,#0369a1,#0284c7);
                color:white;border:none;border-radius:8px;
                font-size:0.9rem;cursor:pointer;width:100%;
            ">▶ Start Camera</button>
            <button onclick="stopCamera()" style="
                margin-top:6px;padding:8px 20px;
                background:#1e3a5f;color:#94a3b8;
                border:none;border-radius:8px;
                font-size:0.85rem;cursor:pointer;width:100%;
            ">■ Stop Camera</button>
        </div>
        <input type="hidden" id="scanned-value" value="">

        <script src="https://unpkg.com/@zxing/library@latest/umd/index.min.js"></script>
        <script>
        let codeReader = null;
        let stream = null;

        function startCamera() {
            codeReader = new ZXing.BrowserQRCodeReader();
            codeReader.decodeFromVideoDevice(null, 'preview', (result, err) => {
                if (result) {
                    let text = result.getText();
                    document.getElementById('result-box').innerText = '✅ Scanned: ' + text;
                    document.getElementById('result-box').style.borderColor = '#16a34a';
                    document.getElementById('scanned-value').value = text;

                    // Send to Streamlit
                    try {
                        let data = JSON.parse(text);
                        let farmerId = data.id || text;
                        window.parent.postMessage({
                            type: 'streamlit:setComponentValue',
                            value: farmerId
                        }, '*');
                    } catch(e) {
                        window.parent.postMessage({
                            type: 'streamlit:setComponentValue',
                            value: text
                        }, '*');
                    }
                }
            });
        }

        function stopCamera() {
            if (codeReader) {
                codeReader.reset();
                codeReader = null;
            }
            document.getElementById('result-box').innerText = 'Camera stopped.';
            document.getElementById('result-box').style.borderColor = '#1e3a5f';
        }
        </script>
        """, height=420)

        st.caption("After scanning, paste the Farmer ID that appears in the box below:")
        scanned_id = st.text_input("Farmer ID from scan", placeholder="VP-XXXXXXXX", key="camera_id").strip().upper()

    else:
        st.caption("Type the Farmer ID or scan with bluetooth scanner (it types automatically):")
        scanned_id = st.text_input(
            "Farmer ID",
            placeholder="VP-XXXXXXXX — bluetooth scanner auto-types here",
            key="manual_id",
            help="Bluetooth barcode/QR scanners act as keyboards — just click this field and scan."
        ).strip().upper()

    # ── Farmer Lookup ──────────────────────────────────────────────────────
    selected_id = None

    if scanned_id:
        # Try direct match first
        if scanned_id in farmers:
            selected_id = scanned_id
        else:
            # Try parsing JSON payload from QR
            try:
                payload = json.loads(scanned_id)
                fid = payload.get("id", "")
                if fid in farmers:
                    selected_id = fid
            except Exception:
                pass

            if not selected_id:
                st.error(f"❌ No farmer found for ID: `{scanned_id}` — check QR card or register farmer first.")

    # Fallback dropdown if no scan
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

    # ── Farmer Identity Card ───────────────────────────────────────────────
    farmer = farmers[selected_id]
    risk_color = "#4ade80"

    st.markdown(f"""
    <div style='background:#071a0f;border:1.5px solid #16a34a;border-radius:12px;padding:16px 20px;margin:14px 0'>
        <div style='font-size:1.1rem;font-weight:700;color:#4ade80'>✅ {farmer["name"]}</div>
        <div style='color:#94a3b8;font-size:0.85rem;margin-top:4px'>
            ID: <code style='color:#38bdf8'>{selected_id}</code> &nbsp;|&nbsp;
            {farmer["county"]} &nbsp;|&nbsp;
            {farmer["farm_size_ha"]} ha &nbsp;|&nbsp;
            📞 {farmer["phone"]}
        </div>
        <div style='color:#64748b;font-size:0.8rem;margin-top:4px'>
            GPS: {farmer.get("gps","—")} &nbsp;|&nbsp;
            Registered crops: {", ".join(farmer["crops"])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Packhouse + Date ───────────────────────────────────────────────────
    st.markdown("### Step 2 — Session Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        packhouse_name = st.text_input("Packhouse Name *", placeholder="e.g. Kakuzi Thika", key="ph_name")
    with col2:
        batch_ref = st.text_input("Batch Ref (optional)", placeholder="e.g. BATCH-001", key="ph_batch")
    with col3:
        intake_date = st.date_input("Intake Date", value=dt.date.today(), key="ph_date")

    day_of_week = intake_date.strftime("%A")
    st.caption(f"📅 Day: **{day_of_week}** — {intake_date.strftime('%d %b %Y')}")

    st.markdown("---")

    # ── Product Rows ───────────────────────────────────────────────────────
    st.markdown("### Step 3 — Add Product Rows")
    st.caption("One row per crop type. Multiple rows allowed per session.")

    if "intake_rows" not in st.session_state:
        st.session_state.intake_rows = []

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        crop = st.selectbox("Crop / Product *", ["— Select —"] + list(CROP_HS_CODES.keys()), key="ph_crop")
    with col2:
        weight_kg = st.number_input("Weight (kg) *", min_value=0.1, max_value=99999.0, value=100.0, step=0.5, key="ph_weight")
    with col3:
        grade = st.selectbox("Grade", ["Grade A", "Grade B", "Grade C", "Mixed"], key="ph_grade")

    notes = st.text_input("Notes (optional)", placeholder="e.g. Harvest Block 3", key="ph_notes")

    if crop != "— Select —":
        hs   = CROP_HS_CODES[crop]
        eudr = EUDR_RISK.get(crop, "GREEN")
        color = {"GREEN": "#4ade80", "AMBER": "#fbbf24", "RED": "#f87171"}.get(eudr)
        st.markdown(
            f"**HS Code:** `{hs}` &nbsp;|&nbsp; **EUDR:** <span style='color:{color};font-weight:700'>{eudr}</span>",
            unsafe_allow_html=True
        )

    if st.button("➕ Add Product Row", use_container_width=True):
        if crop == "— Select —":
            st.error("Select a crop type first.")
        else:
            st.session_state.intake_rows.append({
                "crop":      crop,
                "hs_code":   CROP_HS_CODES[crop],
                "weight_kg": weight_kg,
                "grade":     grade,
                "notes":     notes,
                "eudr_risk": EUDR_RISK.get(crop, "GREEN"),
            })
            st.rerun()

    # ── Row Preview ────────────────────────────────────────────────────────
    if st.session_state.intake_rows:
        total_kg = sum(r["weight_kg"] for r in st.session_state.intake_rows)
        st.markdown(f"**{len(st.session_state.intake_rows)} row(s) — Total: {total_kg:,.1f} kg**")

        for i, row in enumerate(st.session_state.intake_rows):
            color = {"GREEN": "#4ade80", "AMBER": "#fbbf24", "RED": "#f87171"}.get(row["eudr_risk"], "#4ade80")
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f"""
                <div style='background:#111827;border:1px solid #1e3a5f;border-radius:8px;
                            padding:10px 14px;margin-bottom:6px;font-size:0.9rem'>
                    <b style='color:#e8eaf0'>{row["crop"]}</b>
                    &nbsp;·&nbsp; {row["weight_kg"]} kg
                    &nbsp;·&nbsp; {row["grade"]}
                    &nbsp;·&nbsp; HS: <code>{row["hs_code"]}</code>
                    &nbsp;·&nbsp; EUDR: <span style='color:{color};font-weight:700'>{row["eudr_risk"]}</span>
                    {f'<br><span style="color:#64748b;font-size:0.8rem">{row["notes"]}</span>' if row["notes"] else ""}
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.intake_rows.pop(i)
                    st.rerun()

        st.markdown("---")

        if st.button("💾 Save Session to Ledger", use_container_width=True, type="primary"):
            if not packhouse_name:
                st.error("Enter packhouse name before saving.")
            else:
                ledger     = load_ledger()
                timestamp  = dt.datetime.now().isoformat()
                session_id = "SES-" + dt.datetime.now().strftime("%Y%m%d%H%M%S")

                for row in st.session_state.intake_rows:
                    ledger.append({
                        "session_id":   session_id,
                        "batch_ref":    batch_ref or session_id,
                        "intake_date":  intake_date.isoformat(),
                        "day_of_week":  day_of_week,
                        "farmer_id":    selected_id,
                        "farmer_name":  farmer["name"],
                        "farmer_phone": farmer["phone"],
                        "county":       farmer["county"],
                        "sub_location": farmer.get("sub_location", ""),
                        "gps":          farmer.get("gps", ""),
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
                    })

                save_ledger(ledger)
                st.success(f"✅ {len(st.session_state.intake_rows)} rows saved — Session: **{session_id}**")
                st.balloons()
                st.session_state.intake_rows = []
                st.rerun()
    else:
        st.info("No rows yet. Select a crop and click ➕ Add Product Row.")
