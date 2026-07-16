with open("kpi_dashboard.py", "r") as f:
    content = f.read()

anchor = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Upgrade Company Subscription</div>", unsafe_allow_html=True)'''

toggle_section = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Live Portal Transmission</div>", unsafe_allow_html=True)

    from supabase_db import get_client as _gc2
    try:
        _live_row = _gc2().table("platform_settings").select("setting_value").eq(
            "setting_key", "live_transmission_enabled"
        ).execute().data
        _live_now = _live_row[0]["setting_value"] == "true" if _live_row else False
    except Exception:
        _live_now = False

    st.markdown(
        f"Current status: {'🟢 **ENABLED**' if _live_now else '🔒 **LOCKED**'} — "
        f"controls whether any exporter can use Live Mode on Transmit to Portals."
    )
    col_lock1, col_lock2 = st.columns(2)
    with col_lock1:
        if st.button("🔓 Enable Live Transmission", use_container_width=True, disabled=_live_now):
            _gc2().table("platform_settings").upsert({
                "setting_key": "live_transmission_enabled",
                "setting_value": "true",
                "updated_by": "admin",
            }, on_conflict="setting_key").execute()
            st.success("✅ Live transmission enabled.")
            st.rerun()
    with col_lock2:
        if st.button("🔒 Lock Live Transmission", use_container_width=True, disabled=not _live_now):
            _gc2().table("platform_settings").upsert({
                "setting_key": "live_transmission_enabled",
                "setting_value": "false",
                "updated_by": "admin",
            }, on_conflict="setting_key").execute()
            st.warning("🔒 Live transmission locked.")
            st.rerun()

    st.markdown("---")

''' + anchor

if anchor not in content:
    print("ERROR: anchor not found — no changes made.")
else:
    content = content.replace(anchor, toggle_section)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("Added Live Transmission lock/unlock toggle to KPI Dashboard.")
