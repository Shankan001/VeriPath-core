with open("app.py", "r") as f:
    content = f.read()

old = "render_trial_banner(profile[\"username\"])"
new = "render_trial_banner(profile[\"username\"], role=profile.get(\"role\", \"exporter\"))"

if old in content:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("✅ app.py patched — role passed to trial banner")
else:
    print("❌ render_trial_banner call not found — paste line from app.py")
