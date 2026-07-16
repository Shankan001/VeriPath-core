with open("app.py", "r") as f:
    content = f.read()

old = '''        with col_tog2:
            if st.button("🟢 LIVE MODE",
                         use_container_width=True,
                         type="primary" if get_bridge_mode()=="real" else "secondary"):
                set_bridge_mode("real")
                st.rerun()'''

new = '''        from supabase_db import get_client as _gc
        try:
            _live_setting = _gc().table("platform_settings").select("setting_value").eq(
                "setting_key", "live_transmission_enabled"
            ).execute().data
            _live_enabled = _live_setting[0]["setting_value"] == "true" if _live_setting else False
        except Exception:
            _live_enabled = False

        with col_tog2:
            if _live_enabled:
                if st.button("🟢 LIVE MODE",
                             use_container_width=True,
                             type="primary" if get_bridge_mode()=="real" else "secondary"):
                    set_bridge_mode("real")
                    st.rerun()
            else:
                st.button("🔒 LIVE MODE (Locked)", use_container_width=True, disabled=True,
                           help="Live portal submission is locked until official integration approval is confirmed by VeriPath admin.")'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — Live Mode now locked unless admin enables it.")
