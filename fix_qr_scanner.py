with open("packhouse.py","r") as f:
    content = f.read()

old = '''    if scan_method == "📷 Camera Scan":
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
                                    placeholder="VP-XXXXXXXX", key="camera_id").strip().upper()'''

new = '''    if scan_method == "📷 Camera Scan":
        st.markdown("""
        <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:12px;
                    padding:16px;text-align:center;margin-bottom:12px'>
            <div style='color:#38bdf8;font-family:Space Mono,monospace;font-size:0.85rem;
                        margin-bottom:8px'>📱 MOBILE QR SCAN</div>
            <div style='color:#94a3b8;font-size:0.82rem;margin-bottom:12px'>
                Tap the button below to open your camera and scan the farmer QR card.
                The farmer ID will appear in the field below automatically.
            </div>
        </div>
        """, unsafe_allow_html=True)
        components.html("""
        <div style="text-align:center;padding:10px">
            <input type="file" id="qr-input" accept="image/*" capture="environment"
                style="display:none" onchange="decodeQR(this)"/>
            <button onclick="document.getElementById('qr-input').click()"
                style="background:linear-gradient(135deg,#0369a1,#0284c7);
                       color:white;border:none;border-radius:10px;
                       padding:14px 28px;font-size:1rem;cursor:pointer;
                       width:100%;max-width:320px;font-weight:700;
                       letter-spacing:0.05em">
                📷 Open Camera to Scan QR
            </button>
            <div id="result-box" style="margin-top:14px;padding:12px 16px;
                background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                font-family:monospace;font-size:0.95rem;color:#38bdf8;
                min-height:38px;word-break:break-all;">
                Tap button above to scan QR card
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
        <script>
        function decodeQR(input) {
            const file = input.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = new Image();
                img.onload = function() {
                    const canvas  = document.createElement('canvas');
                    canvas.width  = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height);
                    if (code) {
                        let text = code.data;
                        document.getElementById('result-box').innerText = '✅ Scanned: ' + text;
                        document.getElementById('result-box').style.borderColor = '#16a34a';
                        try {
                            let data = JSON.parse(text);
                            let fid = data.id || text;
                            window.parent.postMessage({
                                type:'streamlit:setComponentValue', value: fid
                            }, '*');
                        } catch(e) {
                            window.parent.postMessage({
                                type:'streamlit:setComponentValue', value: text
                            }, '*');
                        }
                    } else {
                        document.getElementById('result-box').innerText =
                            '❌ No QR found. Try again with better lighting.';
                        document.getElementById('result-box').style.borderColor = '#dc2626';
                    }
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
        </script>
        """, height=220)
        scanned_id = st.text_input("Farmer ID (paste here after scan)",
                                    placeholder="VP-XXXXXXXX", key="camera_id").strip().upper()'''

if old in content:
    content = content.replace(old, new)
    print("✅ QR scanner replaced with HTML5 camera input")
else:
    print("❌ Block not found")

with open("packhouse.py","w") as f:
    f.write(content)
