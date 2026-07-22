with open("eudr.py", "r") as f:
    content = f.read()

old = '''            st.markdown(f"""
            <div style='background:{bg};border:2px solid {border};border-radius:12px;padding:18px 22px;margin:14px 0'>
                <div style='font-size:1.4rem;font-weight:700;font-family:Space Mono,monospace;color:{color}'>{icon} {risk} — {result["risk_level"].upper()} RISK</div>
                <div style='color:#94a3b8;font-size:0.88rem;margin-top:8px'>{EUDR_RULES.get(crop, {}).get("reason", "")}</div>
                <div style='color:#e8eaf0;font-size:0.9rem;margin-top:10px'>⚡ <b>Required action:</b> {EUDR_RULES.get(crop, {}).get("action", "")}</div>
                {f"<div style='color:#94a3b8;font-size:0.85rem;margin-top:8px;padding-top:8px;border-top:1px solid #ffffff22'><b>Satellite check (informational — does not override overall status):</b> {whisp_supporting_note}</div>" if whisp_supporting_note else ""}
                <div style='color:#64748b;font-size:0.8rem;margin-top:8px'>EUDR Score: {result["score"]} / 3</div>
            </div>
            """, unsafe_allow_html=True)'''

new = '''            whisp_note_html = (
                f"<div style='color:#94a3b8;font-size:0.85rem;margin-top:8px;padding-top:8px;"
                f"border-top:1px solid #ffffff22'><b>Satellite check (informational — does not "
                f"override overall status):</b> {whisp_supporting_note}</div>"
            ) if whisp_supporting_note else ""

            card_html = (
                f"<div style='background:{bg};border:2px solid {border};border-radius:12px;padding:18px 22px;margin:14px 0'>"
                f"<div style='font-size:1.4rem;font-weight:700;font-family:Space Mono,monospace;color:{color}'>{icon} {risk} — {result['risk_level'].upper()} RISK</div>"
                f"<div style='color:#94a3b8;font-size:0.88rem;margin-top:8px'>{EUDR_RULES.get(crop, {}).get('reason', '')}</div>"
                f"<div style='color:#e8eaf0;font-size:0.9rem;margin-top:10px'>⚡ <b>Required action:</b> {EUDR_RULES.get(crop, {}).get('action', '')}</div>"
                f"{whisp_note_html}"
                f"<div style='color:#64748b;font-size:0.8rem;margin-top:8px'>EUDR Score: {result['score']} / 3</div>"
                f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("eudr.py", "w") as f:
        f.write(content)
    print("Fixed — HTML now built as a single-line string, no more blank-line code-block bug.")
