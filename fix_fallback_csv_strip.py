with open("app.py", "r") as f:
    content = f.read()

old = '''                _batch_ref = f"{st.session_state.get('audit_result',{}).get('run_at','')[:10]}_{profile.get('company','')}"
                for _r in all_results:
                    _r["batch_reference"] = _batch_ref
                save_transmission_log_db(all_results, company=profile.get("company",""))'''

new = '''                _batch_ref = f"{st.session_state.get('audit_result',{}).get('run_at','')[:10]}_{profile.get('company','')}"
                _clean_results = [
                    {k: v for k, v in _r.items() if k != "fallback_csv"} | {"batch_reference": _batch_ref}
                    for _r in all_results
                ]
                save_transmission_log_db(_clean_results, company=profile.get("company",""))'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — fallback_csv now stripped before saving to transmission_log.")
