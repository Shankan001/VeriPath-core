with open("auth.py", "r") as f:
    content = f.read()

old_signature = '''def register_user(username: str, password: str,
                  full_name: str, company: str,
                  role: str = "exporter",
                  invite_code: str = "",
                  module: str = "🌿 VeriPath Crops") -> tuple[bool, str]:'''

new_signature = '''def register_user(username: str, password: str,
                  full_name: str, company: str,
                  role: str = "exporter",
                  invite_code: str = "",
                  module: str = "🌿 VeriPath Crops",
                  phone: str = "") -> tuple[bool, str]:'''

content = content.replace(old_signature, new_signature)

old_phone_check = '''    full_name = full_name.strip()[:100]
    if not full_name:
        return False, "Full name is required."'''

new_phone_check = '''    full_name = full_name.strip()[:100]
    if not full_name:
        return False, "Full name is required."
    from phone_utils import normalize_kenyan_phone
    normalized_phone = normalize_kenyan_phone(phone)
    if not normalized_phone:
        return False, "A valid phone number is required (e.g. 07XXXXXXXX)."'''

content = content.replace(old_phone_check, new_phone_check)

old_save = '''        "invite_code_used":  invite_code.strip().upper(),
        "subscription_tier": "trial",
        "containers_used":   0,
    })'''

new_save = '''        "invite_code_used":  invite_code.strip().upper(),
        "subscription_tier": "trial",
        "containers_used":   0,
        "phone":             normalized_phone,
    })'''

if old_save not in content:
    print("ERROR: save block not found — no changes made.")
else:
    content = content.replace(old_save, new_save)
    with open("auth.py", "w") as f:
        f.write(content)
    print("Patched register_user to accept, validate, and store normalized phone.")
