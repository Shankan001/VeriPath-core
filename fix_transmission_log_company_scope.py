with open("app.py", "r") as f:
    content = f.read()

# 1. Swap imports — use the real Supabase-backed, company-scoped functions
old_import = "from bridge_engine   import transmit_consignment, save_transmission_log, load_transmission_log, get_bridge_mode, get_credential_status, set_bridge_mode, set_portal_credentials, generate_kentrade_csv, generate_kephis_csv"
new_import = "from bridge_engine   import transmit_consignment, get_bridge_mode, get_credential_status, set_bridge_mode, set_portal_credentials, generate_kentrade_csv, generate_kephis_csv\nfrom supabase_db import save_transmission_log_db, load_transmission_log_db"

if old_import not in content:
    print("ERROR: import line not found — no changes made.")
else:
    content = content.replace(old_import, new_import)

    # 2. Tag each result with a batch_reference before saving, and use the
    # real company-scoped save function instead of the flat JSON file
    old_save = '''                save_transmission_log(all_results)'''
    new_save = '''                _batch_ref = f"{st.session_state.get('audit_result',{}).get('run_at','')[:10]}_{profile.get('company','')}"
                for _r in all_results:
                    _r["batch_reference"] = _batch_ref
                save_transmission_log_db(all_results, company=profile.get("company",""))'''
    content = content.replace(old_save, new_save)

    # 3. Load only this company's log, and group by batch in the display
    old_log_display = '''        log = load_transmission_log()
        if log:
            st.markdown("---")
            st.markdown("<div class='section-header'>TRANSMISSION LOG</div>",
                        unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(log), use_container_width=True)'''

    new_log_display = '''        log = load_transmission_log_db(company=profile.get("company",""))
        if log:
            st.markdown("---")
            st.markdown("<div class='section-header'>TRANSMISSION LOG</div>",
                        unsafe_allow_html=True)
            log_df = pd.DataFrame(log)
            if "batch_reference" in log_df.columns:
                batch_options = ["All Batches"] + sorted(
                    [b for b in log_df["batch_reference"].dropna().unique() if b], reverse=True
                )
                selected_batch = st.selectbox("Filter by batch", batch_options)
                if selected_batch != "All Batches":
                    log_df = log_df[log_df["batch_reference"] == selected_batch]
            st.dataframe(log_df, use_container_width=True)'''

    if old_log_display not in content:
        print("ERROR: log display block not found — import/save patched, but display not updated.")
    else:
        content = content.replace(old_log_display, new_log_display)

    with open("app.py", "w") as f:
        f.write(content)
    print("Patched — transmission log now company-scoped and batch-filterable.")
