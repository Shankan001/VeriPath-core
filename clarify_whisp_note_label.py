with open("eudr.py", "r") as f:
    content = f.read()

old = '''                {f"<div style='color:#94a3b8;font-size:0.85rem;margin-top:8px;padding-top:8px;border-top:1px solid #ffffff22'>{whisp_supporting_note}</div>" if whisp_supporting_note else ""}'''

new = '''                {f"<div style='color:#94a3b8;font-size:0.85rem;margin-top:8px;padding-top:8px;border-top:1px solid #ffffff22'><b>Satellite check (informational — does not override overall status):</b> {whisp_supporting_note}</div>" if whisp_supporting_note else ""}'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("eudr.py", "w") as f:
        f.write(content)
    print("Clarified the supporting note label.")
