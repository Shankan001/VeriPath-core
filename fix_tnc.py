with open("app.py","r") as f:
    content = f.read()

old = '''            invite_code = st.text_input("Invite Code *", placeholder="VP-EXP-XXXX")
            password  = st.text_input("Password *",         type="password", placeholder="Min. 8 characters")
            password2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
            submit    = st.form_submit_button("Create Account →", use_container_width=True)
        if submit:
            errors = []
            if not full_name.strip():   errors.append("Full Name is required")
            if not username.strip():    errors.append("Username is required")
            if not company.strip():     errors.append("Company is required")
            if not invite_code.strip(): errors.append("Invite code is required")
            if not password:            errors.append("Password is required")
            if password != password2:   errors.append("Passwords do not match")'''

new = '''            invite_code = st.text_input("Invite Code *", placeholder="VP-EXP-XXXX")
            password  = st.text_input("Password *",         type="password", placeholder="Min. 8 characters")
            password2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
            st.markdown("""
            <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                        padding:12px 16px;margin:8px 0;font-size:0.82rem;color:#94a3b8'>
                By registering, you agree to VeriPath Africa\'s
                <a href='https://github.com/Shankan001/VeriPath-core/blob/main/docs/VeriPath_Terms_Conditions.pdf'
                   target='_blank' style='color:#38bdf8;text-decoration:underline'>
                   Terms &amp; Conditions
                </a>.
            </div>
            """, unsafe_allow_html=True)
            agree_tnc = st.checkbox("I have read and agree to the Terms & Conditions *")
            submit    = st.form_submit_button("Create Account →", use_container_width=True)
        if submit:
            errors = []
            if not full_name.strip():   errors.append("Full Name is required")
            if not username.strip():    errors.append("Username is required")
            if not company.strip():     errors.append("Company is required")
            if not invite_code.strip(): errors.append("Invite code is required")
            if not password:            errors.append("Password is required")
            if password != password2:   errors.append("Passwords do not match")
            if not agree_tnc:           errors.append("You must agree to the Terms & Conditions")'''

if old in content:
    content = content.replace(old, new)
    print("✅ T&C checkbox added")
else:
    print("❌ Block not found")

with open("app.py","w") as f:
    f.write(content)
