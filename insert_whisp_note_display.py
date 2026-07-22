with open("eudr.py", "r") as f:
    lines = f.readlines()

target_line = '                <div style=\'color:#e8eaf0;font-size:0.9rem;margin-top:10px\'>⚡ <b>Required action:</b> {EUDR_RULES.get(crop, {}).get("action", "")}</div>\n'

insert_line = '                {f"<div style=\'color:#94a3b8;font-size:0.85rem;margin-top:8px;padding-top:8px;border-top:1px solid #ffffff22\'>{whisp_supporting_note}</div>" if whisp_supporting_note else ""}\n'

found = False
for i, line in enumerate(lines):
    if line == target_line:
        lines.insert(i + 1, insert_line)
        found = True
        break

if not found:
    print("ERROR: exact target line not found — no changes made.")
else:
    with open("eudr.py", "w") as f:
        f.writelines(lines)
    print("Inserted whisp_supporting_note display line.")
