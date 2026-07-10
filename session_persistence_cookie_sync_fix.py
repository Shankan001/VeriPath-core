with open("session_persistence.py", "r") as f:
    content = f.read()

old = '''def get_valid_username_from_cookie():
    """Returns the username if a valid, non-expired session cookie exists, else None."""
    cookie_manager = get_cookie_manager()
    token = cookie_manager.get("veripath_session")
    if not token:
        return None'''

new = '''def get_valid_username_from_cookie():
    """Returns the username if a valid, non-expired session cookie exists, else None."""
    cookie_manager = get_cookie_manager()

    # Force a full cookie sync from the browser before reading — on the very
    # first script run after a page load, .get() can return None even when
    # the cookie exists, because the component hasn't synced yet.
    all_cookies = cookie_manager.get_all()
    token = all_cookies.get("veripath_session") if all_cookies else None

    if not token and not st.session_state.get("_cookie_sync_retried"):
        # Give the component one rerun to finish syncing, but only once
        # to avoid an infinite loop if there's genuinely no cookie.
        st.session_state["_cookie_sync_retried"] = True
        st.rerun()

    if not token:
        return None'''

content = content.replace(old, new)

with open("session_persistence.py", "w") as f:
    f.write(content)

print("Patched cookie sync fix.")
