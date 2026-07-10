with open("app.py", "r") as f:
    content = f.read()

# 1. Import the new module (near the top — after other local imports)
content = content.replace(
    "from weather_risk_dashboard import render_weather_risk_dashboard_page",
    "from weather_risk_dashboard import render_weather_risk_dashboard_page\n"
    "from session_persistence import (\n"
    "    get_valid_username_from_cookie, create_session,\n"
    "    set_session_cookie, clear_session\n"
    ")\n"
    "from supabase_db import get_user"
)

# 2. Right after the auth-state init block, try restoring from cookie
old_auth_init = '''for key, val in [("authenticated",False),("user_profile",None),("auth_page","login"),("reg_module",None)]:
    if key not in st.session_state:
        st.session_state[key] = val'''

new_auth_init = '''for key, val in [("authenticated",False),("user_profile",None),("auth_page","login"),("reg_module",None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Restore session from cookie (survives page refresh) ────────────────────
if not st.session_state["authenticated"]:
    _cookie_username = get_valid_username_from_cookie()
    if _cookie_username:
        _restored_user = get_user(_cookie_username)
        if _restored_user:
            st.session_state["authenticated"] = True
            st.session_state["user_profile"] = {
                k: v for k, v in _restored_user.items()
                if k not in ("password", "salt")
            }'''

content = content.replace(old_auth_init, new_auth_init)

# 3. On successful login, create + set the session cookie
old_login_success = '''                ok, msg, profile = login_user(username, password)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_profile"]  = profile
                    st.success(f"✅ {msg}")
                    st.rerun()'''

new_login_success = '''                ok, msg, profile = login_user(username, password)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_profile"]  = profile
                    _token = create_session(profile["username"])
                    set_session_cookie(_token)
                    st.success(f"✅ {msg}")
                    st.rerun()'''

content = content.replace(old_login_success, new_login_success)

# 4. On sign out, clear the server-side session + cookie
old_signout = '''if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    for k in ["authenticated","user_profile","auth_page","audit_result",
              "batch_approved","intake_rows","ingestion_entries","reg_module"]:
        st.session_state.pop(k, None)
    st.rerun()'''

new_signout = '''if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    clear_session()
    for k in ["authenticated","user_profile","auth_page","audit_result",
              "batch_approved","intake_rows","ingestion_entries","reg_module"]:
        st.session_state.pop(k, None)
    st.rerun()'''

content = content.replace(old_signout, new_signout)

with open("app.py", "w") as f:
    f.write(content)

print("Patched app.py for session persistence.")
