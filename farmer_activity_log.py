import streamlit as st
from supabase_db import get_client, get_signed_activity_photo_url
from farmer_dashboard import ACTIVITY_TYPES


def get_scoped_farmers_for_log(supabase, company: str) -> list:
    """Same pattern as get_scoped_farmers() elsewhere in the app — company is
    required, not optional, so a missing company returns nothing rather than
    everyone."""
    if not company or not company.strip():
        return []
    try:
        rows = supabase.table("farmers").select("farmer_id, name, phone, company").execute().data
        company_norm = company.strip().lower()
        return [f for f in rows if f.get("company", "").strip().lower() == company_norm]
    except Exception:
        return []


def load_activities_for_farmer(supabase, farmer_id: str, allowed_farmer_ids: set) -> list:
    """Defense in depth: even though the UI only ever offers farmer_ids already
    scoped to this company, double-check membership here too before querying —
    same standard applied to every other company-scoped read this session."""
    if farmer_id not in allowed_farmer_ids:
        return []
    try:
        res = (supabase.table("farmer_activities")
               .select("*")
               .eq("farmer_id", farmer_id)
               .order("date", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def render_farmer_activity_log_page(profile: dict):
    st.markdown("# 🔍 Farmer Activity Log")
    st.caption("Search a farmer to view their full logged activity history — "
               "planting, spraying, harvesting, inspections — with photo evidence.")
    st.markdown("---")

    supabase = get_client()
    company  = profile.get("company", "")
    farmers  = get_scoped_farmers_for_log(supabase, company)
    allowed_ids = {f["farmer_id"] for f in farmers}

    if not farmers:
        st.info("No registered farmers found for your company yet.")
        return

    search = st.text_input("🔎 Search by farmer name, phone, or ID")
    filtered = farmers
    if search.strip():
        s = search.strip().lower()
        filtered = [
            f for f in farmers
            if s in f.get("name", "").lower()
            or s in f.get("phone", "").lower()
            or s in f.get("farmer_id", "").lower()
        ]

    if not filtered:
        st.warning("No farmers match that search.")
        return

    options = {f"{f['name']} ({f['phone']}) — {f['farmer_id']}": f["farmer_id"] for f in filtered}
    selected_label = st.selectbox("Select a farmer", ["— Select —"] + list(options.keys()))

    if selected_label == "— Select —":
        return

    selected_farmer_id = options[selected_label]
    activities = load_activities_for_farmer(supabase, selected_farmer_id, allowed_ids)

    st.markdown(f"### 📋 Activity History — {selected_label.split(' (')[0]}")

    if not activities:
        st.info("No activities logged for this farmer yet.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        activity_filter = st.multiselect(
            "Filter by activity type",
            options=list(ACTIVITY_TYPES.keys()),
            format_func=lambda k: f"{ACTIVITY_TYPES[k]['icon']} {ACTIVITY_TYPES[k]['label']}",
        )
    with col2:
        crop_options = sorted({a.get("crop", "—") for a in activities})
        crop_filter = st.multiselect("Filter by crop", options=crop_options)
    with col3:
        date_range = st.date_input("Date range", value=())

    shown = activities
    if activity_filter:
        shown = [a for a in shown if a.get("activity") in activity_filter]
    if crop_filter:
        shown = [a for a in shown if a.get("crop") in crop_filter]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        shown = [a for a in shown if start.isoformat() <= a.get("date", "") <= end.isoformat()]

    st.markdown(f"**{len(shown)} of {len(activities)} activities shown**")
    st.markdown("---")

    for a in shown:
        act_key = a.get("activity", "")
        act_cfg = ACTIVITY_TYPES.get(act_key, {"label": act_key, "icon": "📋", "color": "#64748b"})
        chemicals = a.get("chemicals") or []

        st.markdown(f"""
        <div style='background:#0f172a;border-left:4px solid {act_cfg['color']};
                    border-radius:8px;padding:14px 18px;margin-bottom:6px'>
            <div style='font-weight:700;color:#e8eaf0'>{act_cfg['icon']} {act_cfg['label']} — {a.get('date','—')}</div>
            <div style='color:#94a3b8;font-size:0.85rem;margin-top:4px'>
                Crop: {a.get('crop','—')} · Plot: {a.get('plot_area_ha','—')} ha
                {' · Chemicals: ' + ', '.join(chemicals) if chemicals else ''}
            </div>
            {f"<div style='color:#cbd5e1;font-size:0.85rem;margin-top:6px'>{a.get('notes','')}</div>" if a.get('notes') else ''}
        </div>
        """, unsafe_allow_html=True)

        # Signed URL generated lazily on expand only — no photo bytes are
        # fetched or decoded until the viewer actually opens this entry.
        if a.get("photo_path"):
            with st.expander("📸 View photo evidence"):
                signed_url = get_signed_activity_photo_url(a["photo_path"])
                if signed_url:
                    st.image(signed_url, width=400)
                else:
                    st.warning("Could not generate photo link for this entry.")

        st.markdown("---")
