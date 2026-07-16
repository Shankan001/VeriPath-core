with open("app.py", "r") as f:
    content = f.read()

old = '''                _clean_results = [
                    {k: v for k, v in _r.items() if k != "fallback_csv"} | {"batch_reference": _batch_ref}
                    for _r in all_results
                ]'''

new = '''                _allowed_keys = {"company", "consignment", "portal", "status", "message", "submitted_at"}
                _clean_results = [
                    {k: v for k, v in _r.items() if k in _allowed_keys} | {"batch_reference": _batch_ref}
                    for _r in all_results
                ]'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — now allow-listing exact table columns instead of block-listing one field at a time.")
