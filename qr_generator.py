import streamlit as st
import streamlit.components.v1 as components
import qrcode
import json
import uuid
import math
from datetime import datetime
from io import BytesIO
from PIL import Image
from ledger_db import load_farmers, save_farmers
from invite_codes import generate_invite_code

KENYA_COUNTIES = [
    "Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa",
    "Homa Bay","Isiolo","Kajiado","Kakamega","Kericho","Kiambu","Kilifi",
    "Kirinyaga","Kisii","Kisumu","Kitui","Kwale","Laikipia","Lamu","Machakos",
    "Makueni","Mandera","Marsabit","Meru","Migori","Mombasa","Murang'a",
    "Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri",
    "Samburu","Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia",
    "Turkana","Uasin Gishu","Vihiga","Wajir","West Pokot"
]

CROP_HS_CODES = {
    "Avocado": "080440", "French Beans": "070820", "Roses": "060311",
    "Carnations": "060312", "Mango": "080450", "Passion Fruit": "081090",
    "Macadamia Nuts": "080251", "Tea": "090210", "Coffee": "090111",
    "Spinach": "070970", "Kale": "070499", "Capsicum": "070960",
    "Tomato": "070200", "Snow Peas": "071021", "Pineapple": "080430",
    "Maize": "100590",
}

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def extract_exif_gps(image_file):
    try:
        img  = Image.open(image_file)
        exif = img._getexif()
        if not exif:
            return None
        from PIL.ExifTags import TAGS, GPSTAGS
        gps_info = {}
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id, gps_val in value.items():
                    gps_info[GPSTAGS.get(gps_tag_id, gps_tag_id)] = gps_val
        if not gps_info:
            return None
        def to_decimal(dms, ref):
            d, m, s = dms
            dec = float(d) + float(m)/60 + float(s)/3600
            return -dec if ref in ("S","W") else dec
        lat = to_decimal(gps_info["GPSLatitude"],  gps_info["GPSLatitudeRef"])
        lon = to_decimal(gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"])
        return lat, lon
    except Exception:
        return None

def generate_qr(farmer_id, farmer_data):
    payload = json.dumps({
        "id":         farmer_id,
        "name":       farmer_data["name"],
        "phone":      farmer_data["phone"],
        "county":     farmer_data["county"],
        "crops":      farmer_data["crops"],
        "gps":        farmer_data.get("gps",""),
        "company":    farmer_data.get("company",""),
        "registered": farmer_data["registered_at"],
    })
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8, border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a6b3c", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def render_qr_page(profile: dict = None):
    company = profile.get("company","") if profile else ""
    role    = profile.get("role","") if profile else ""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#1a6b3c 0%,#2d9e5f 100%);
                color:white;padding:20px 24px;border-radius:12px;margin-bottom:24px'>
        <h2 style='margin:0;font-size:1.4rem'>&#127807; Outgrower Registry</h2>
        <p style='margin:6px 0 0;opacity:0.85;font-size:0.9rem'>
            Register farmers &middot; Auto GPS &middot; Photo verification &middot; QR cards
        </p>
    </div>
    """, unsafe_allow_html=True)

    farmers = load_farmers(company)
    tab1, tab2 = st.tabs(["&#10133; Register Farmer", "&#128203; View All Farmers"])

    with tab1:
        st.markdown("### New Outgrower Registration")

        col1, col2 = st.columns(2)
        with col1:
            name         = st.text_input("Full Name *", placeholder="Jane Wanjiku")
            phone        = st.text_input("Phone Number *", placeholder="+254712345678")
            id_number    = st.text_input("National ID Number", placeholder="12345678")
        with col2:
            county       = st.selectbox("County *", ["— Select —"] + KENYA_COUNTIES)
            sub_location = st.text_input("Sub-location / Village", placeholder="e.g. Ol Kalou")
            farm_size_ha = st.number_input("Farm Size (hectares)",
                                            min_value=0.1, max_value=500.0,
                                            value=1.0, step=0.1)

        crops = st.multiselect("Crops Grown *", options=list(CROP_HS_CODES.keys()),
                               help="Select all crops this farmer grows")

        # ── Auto GPS via postMessage bridge ───────────────────────────────
        st.markdown("#### GPS Farm Location *")
        st.caption("Tap the button — GPS is captured automatically. No typing needed.")

        geo_html = """
        <div id="geo_wrap" style="font-family:monospace">
          <button id="geo_btn" onclick="captureGeo()"
            style="background:#1a6b3c;color:white;border:none;padding:11px 26px;
                   border-radius:8px;font-size:0.95rem;cursor:pointer;font-weight:700">
            &#128205; Use My Location
          </button>
          <div id="geo_status"
               style="margin-top:9px;color:#94a3b8;font-size:0.83rem;min-height:18px"></div>
          <div id="geo_result_box"
               style="display:none;margin-top:8px;background:#071a0f;border:1px solid #16a34a;
                      border-radius:7px;padding:9px 13px;font-size:0.85rem;color:#4ade80"></div>
        </div>

        <script>
        function captureGeo() {
          var btn   = document.getElementById('geo_btn');
          var stat  = document.getElementById('geo_status');
          var box   = document.getElementById('geo_result_box');
          btn.disabled    = true;
          btn.innerText   = 'Detecting...';
          stat.innerText  = '';
          stat.style.color = '#94a3b8';
          if (!navigator.geolocation) {
            stat.innerText = 'Geolocation not supported by this browser.';
            btn.disabled = false; btn.innerText = 'Use My Location'; return;
          }
          navigator.geolocation.getCurrentPosition(
            function(pos) {
              var lat = pos.coords.latitude.toFixed(6);
              var lon = pos.coords.longitude.toFixed(6);
              var acc = Math.round(pos.coords.accuracy);
              btn.innerText   = 'Location Captured';
              stat.style.color = '#4ade80';
              stat.innerText  = 'GPS ready (+-' + acc + 'm accuracy)';
              box.style.display = 'block';
              box.innerText = lat + ', ' + lon;
              window.parent.postMessage({type:'vp_geo', lat:lat, lon:lon, acc:acc}, '*');
              btn.disabled = false;
            },
            function(err) {
              var msgs = {1:'Permission denied.',2:'Position unavailable.',3:'Timed out.'};
              btn.innerText   = 'Try Again';
              stat.style.color = '#f87171';
              stat.innerText = msgs[err.code] || err.message;
              btn.disabled = false;
            },
            {enableHighAccuracy:true, timeout:20000, maximumAge:0}
          );
        }
        </script>
        """
        components.html(geo_html, height=130, scrolling=False)

        # Parent-frame listener — injected once, writes into hidden input
        if "_geo_listener_injected" not in st.session_state:
            st.session_state["_geo_listener_injected"] = True
            st.markdown("""
            <script>
            (function(){
              if (window.__vp_geo_ready) return;
              window.__vp_geo_ready = true;
              window.addEventListener('message', function(e){
                if (!e.data || e.data.type !== 'vp_geo') return;
                var val = e.data.lat + ',' + e.data.lon;
                var inputs = window.parent.document.querySelectorAll('input[type=text]');
                for (var i=0; i<inputs.length; i++){
                  if (inputs[i].getAttribute('aria-label') === 'gps_auto_field'){
                    var setter = Object.getOwnPropertyDescriptor(
                      window.HTMLInputElement.prototype,'value').set;
                    setter.call(inputs[i], val);
                    inputs[i].dispatchEvent(new Event('input',{bubbles:true}));
                    break;
                  }
                }
              });
            })();
            </script>
            """, unsafe_allow_html=True)

        gps_auto = st.text_input(
            "gps_auto_field",
            value=st.session_state.get("gps_captured",""),
            key="gps_hidden",
            label_visibility="collapsed",
        )
        if gps_auto and gps_auto != st.session_state.get("gps_captured",""):
            st.session_state["gps_captured"] = gps_auto
            st.rerun()

        raw_gps = st.session_state.get("gps_captured","").strip()
        if raw_gps:
            st.markdown(f"""
            <div style='background:#071a0f;border:1px solid #16a34a;border-radius:7px;
                        padding:9px 14px;font-family:monospace;font-size:0.85rem;color:#4ade80'>
                GPS ready: <b>{raw_gps}</b>
            </div>""", unsafe_allow_html=True)

        with st.expander("Enter GPS manually instead"):
            gps_manual = st.text_input("Manual GPS (lat, lon)",
                                        placeholder="-0.3031, 36.8000",
                                        key="gps_manual")
            if gps_manual.strip():
                st.session_state["gps_captured"] = gps_manual.strip()
                raw_gps = gps_manual.strip()

        captured_gps = None
        if raw_gps:
            try:
                parts = raw_gps.split(",")
                captured_gps = (float(parts[0].strip()), float(parts[1].strip()))
            except Exception:
                st.warning("GPS value not parseable. Use format: -0.3031, 36.8000")

        # ── Photo upload + EXIF check ─────────────────────────────────────
        st.markdown("#### Farm / Farmer Photo *")
        st.caption("Required. On-site JPEG photos carry GPS EXIF — VeriPath verifies location automatically.")

        photo = st.file_uploader("Upload photo (JPEG/PNG)",
                                  type=["jpg","jpeg","png"],
                                  key="farmer_photo_upload")

        THRESHOLD_M    = 500
        geo_verified   = False
        geo_suspicious = False
        exif_coords    = None
        distance_m     = None

        if photo and captured_gps:
            photo.seek(0)
            exif_coords = extract_exif_gps(photo)
            photo.seek(0)
            if exif_coords:
                distance_m = haversine_m(
                    captured_gps[0], captured_gps[1],
                    exif_coords[0],  exif_coords[1]
                )
                if distance_m <= THRESHOLD_M:
                    geo_verified = True
                    st.markdown(f"""
                    <div style='background:#071a0f;border:2px solid #16a34a;
                                border-radius:10px;padding:11px 16px;margin-top:6px'>
                        <b style='color:#4ade80'>GPS Verified</b>
                        <span style='color:#94a3b8;font-size:0.85rem'>
                         — Photo EXIF matches within <b>{distance_m:.0f}m</b>
                        </span>
                    </div>""", unsafe_allow_html=True)
                else:
                    geo_suspicious = True
                    st.markdown(f"""
                    <div style='background:#1a0a0a;border:2px solid #dc2626;
                                border-radius:10px;padding:11px 16px;margin-top:6px'>
                        <b style='color:#f87171'>Location Mismatch — SUSPICIOUS</b><br>
                        <span style='color:#94a3b8;font-size:0.85rem'>
                        Photo EXIF is <b>{distance_m:.0f}m away</b> from captured GPS
                        (threshold {THRESHOLD_M}m).<br>
                        Captured: {captured_gps[0]:.5f}, {captured_gps[1]:.5f} |
                        EXIF: {exif_coords[0]:.5f}, {exif_coords[1]:.5f}
                        </span>
                    </div>""", unsafe_allow_html=True)
            else:
                geo_verified = True
                st.info("No GPS EXIF in photo — manual GPS accepted.")

        # ── Farmer invite code inside registration ────────────────────────
        st.markdown("#### Farmer App Invite Code")
        st.caption("Generate a VP-FAR code so this farmer can log into VeriPath directly.")

        col_fa, col_fb = st.columns([3,2])
        with col_fa:
            if "pending_farmer_code" in st.session_state:
                st.markdown(f"""
                <div style='background:#0f172a;border:1px solid #38bdf8;border-radius:7px;
                            padding:9px 14px;font-family:monospace;font-size:0.95rem;color:#38bdf8'>
                    {st.session_state["pending_farmer_code"]}
                </div>""", unsafe_allow_html=True)
        with col_fb:
            if st.button("Generate VP-FAR Code", key="gen_far_inline"):
                code = generate_invite_code("farmer",
                                             created_by=profile.get("username",""))
                st.session_state["pending_farmer_code"] = code
                st.rerun()

        if "pending_farmer_code" in st.session_state:
            fc      = st.session_state["pending_farmer_code"]
            wa_msg  = f"Hello,+your+VeriPath+farmer+code+is:+{fc}"
            wa_link = f"https://wa.me/?text={wa_msg}"
            st.markdown(f"""
            <a href="{wa_link}" target="_blank"
               style='background:#16a34a;color:white;padding:8px 20px;border-radius:7px;
                      font-size:0.82rem;font-weight:700;text-decoration:none;
                      display:inline-block;margin-top:6px'>
                Send via WhatsApp
            </a>""", unsafe_allow_html=True)

        st.markdown("---")

        override_geo = False
        if geo_suspicious:
            override_geo = st.checkbox(
                "I acknowledge the location mismatch and confirm this registration is legitimate.",
                key="geo_override_cb"
            )

        if st.button("Register and Generate QR Card",
                     use_container_width=True, type="primary"):
            errors = []
            if not name.strip():           errors.append("Full name is required.")
            if not phone.strip():          errors.append("Phone number is required.")
            if county == "— Select —":     errors.append("County is required.")
            if not crops:                  errors.append("At least one crop is required.")
            if not photo:                  errors.append("Farm photo is required.")
            if not raw_gps:                errors.append("GPS location is required — tap Use My Location.")
            if captured_gps is None and raw_gps:
                errors.append("GPS format invalid. Use: -0.3031, 36.8000")
            if geo_suspicious and not override_geo:
                errors.append("Location mismatch flagged — tick the acknowledgement box to proceed.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                farmer_id = "VP-" + str(uuid.uuid4())[:8].upper()
                gps_str   = f"{captured_gps[0]:.6f}, {captured_gps[1]:.6f}"

                if geo_suspicious and override_geo:
                    geo_status = f"SUSPICIOUS_OVERRIDE — {distance_m:.0f}m mismatch acknowledged"
                elif geo_verified and exif_coords:
                    geo_status = f"VERIFIED — EXIF match within {distance_m:.0f}m"
                elif geo_verified:
                    geo_status = "ACCEPTED — No EXIF (manual GPS)"
                else:
                    geo_status = "UNVERIFIED"

                farmer_data = {
                    "name":          name.strip(),
                    "phone":         phone.strip(),
                    "id_number":     id_number.strip(),
                    "county":        county,
                    "sub_location":  sub_location.strip(),
                    "farm_size_ha":  farm_size_ha,
                    "crops":         crops,
                    "hs_codes":      {c: CROP_HS_CODES[c] for c in crops},
                    "gps":           gps_str,
                    "geo_status":    geo_status,
                    "company":       company,
                    "registered_by": profile.get("username",""),
                    "registered_at": datetime.now().isoformat(),
                    "status":        "Active",
                }

                from supabase_db import save_farmer_db
                save_farmer_db(farmer_id, farmer_data)

                st.session_state.pop("gps_captured", None)
                st.session_state.pop("pending_farmer_code", None)

                st.success(f"Registered! {name} — ID: {farmer_id} | {geo_status}")

                qr_buf = generate_qr(farmer_id, farmer_data)
                col_a, col_b = st.columns([1,1])
                with col_a:
                    st.image(Image.open(qr_buf), caption=f"QR — {name}", width=240)
                with col_b:
                    st.markdown(f"""
                    **ID:** `{farmer_id}`
                    **Name:** {name}
                    **Phone:** {phone}
                    **County:** {county}
                    **Farm:** {farm_size_ha} ha
                    **Crops:** {', '.join(crops)}
                    **GPS:** {gps_str}
                    **Geo:** {geo_status}
                    **Company:** {company}
                    **Registered:** {datetime.now().strftime('%d %b %Y')}
                    """)
                qr_buf.seek(0)
                st.download_button(
                    "Download QR Card PNG", data=qr_buf,
                    file_name=f"VeriPath_QR_{farmer_id}.png",
                    mime="image/png", use_container_width=True
                )

    with tab2:
        if not farmers:
            st.info("No farmers registered yet for your company.")
            return

        st.markdown(f"**{len(farmers)} outgrowers registered under {company}**")
        search = st.text_input("Search by name or ID", placeholder="Jane or VP-...")

        suspicious_list = [(fid, f) for fid, f in farmers.items()
                           if "SUSPICIOUS" in f.get("geo_status","")]
        if suspicious_list:
            st.markdown(f"""
            <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:8px;
                        padding:10px 14px;margin-bottom:12px'>
                <b style='color:#f87171'>{len(suspicious_list)} farmer(s) flagged
                with GPS mismatch</b> — field verification required before shipment.
            </div>""", unsafe_allow_html=True)

        for fid, fdata in farmers.items():
            if search and search.lower() not in fdata["name"].lower() \
                       and search.lower() not in fid.lower():
                continue

            geo_st  = fdata.get("geo_status","")
            is_susp = "SUSPICIOUS" in geo_st
            badge   = "GPS Mismatch" if is_susp else \
                      ("Verified" if "VERIFIED" in geo_st else "Manual GPS")

            with st.expander(f"{fdata['name']} · {fid} · {fdata['county']} · {badge}"):
                col1, col2 = st.columns([1,1])
                with col1:
                    qr_buf = generate_qr(fid, fdata)
                    st.image(Image.open(qr_buf), width=200)
                    qr_buf.seek(0)
                    st.download_button(
                        "Download QR", data=qr_buf,
                        file_name=f"VeriPath_QR_{fid}.png",
                        mime="image/png", key=f"dl_{fid}"
                    )
                with col2:
                    st.markdown(f"""
                    **ID:** `{fid}`
                    **Phone:** {fdata['phone']}
                    **National ID:** {fdata.get('id_number','—')}
                    **Sub-location:** {fdata.get('sub_location','—')}
                    **Farm size:** {fdata['farm_size_ha']} ha
                    **Crops:** {', '.join(fdata['crops'])}
                    **GPS:** {fdata.get('gps','—')}
                    **Geo Status:** {geo_st or '—'}
                    **Registered by:** {fdata.get('registered_by','—')}
                    **Status:** {fdata['status']}
                    **Registered:** {fdata['registered_at'][:10]}
                    """)
                    if is_susp:
                        st.markdown("""
                        <div style='background:#1a0a0a;border:1px solid #dc2626;
                                    border-radius:6px;padding:8px 12px;margin-top:6px;
                                    font-size:0.82rem;color:#f87171'>
                        Photo GPS did not match captured location.
                        Requires field verification before any shipment approval.
                        </div>""", unsafe_allow_html=True)
