with open("app.py", "r") as f:
    content = f.read()

old_validation = '''                if not full_name.strip():              errors.append("Full Name is required")
                if not username.strip():               errors.append("Username is required")
                if not company.strip():                errors.append("Company is required")'''

new_validation = '''                if not full_name.strip():              errors.append("Full Name is required")
                if not username.strip():               errors.append("Username is required")
                if not phone.strip():                  errors.append("Phone number is required")
                if not company.strip():                errors.append("Company is required")'''

content = content.replace(old_validation, new_validation)

old_call = '''                    ok, msg = register_user(
                        username, password, full_name, company,
                        role, invite_code, module=selected_module
                    )'''

new_call = '''                    ok, msg = register_user(
                        username, password, full_name, company,
                        role, invite_code, module=selected_module, phone=phone
                    )'''

if old_call not in content:
    print("ERROR: register_user call not found — no changes made.")
else:
    content = content.replace(old_call, new_call)
    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — phone now validated and passed to register_user.")
