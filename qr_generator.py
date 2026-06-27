import streamlit as st
import streamlit.components.v1 as components
import qrcode
import json
import uuid
import math
from datetime import datetime
from io import BytesIO
from PIL import Image
from ledger_db import load_farmers
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
    "Avocado":"080440","French Beans":"070820","Roses":"060311",
    "Carnations":"060312","Mango":"080450","Passion Fruit":"081090",
    "Macadamia Nuts":"080251","Tea":"090210","Coffee":"090111",
    "Spinach":"070970","Kale":"070499","Capsicum":"070960",
    "Tomato":"070200","Snow Peas":"071021","Pineapple":"080430","Maize":"100590",
}

def haversine_m(lat1,lon1,lat2,lon2):
    R=6_371_000
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def extract_exif_gps(image_file):
    try:
        img=Image.open(image_file); exif=img._getexif()
        if not exif: return None
        from PIL.ExifTags import TAGS,GPSTAGS
        gps={}
        for tid,val in exif.items():
            if TAGS.get(tid)=="GPSInfo":
                for gid,gv in val.items(): gps[GPSTAGS.get(gid,gid)]=gv
        if not gps: return None
        def dec(dms,ref):
            d,m,s=dms; v=float(d)+float(m)/60+float(s)/3600
            return -v if ref in("S","W") else v
        return dec(gps["GPSLatitude"],gps["GPSLatitudeRef"]),dec(gps["GPSLongitude"],gps["GPSLongitudeRef"])
    except: return None

def generate_qr(farmer_id,farmer_data):
    payload=json.dumps({
        "id":farmer_id,"name":farmer_data["name"],"phone":farmer_data["phone"],
        "county":farmer_data["county"],"crops":farmer_data["crops"],
        "gps":farmer_data.get("gps",""),"company":farmer_data.get("company",""),
        "registered":farmer_data["registered_at"],
    })
    qr=qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=8,border=3)
    qr.add_data(payload); qr.make(fit=True)
    img=qr.make_image(fill_color="#1a6b3c",back_color="white")
    buf=BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    return buf

