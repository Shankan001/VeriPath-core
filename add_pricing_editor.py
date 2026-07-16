with open("kpi_dashboard.py", "r") as f:
    content = f.read()

anchor = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Upgrade Company Subscription</div>", unsafe_allow_html=True)'''

pricing_section = '''    st.markdown("<div style='font-family:Space Mono,monospace;font-size:0.75rem;"
                "color:#64748b;letter-spacing:0.1em;text-transform:uppercase;"
                "margin-bottom:12px'>Set Pricing</div>", unsafe_allow_html=True)

    from trial import get_module_tiers, PRICING_TIERS
    from supabase_db import get_client

    pricing_module_tab = st.radio("Module", ["Crops", "Livestock"], horizontal=True, key="pricing_module_tab")
    _pm = "crops" if pricing_module_tab == "Crops" else "livestock"
    _current_tiers = get_module_tiers(_pm)

    with st.form(f"pricing_form_{_pm}"):
        new_prices = {}
        cols = st.columns(len(_current_tiers))
        for i, (tier_name, tier_data) in enumerate(_current_tiers.items()):
            with cols[i]:
                new_prices[tier_name] = st.number_input(
                    f"{tier_name} (KES/mo)",
                    min_value=0,
                    value=int(tier_data.get("price_kes", 0)),
                    step=500,
                    key=f"price_{_pm}_{tier_name}"
                )
        if st.form_submit_button("💾 Save Pricing", use_container_width=True):
            def _slug(name):
                return name.lower().replace(" ", "_")
            for tier_name, value in new_prices.items():
                key = f"price_{_pm}_{_slug(tier_name)}_kes"
                get_client().table("platform_settings").upsert({
                    "setting_key": key,
                    "setting_value": str(value),
                    "updated_by": "admin",
                }, on_conflict="setting_key").execute()
            st.success(f"✅ {pricing_module_tab} pricing saved.")
            st.rerun()

    st.markdown("---")

''' + anchor

if anchor not in content:
    print("ERROR: anchor not found — no changes made.")
else:
    content = content.replace(anchor, pricing_section)
    with open("kpi_dashboard.py", "w") as f:
        f.write(content)
    print("Added pricing editor section.")
