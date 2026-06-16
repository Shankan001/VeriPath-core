import streamlit as st
import qrcode
import json
import os
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image

FARMERS_DB = "farmers.json"

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
    "Avocado": "080440",
    "French Beans": "070820",
    "Roses": "060311",
    "Carnations": "060312",
    "Mango": "080450",
    "Passion Fruit": "081090",
    "Macadamia": "080251",
    "Tea": "090210",
    "Coffee": "090111",
    "Spinach": "070970",
    "Kale": "070499",
    "Capsicum": "070960",
    "Tomato": "070200",
    "Snow Peas": "071021",
}

def load_farmers():
    if os.path.exists(FARMERS_DB):
        with open(FARMERS_DB, "r") as f:
            return json.load(f)
    return {}

def save_farmers(farmers):
    with open(FARMERS_DB, "w") as f:
        json.dump(farmers, f, indent=2)

def generate_qr(farmer_id, farmer_data):
    payload = json.dumps({
        "id": farmer_id,
        "name": farmer_data["name"],
        "phone": farmer_data["phone"],
        "county": farmer_data["county"],
        "crops": farmer_data["crops"],
        "gps": farmer_data.get("gps", ""),
        "registered": farmer_data["registered_at"]
    })
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a6b3c", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def render_qr_page():
    st.markdown("""
    <style>
    .vp-header {
        background: linear-gradient(135deg, #1a6b3c 0%, #2d9e5f 100%);
        color: white;
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="vp-header">
        <h2 style="margin:0;font-size:1.4rem;">🌿 Outgrower Registry</h2>
        <p style="margin:6px 0 0;opacity:0.85;font-size:0.9rem;">Register farmers · Generate QR cards · Link to packhouse</p>
    </div>
    """, unsafe_allow_html=True)

    farmers = load_farmers()
    tab1, tab2 = st.tabs(["➕ Register Farmer", "📋 View All Farmers"])

    with tab1:
        st.markdown("### New Outgrower Registration")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="e.g. Jane Wanjiku")
            phone = st.text_input("Phone Number *", placeholder="+254712345678")
            id_number = st.text_input("National ID Number", placeholder="12345678")
        with col2:
            county = st.selectbox("County *", ["— Select —"] + KENYA_COUNTIES)
            sub_location = st.text_input("Sub-location / Village", placeholder="e.g. Ol Kalou")
            farm_size_ha = st.number_input("Farm Size (hectares)", min_value=0.1, max_value=500.0, value=1.0, step=0.1)

        crops = st.multiselect(
            "Crops Grown *",
            options=list(CROP_HS_CODES.keys()),
            help="Select all crops this farmer grows — they can vary per intake session"
        )
        gps = st.text_input("GPS Coordinates (optional)", placeholder="-0.3031, 36.8000")

        st.markdown("---")
        if st.button("✅ Register & Generate QR Card", use_container_width=True, type="primary"):
            if not name or not phone or county == "— Select —" or not crops:
                st.error("Please fill in all required fields: Name, Phone, County, Crops.")
            else:
                farmer_id = "VP-" + str(uuid.uuid4())[:8].upper()
                farmer_data = {
                    "name": name,
                    "phone": phone,
                    "id_number": id_number,
                    "county": county,
                    "sub_location": sub_location,
                    "farm_size_ha": farm_size_ha,
                    "crops": crops,
                    "hs_codes": {c: CROP_HS_CODES[c] for c in crops},
                    "gps": gps,
                    "registered_at": datetime.now().isoformat(),
                    "status": "Active"
                }
                farmers[farmer_id] = farmer_data
                save_farmers(farmers)

                st.success(f"✅ Farmer registered! ID: **{farmer_id}**")
                qr_buf = generate_qr(farmer_id, farmer_data)
                qr_img = Image.open(qr_buf)

                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.image(qr_img, caption=f"QR Card — {name}", width=240)
                with col_b:
                    st.markdown(f"""
                    **Farmer ID:** `{farmer_id}`
                    **Name:** {name}
                    **Phone:** {phone}
                    **County:** {county}
                    **Farm:** {farm_size_ha} ha
                    **Crops:** {', '.join(crops)}
                    **Registered:** {datetime.now().strftime('%d %b %Y')}
                    """)
                qr_buf.seek(0)
                st.download_button(
                    label="⬇️ Download QR Card (PNG)",
                    data=qr_buf,
                    file_name=f"VeriPath_QR_{farmer_id}.png",
                    mime="image/png",
                    use_container_width=True
                )

    with tab2:
        if not farmers:
            st.info("No farmers registered yet. Use the Register tab to add your first outgrower.")
        else:
            st.markdown(f"**{len(farmers)} outgrowers registered**")
            search = st.text_input("🔍 Search by name or ID", placeholder="Jane or VP-...")
            for fid, fdata in farmers.items():
                if search and search.lower() not in fdata["name"].lower() and search.lower() not in fid.lower():
                    continue
                with st.expander(f"🧑‍🌾 {fdata['name']}  •  {fid}  •  {fdata['county']}"):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        qr_buf = generate_qr(fid, fdata)
                        st.image(Image.open(qr_buf), width=200)
                        qr_buf.seek(0)
                        st.download_button(
                            "⬇️ Download QR",
                            data=qr_buf,
                            file_name=f"VeriPath_QR_{fid}.png",
                            mime="image/png",
                            key=f"dl_{fid}"
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
                        **Status:** {fdata['status']}
                        **Registered:** {fdata['registered_at'][:10]}
                        """)

if __name__ == "__main__":
    render_qr_page()
