with open("app.py", "r") as f:
    content = f.read()

old = '''                    full_name = st.text_input("Full Name *", placeholder="Joseph Memusi")
                    username  = st.text_input("Username *",  placeholder="josephm")'''

new = '''                    full_name = st.text_input("Full Name *", placeholder="Joseph Memusi")
                    username  = st.text_input("Username *",  placeholder="josephm")
                    phone     = st.text_input("Phone Number *", placeholder="0712345678",
                                               help="Used for password reset via SMS.")'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Added phone field to registration form.")
