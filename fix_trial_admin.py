with open("trial.py", "r") as f:
    content = f.read()

old = '''def render_trial_banner(username: str):
    """
    Renders the appropriate banner inside a Streamlit page.
    Import and call at the top of app.py after auth.
    """
    import streamlit as st
    status = get_trial_status(username)

    # ── EXPIRED LOCK ─────────────────────────────────────────
    if status["is_expired"]:'''

new = '''def render_trial_banner(username: str, role: str = "exporter"):
    """
    Renders the appropriate banner inside a Streamlit page.
    Import and call at the top of app.py after auth.
    Admins are fully exempt from trial restrictions.
    """
    import streamlit as st

    # ── Admins see nothing ────────────────────────────────────
    if role == "admin":
        return

    status = get_trial_status(username)

    # ── EXPIRED LOCK ─────────────────────────────────────────
    if status["is_expired"]:'''

content = content.replace(old, new)

with open("trial.py", "w") as f:
    f.write(content)

print("✅ trial.py patched — admin exempt from trial banner")
