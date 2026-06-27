import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_db import get_supabase

# ── Activity types farmers can log ───────────────────────────────────────
ACTIVITY_TYPES = {
    "planting":    {"label": "Planting",    "icon": "🌱", "color": "#16a34a"},
    "spraying":    {"label": "Spraying",    "icon": "💧", "color": "#0ea5e9"},
    "harvesting":  {"label": "Harvesting",  "icon": "🌾", "color": "#d97706"},
    "fertilizing": {"label": "Fertilizing", "icon": "🧪", "color": "#7c3aed"},
    "inspection":  {"label": "Inspection",  "icon": "🔍", "color": "#64748b"},
}

CHEMICAL_OPTIONS = [
    "None / Not applicable",
    "Mancozeb", "Chlorothalonil", "Copper Oxychloride",
    "Imidacloprid", "Lambda-cyhalothrin", "Cypermethrin",
    "Glyphosate", "Paraquat", "2,4-D",
    "Urea (fertilizer)", "CAN (fertilizer)", "DAP (fertilizer)",
    "Organic compost", "Neem extract (organic)",
    "Other (specify below)",
]


def load_farmer_profile(farmer_id: str) -> dict:
    try:
        sb  = get_supabase()
        res = sb.table("farmers").select("*").eq("farmer_id", farmer_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {}


def load_farmer_activities(farmer_id: str) -> list:
    try:
        sb  = get_supabase()
        res = (sb.table("farmer_activities")
               .select("*")
               .eq("farmer_id", farmer_id)
               .order("created_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def save_activity(data: dict):
    try:
        sb = get_supabase()
        sb.table("farmer_activities").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def load_farmer_batches(farmer_id: str) -> list:
    try:
        sb  = get_supabase()
        res = (sb.table("ledger")
               .select("*")
               .eq("farmer_id", farmer_id)
               .order("timestamp", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def load_farmer_payments(farmer_id: str) -> list:
    try:
        sb  = get_supabase()
        res = (sb.table("payments")
               .select("*")
               .eq("farmer_id", farmer_id)
               .order("payment_date", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


# ── Main dashboard ────────────────────────────────────────────────────────
def render_farmer_dashboard(profile: dict):
    farmer_id = profile.get("farmer_id") or profile.get("username","")
    company   = profile.get("company","")
    name      = profile.get("full_name", profile.get("name","Farmer"))

    # Header
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#14532d 0%,#16a34a 100%);
                color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px'>
        <div style='font-size:1.3rem;font-weight:700'>Welcome, {name}</div>
        <div style='opacity:0.85;font-size:0.88rem;margin-top:4px'>
            VeriPath Farmer Portal &nbsp;·&nbsp; {company}
        </div>
    </div>
    """, unsafe_allow_html=True)

    farmer = load_farmer_profile(farmer_id)

    # Quick stats
    batches  = load_farmer_batches(farmer_id)
    payments = load_farmer_payments(farmer_id)
    total_kg = sum(float(b.get("weight_kg",0)) for b in batches)
    total_paid = sum(float(p.get("amount",0)) for p in payments)

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Total Batches",    str(len(batches)),   "#16a34a"),
        (c2, "Total Weight (kg)",f"{total_kg:,.0f}",  "#0ea5e9"),
        (c3, "Payments Received",f"KES {total_paid:,.0f}", "#d97706"),
        (c4, "Farm Size",        f"{farmer.get('farm_size_ha','—')} ha", "#7c3aed"),
    ]
    for col, label, value, color in cards:
        with col:
            st.markdown(f"""
            <div style='background:#0f172a;border:1px solid {color};border-radius:10px;
                        padding:14px 16px;text-align:center'>
                <div style='color:#64748b;font-size:0.78rem;margin-bottom:4px'>{label}</div>
                <div style='color:{color};font-size:1.5rem;font-weight:700'>{value}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Log Activity",
        "📦 My Batches",
        "💰 Payments",
        "🌿 My Farm Profile",
    ])

    # ── TAB 1: Log farm activity with photo ───────────────────────────────
    with tab1:
        st.markdown("### Log Farm Activity")
        st.caption("Upload a photo at each stage — planting, spraying, harvesting. "
                   "GPS in your photo is used for EUDR location verification.")

        col_a, col_b = st.columns(2)
        with col_a:
            activity_key  = st.selectbox(
                "Activity Type *",
                options=list(ACTIVITY_TYPES.keys()),
                format_func=lambda k: f"{ACTIVITY_TYPES[k]['icon']} {ACTIVITY_TYPES[k]['label']}"
            )
            activity_date = st.date_input("Date *", value=datetime.today())
            crop          = st.selectbox("Crop *",
                options=farmer.get("crops", ["—"]) if farmer else ["—"])
        with col_b:
            plot_area_ha  = st.number_input("Plot Area (ha)", min_value=0.1,
                                             max_value=500.0, value=1.0, step=0.1)
            chemicals     = st.multiselect("Chemicals / Inputs Used", CHEMICAL_OPTIONS,
                                            default=["None / Not applicable"])
            if "Other (specify below)" in chemicals:
                other_chem = st.text_input("Specify other chemical")
            else:
                other_chem = ""

        notes = st.text_area("Notes / Observations",
                              placeholder="e.g. Applied 2L/acre, weather was dry, signs of aphids on 3 rows...")

        st.markdown("#### Photo Evidence *")
        st.caption("Take the photo on your phone at the farm. "
                   "Phone photos carry GPS location data — this verifies your farm against EUDR maps.")
        photo = st.file_uploader("Upload activity photo (JPEG preferred)",
                                  type=["jpg","jpeg","png"],
                                  key=f"activity_photo_{activity_key}")

        if photo:
            from PIL import Image as _Img
            img = _Img.open(photo)
            st.image(img, caption=f"{ACTIVITY_TYPES[activity_key]['icon']} "
                                   f"{ACTIVITY_TYPES[activity_key]['label']} photo",
                     width=320)
            # Check EXIF GPS
            photo.seek(0)
            try:
                exif = img._getexif()
                if exif:
                    from PIL.ExifTags import TAGS, GPSTAGS
                    for tag_id, value in exif.items():
                        if TAGS.get(tag_id) == "GPSInfo":
                            st.markdown("""
                            <div style='background:#071a0f;border:1px solid #16a34a;
                                        border-radius:7px;padding:8px 14px;font-size:0.83rem;
                                        color:#4ade80;margin-top:6px'>
                                GPS found in photo — location will be verified against EUDR maps.
                            </div>""", unsafe_allow_html=True)
                            break
                    else:
                        st.info("No GPS in photo EXIF. Try uploading directly from your phone camera.")
                else:
                    st.info("No EXIF data in photo. Direct camera photos work best.")
            except Exception:
                pass
            photo.seek(0)

        if st.button("Submit Activity Log", type="primary", use_container_width=True):
            if not photo:
                st.error("Photo is required for every activity log.")
            else:
                import base64
                photo.seek(0)
                photo_b64 = base64.b64encode(photo.read()).decode()
                chem_list = [c for c in chemicals if c != "None / Not applicable"]
                if other_chem:
                    chem_list.append(other_chem)

                record = {
                    "farmer_id":    farmer_id,
                    "company":      company,
                    "activity":     activity_key,
                    "crop":         crop,
                    "date":         str(activity_date),
                    "plot_area_ha": plot_area_ha,
                    "chemicals":    chem_list,
                    "notes":        notes.strip(),
                    "photo_b64":    photo_b64,
                    "created_at":   datetime.now().isoformat(),
                    "status":       "submitted",
                }
                if save_activity(record):
                    st.success(f"{ACTIVITY_TYPES[activity_key]['icon']} "
                               f"{ACTIVITY_TYPES[activity_key]['label']} activity logged successfully.")
                    st.rerun()

    # ── TAB 2: Submitted batches ──────────────────────────────────────────
    with tab2:
        st.markdown("### My Submitted Batches")
        if not batches:
            st.info("No batches submitted yet. Batches are recorded at the packhouse.")
        else:
            for b in batches:
                eudr   = b.get("eudr_risk","—")
                color  = {"GREEN":"#16a34a","AMBER":"#d97706","RED":"#dc2626"}.get(eudr,"#64748b")
                status = b.get("status","pending")
                st.markdown(f"""
                <div style='background:#0f172a;border:1px solid {color};border-radius:10px;
                            padding:14px 18px;margin-bottom:10px'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div>
                            <span style='color:#e8eaf0;font-weight:700'>{b.get("crop","—")}</span>
                            &nbsp;&middot;&nbsp;
                            <span style='color:#94a3b8'>{b.get("weight_kg","—")} kg</span>
                            &nbsp;&middot;&nbsp;
                            <span style='color:#64748b;font-size:0.82rem'>{str(b.get("timestamp",""))[:10]}</span>
                        </div>
                        <div>
                            <span style='background:{color}22;color:{color};padding:3px 10px;
                                         border-radius:20px;font-size:0.8rem;font-weight:700'>
                                EUDR: {eudr}
                            </span>
                        </div>
                    </div>
                    <div style='margin-top:8px;color:#64748b;font-size:0.82rem'>
                        Packhouse: {b.get("packhouse","—")} &nbsp;&middot;&nbsp;
                        Grade: {b.get("grade","—")} &nbsp;&middot;&nbsp;
                        Status: <b style='color:#94a3b8'>{status.title()}</b>
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── TAB 3: Payments ───────────────────────────────────────────────────
    with tab3:
        st.markdown("### Payment Receipts")
        if not payments:
            st.info("No payment records yet. Payments will appear here once processed by your exporter.")
        else:
            total = sum(float(p.get("amount",0)) for p in payments)
            st.markdown(f"""
            <div style='background:#071a0f;border:1px solid #16a34a;border-radius:10px;
                        padding:14px 18px;margin-bottom:16px;text-align:center'>
                <div style='color:#64748b;font-size:0.85rem'>Total Received</div>
                <div style='color:#4ade80;font-size:2rem;font-weight:700'>
                    KES {total:,.0f}
                </div>
            </div>""", unsafe_allow_html=True)

            for p in payments:
                st.markdown(f"""
                <div style='background:#0f172a;border:1px solid #1e293b;border-radius:9px;
                            padding:12px 16px;margin-bottom:8px;
                            display:flex;justify-content:space-between'>
                    <div>
                        <div style='color:#e8eaf0;font-weight:700'>
                            KES {float(p.get("amount",0)):,.0f}
                        </div>
                        <div style='color:#64748b;font-size:0.82rem'>
                            {p.get("crop","—")} &middot; {p.get("batch_ref","—")}
                        </div>
                    </div>
                    <div style='text-align:right'>
                        <div style='color:#4ade80;font-size:0.82rem'>
                            {str(p.get("payment_date",""))[:10]}
                        </div>
                        <div style='color:#64748b;font-size:0.78rem'>
                            {p.get("method","—")}
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

            # Download receipts as CSV
            df_pay = pd.DataFrame(payments)
            csv    = df_pay.to_csv(index=False).encode()
            st.download_button("Download Payment History CSV", data=csv,
                               file_name=f"VeriPath_Payments_{farmer_id}.csv",
                               mime="text/csv", use_container_width=True)

    # ── TAB 4: Farm profile ───────────────────────────────────────────────
    with tab4:
        st.markdown("### My Farm Profile")
        if not farmer:
            st.info("Farm profile not found. Contact your record keeper.")
        else:
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"""
                **Farmer ID:** `{farmer_id}`
                **Name:** {farmer.get("name","—")}
                **Phone:** {farmer.get("phone","—")}
                **National ID:** {farmer.get("id_number","—")}
                **County:** {farmer.get("county","—")}
                **Sub-location:** {farmer.get("sub_location","—")}
                **Farm Size:** {farmer.get("farm_size_ha","—")} ha
                **Crops:** {", ".join(farmer.get("crops",[]))}
                **GPS:** {farmer.get("gps","—")}
                **Geo Status:** {farmer.get("geo_status","—")}
                **Registered:** {str(farmer.get("registered_at",""))[:10]}
                """)
            with col_r:
                # Activity history summary
                activities = load_farmer_activities(farmer_id)
                if activities:
                    st.markdown("**Recent Activity Logs**")
                    for act in activities[:5]:
                        icon = ACTIVITY_TYPES.get(act.get("activity",""),{}).get("icon","📋")
                        st.markdown(f"""
                        <div style='background:#0f172a;border-radius:7px;padding:8px 12px;
                                    margin-bottom:6px;font-size:0.85rem'>
                            {icon} <b style='color:#e8eaf0'>{act.get("activity","").title()}</b>
                            &nbsp;&middot;&nbsp;
                            <span style='color:#64748b'>{act.get("crop","—")}</span>
                            &nbsp;&middot;&nbsp;
                            <span style='color:#64748b'>{str(act.get("date",""))[:10]}</span>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.info("No activity logs yet.")