def render_qr_page(profile: dict = None):
    company  = profile.get("company","") if profile else ""
    role     = profile.get("role","")    if profile else ""
    username = profile.get("username","") if profile else ""

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
    tab1, tab2 = st.tabs(["Register Farmer", "View All Farmers"])

    with tab1:
        st.markdown("### New Outgrower Registration")

        col1, col2 = st.columns(2)
        with col1:
            name         = st.text_input("Full Name *", placeholder="Jane Wanjiku")
            phone        = st.text_input("Phone Number *", placeholder="+254712345678")
            id_number    = st.text_input("National ID Number", placeholder="12345678")
        with col2:
            county       = st.selectbox("County *", ["-- Select --"] + KENYA_COUNTIES)
            sub_location = st.text_input("Sub-location / Village", placeholder="e.g. Ol Kalou")
            farm_size_ha = st.number_input("Farm Size (hectares)",
                                            min_value=0.1, max_value=500.0, value=1.0, step=0.1)

        crops = st.multiselect("Crops Grown *", options=list(CROP_HS_CODES.keys()))

        # ── GPS AUTO CAPTURE ──────────────────────────────────────────────
        st.markdown("#### GPS Farm Location *")
        st.caption("Tap the button below. GPS coordinates are captured automatically.")

        components.html("""
        <div style="font-family:monospace;padding:4px 0">
          <button id="gbtn" onclick="doGeo()"
            style="background:#1a6b3c;color:white;border:none;padding:12px 28px;
                   border-radius:8px;font-size:1rem;cursor:pointer;font-weight:700;
                   width:100%;margin-bottom:8px">
            Use My Location
          </button>
          <div id="gstatus" style="color:#94a3b8;font-size:0.85rem;min-height:20px"></div>
          <div id="gbox" style="display:none;margin-top:8px;background:#071a0f;
                                border:1px solid #16a34a;border-radius:6px;
                                padding:10px;color:#4ade80;font-size:0.9rem;
                                word-break:break-all"></div>
        </div>
        <script>
        function doGeo(){
          var btn=document.getElementById('gbtn');
          var st=document.getElementById('gstatus');
          var bx=document.getElementById('gbox');
          btn.disabled=true; btn.innerText='Detecting...';
          st.style.color='#94a3b8'; st.innerText='Getting GPS...';
          if(!navigator.geolocation){
            st.style.color='#f87171';
            st.innerText='GPS not supported on this browser.';
            btn.disabled=false; btn.innerText='Use My Location'; return;
          }
          navigator.geolocation.getCurrentPosition(function(p){
            var lat=p.coords.latitude.toFixed(6);
            var lon=p.coords.longitude.toFixed(6);
            var acc=Math.round(p.coords.accuracy);
            bx.style.display='block';
            bx.innerText=lat+', '+lon;
            st.style.color='#4ade80';
            st.innerText='GPS captured (+-'+acc+'m). Copy the value above into the field below.';
            btn.innerText='Location Captured'; btn.disabled=false;
          },function(e){
            var m={1:'Permission denied.',2:'Unavailable.',3:'Timed out.'};
            st.style.color='#f87171'; st.innerText=m[e.code]||e.message;
            btn.innerText='Try Again'; btn.disabled=false;
          },{enableHighAccuracy:true,timeout:20000,maximumAge:0});
        }
        </script>
        """, height=150)

        gps_input = st.text_input(
            "Paste GPS here after clicking button above *",
            placeholder="-1.353539, 36.651339",
            key="gps_field"
        )

        captured_gps = None
        if gps_input.strip():
            try:
                parts = gps_input.strip().split(",")
                captured_gps = (float(parts[0].strip()), float(parts[1].strip()))
                st.markdown(f"""
                <div style='background:#071a0f;border:1px solid #16a34a;border-radius:6px;
                            padding:8px 12px;font-size:0.85rem;color:#4ade80'>
                    GPS ready: {captured_gps[0]:.6f}, {captured_gps[1]:.6f}
                </div>""", unsafe_allow_html=True)
            except:
                st.warning("GPS format not valid. Use: -1.353539, 36.651339")

        # ── PHOTO UPLOAD + EXIF ───────────────────────────────────────────
        st.markdown("#### Farm / Farmer Photo *")
        st.caption("Take photo on your phone at the farm. Phone JPEG photos carry GPS — VeriPath checks location.")

        photo = st.file_uploader("Upload photo (JPEG/PNG)",
                                  type=["jpg","jpeg","png"], key="reg_photo")

        THRESHOLD_M   = 500
        geo_verified  = False
        geo_suspicious= False
        exif_coords   = None
        distance_m    = None

        if photo:
            st.image(photo, caption="Uploaded photo", width=300)
            if captured_gps:
                photo.seek(0)
                exif_coords = extract_exif_gps(photo)
                photo.seek(0)
                if exif_coords:
                    distance_m = haversine_m(captured_gps[0],captured_gps[1],
                                              exif_coords[0],exif_coords[1])
                    if distance_m <= THRESHOLD_M:
                        geo_verified = True
                        st.markdown(f"""
                        <div style='background:#071a0f;border:2px solid #16a34a;
                                    border-radius:8px;padding:10px 14px;margin-top:6px'>
                            <b style='color:#4ade80'>GPS Verified</b>
                            <span style='color:#94a3b8;font-size:0.85rem'>
                             - Photo EXIF matches within {distance_m:.0f}m
                            </span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        geo_suspicious = True
                        st.markdown(f"""
                        <div style='background:#1a0a0a;border:2px solid #dc2626;
                                    border-radius:8px;padding:10px 14px;margin-top:6px'>
                            <b style='color:#f87171'>Location Mismatch</b>
                            <span style='color:#94a3b8;font-size:0.85rem'>
                             Photo EXIF is {distance_m:.0f}m from your GPS (max {THRESHOLD_M}m)
                            </span>
                        </div>""", unsafe_allow_html=True)
                else:
                    geo_verified = True
                    st.info("No GPS EXIF in photo - manual GPS accepted.")
            else:
                st.info("Enter GPS coordinates above to enable EXIF verification.")

        # ── FARMER INVITE CODE ────────────────────────────────────────────
        st.markdown("#### Farmer App Invite Code")
        st.caption("Generate a VP-FAR code for this farmer to log into VeriPath.")

        col_fa, col_fb = st.columns([3,2])
        with col_fb:
            if st.button("Generate VP-FAR Code", key="gen_far"):
                code = generate_invite_code("farmer", created_by=username)
                st.session_state["far_code"] = code
        with col_fa:
            if st.session_state.get("far_code"):
                st.code(st.session_state["far_code"], language=None)

        if st.session_state.get("far_code"):
            fc = st.session_state["far_code"]
            wa = f"https://wa.me/?text=Your+VeriPath+farmer+code:+{fc}"
            st.markdown(f"""
            <a href='{wa}' target='_blank'
               style='background:#16a34a;color:white;padding:8px 20px;border-radius:7px;
                      font-size:0.85rem;font-weight:700;text-decoration:none;
                      display:inline-block;margin-top:6px'>
                Send via WhatsApp
            </a>""", unsafe_allow_html=True)

        # ── SUSPICIOUS OVERRIDE ───────────────────────────────────────────
        override_geo = False
        if geo_suspicious:
            override_geo = st.checkbox(
                "I acknowledge the location mismatch and confirm this is legitimate.",
                key="geo_ov"
            )

        st.markdown("---")

        # ── REGISTER BUTTON ───────────────────────────────────────────────
        if st.button("Register and Generate QR Card",
                     use_container_width=True, type="primary"):
            errors = []
            if not name.strip():              errors.append("Full name is required.")
            if not phone.strip():             errors.append("Phone number is required.")
            if county == "-- Select --":      errors.append("County is required.")
            if not crops:                     errors.append("At least one crop is required.")
            if not photo:                     errors.append("Farm photo is required.")
            if not gps_input.strip():         errors.append("GPS is required - tap Use My Location then paste.")
            if captured_gps is None and gps_input.strip():
                errors.append("GPS format invalid. Use: -1.353539, 36.651339")
            if geo_suspicious and not override_geo:
                errors.append("Tick the location mismatch acknowledgement to proceed.")

            if errors:
                for e in errors: st.error(e)
            else:
                farmer_id = "VP-" + str(uuid.uuid4())[:8].upper()
                gps_str   = f"{captured_gps[0]:.6f}, {captured_gps[1]:.6f}"

                if geo_suspicious and override_geo:
                    geo_status = f"SUSPICIOUS_OVERRIDE - {distance_m:.0f}m mismatch"
                elif geo_verified and exif_coords:
                    geo_status = f"VERIFIED - EXIF match within {distance_m:.0f}m"
                else:
                    geo_status = "ACCEPTED - No EXIF"

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
                    "registered_by": username,
                    "registered_at": datetime.now().isoformat(),
                    "status":        "Active",
                }
                from supabase_db import save_farmer_db
                save_farmer_db(farmer_id, farmer_data)
                st.session_state.pop("far_code", None)

                st.success(f"Registered! {name} - ID: {farmer_id}")
                qr_buf = generate_qr(farmer_id, farmer_data)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(Image.open(qr_buf), caption=f"QR - {name}", width=240)
                with col_b:
                    st.markdown(f"""
                    **ID:** `{farmer_id}`
                    **Name:** {name}
                    **Phone:** {phone}
                    **County:** {county}
                    **Crops:** {', '.join(crops)}
                    **GPS:** {gps_str}
                    **Geo:** {geo_status}
                    **Registered:** {datetime.now().strftime('%d %b %Y')}
                    """)
                qr_buf.seek(0)
                st.download_button("Download QR Card PNG", data=qr_buf,
                    file_name=f"VeriPath_QR_{farmer_id}.png",
                    mime="image/png", use_container_width=True)

    # ── VIEW ALL FARMERS ──────────────────────────────────────────────────
    with tab2:
        if not farmers:
            st.info("No farmers registered yet.")
            return

        st.markdown(f"**{len(farmers)} outgrowers registered under {company}**")
        search = st.text_input("Search by name or ID", placeholder="Jane or VP-...")

        suspicious_list = [f for f in farmers.values() if "SUSPICIOUS" in f.get("geo_status","")]
        if suspicious_list:
            st.markdown(f"""
            <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:8px;
                        padding:10px 14px;margin-bottom:12px;color:#f87171'>
                <b>{len(suspicious_list)} farmer(s) flagged with GPS mismatch</b>
                - field verification required before shipment.
            </div>""", unsafe_allow_html=True)

        for fid, fdata in farmers.items():
            if search and search.lower() not in fdata["name"].lower() \
                       and search.lower() not in fid.lower():
                continue
            geo_st  = fdata.get("geo_status","")
            is_susp = "SUSPICIOUS" in geo_st
            badge   = "GPS Mismatch" if is_susp else ("Verified" if "VERIFIED" in geo_st else "Manual GPS")
            reg_by  = fdata.get("registered_by","—")

            with st.expander(f"{fdata['name']} - {fid} - {fdata['county']} - {badge}"):
                col1, col2 = st.columns(2)
                with col1:
                    qr_buf = generate_qr(fid, fdata)
                    st.image(Image.open(qr_buf), width=200)
                    qr_buf.seek(0)
                    st.download_button("Download QR", data=qr_buf,
                        file_name=f"VeriPath_QR_{fid}.png",
                        mime="image/png", key=f"dl_{fid}")
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
                    **Registered by:** {reg_by}
                    **Status:** {fdata['status']}
                    **Registered:** {fdata['registered_at'][:10]}
                    """)
                    if is_susp:
                        st.error("Photo GPS did not match captured location. Field verification required.")
