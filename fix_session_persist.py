with open("packhouse.py","r") as f:
    content = f.read()

# On load — restore intake_rows from disk if session state is empty
old = '''    if "intake_rows" not in st.session_state:
        st.session_state.intake_rows = []'''

new = '''    if "intake_rows" not in st.session_state:
        # Restore from disk if app was refreshed mid-session
        _session_file = os.path.join("data", f"active_session_{company.replace(' ','_')}.json")
        if os.path.exists(_session_file):
            try:
                with open(_session_file) as _f:
                    _saved = json.load(_f)
                st.session_state.intake_rows = _saved.get("rows", [])
                if st.session_state.intake_rows:
                    st.info(f"♻️ Restored {len(st.session_state.intake_rows)} unsaved row(s) from your last session.")
            except:
                st.session_state.intake_rows = []
        else:
            st.session_state.intake_rows = []'''

if old in content:
    content = content.replace(old, new)
    print("✅ Session restore on refresh — added")
else:
    print("❌ intake_rows init block not found")

# On add row — save to disk
old2 = '''            st.session_state.intake_rows.append({
                "crop":      crop,
                "hs_code":   CROP_HS_CODES[crop],
                "weight_kg": weight_kg,
                "grade":     grade,
                "notes":     notes,
                "eudr_risk": EUDR_RISK.get(crop,"GREEN"),
            })
            st.rerun()'''

new2 = '''            st.session_state.intake_rows.append({
                "crop":      crop,
                "hs_code":   CROP_HS_CODES[crop],
                "weight_kg": weight_kg,
                "grade":     grade,
                "notes":     notes,
                "eudr_risk": EUDR_RISK.get(crop,"GREEN"),
            })
            # Persist to disk so refresh doesn't lose data
            _session_file = os.path.join("data", f"active_session_{company.replace(' ','_')}.json")
            os.makedirs("data", exist_ok=True)
            with open(_session_file,"w") as _f:
                json.dump({"rows": st.session_state.intake_rows}, _f)
            st.rerun()'''

if old2 in content:
    content = content.replace(old2, new2)
    print("✅ Session saved to disk on every row add")
else:
    print("❌ Row append block not found")

# On save session — clear the disk session
old3 = '''                st.success(f"✅ {len(st.session_state.intake_rows)} rows saved — **{session_id}**")
                st.balloons()
                st.session_state.intake_rows = []
                st.rerun()'''

new3 = '''                st.success(f"✅ {len(st.session_state.intake_rows)} rows saved — **{session_id}**")
                st.balloons()
                st.session_state.intake_rows = []
                # Clear disk session after successful save
                _session_file = os.path.join("data", f"active_session_{company.replace(' ','_')}.json")
                if os.path.exists(_session_file):
                    os.remove(_session_file)
                st.rerun()'''

if old3 in content:
    content = content.replace(old3, new3)
    print("✅ Disk session cleared after save")
else:
    print("❌ Save success block not found")

with open("packhouse.py","w") as f:
    f.write(content)
