with open("app.py", "r") as f:
    content = f.read()

old = '''    if st.session_state["auth_page"] == "login":
        st.markdown("### Sign In to VeriPath")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="your username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit   = st.form_submit_button("Sign In →", use_container_width=True)
        if submit:'''

new = '''    if st.session_state["auth_page"] == "login":
        st.markdown("### Sign In to VeriPath")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="your username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit   = st.form_submit_button("Sign In →", use_container_width=True)

        with st.expander("🔒 Forgot your password?"):
            from password_reset import request_password_reset, verify_and_reset_password

            st.markdown("**Step 1: Request a reset code**")
            reset_username = st.text_input("Your username", key="reset_username_input")
            if st.button("📱 Send Reset Code via SMS", key="send_reset_code_btn"):
                if not reset_username.strip():
                    st.error("Please enter your username.")
                else:
                    ok, msg = request_password_reset(reset_username)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.markdown("---")
            st.markdown("**Step 2: Enter the code + new password**")
            reset_code = st.text_input("6-digit code from SMS", key="reset_code_input", max_chars=6)
            new_pw = st.text_input("New password", type="password", key="reset_new_pw",
                                    placeholder="Min. 10 chars · Upper · Lower · Number · Special (@#$!)")
            new_pw2 = st.text_input("Confirm new password", type="password", key="reset_new_pw2")
            if st.button("✅ Reset Password", key="confirm_reset_btn"):
                if not reset_username.strip() or not reset_code.strip():
                    st.error("Enter your username and the code sent to your phone.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = verify_and_reset_password(reset_username, reset_code, new_pw)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        if submit:'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("app.py", "w") as f:
        f.write(content)
    print("Added Forgot Password flow to sign-in screen.")
