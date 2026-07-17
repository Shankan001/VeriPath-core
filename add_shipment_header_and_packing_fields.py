with open("app.py") as f:
    src = f.read()

OLD = '''        approved       = st.session_state.get("approved_records", [])
        portal_options = st.multiselect(
            "Target portals",
            ["KenTrade","KEPHIS","AFA IMIS"],
            default=["KenTrade","KEPHIS","AFA IMIS"]
        )'''

NEW = '''        approved       = st.session_state.get("approved_records", [])

        # ── Shipment Header (once per batch) ────────────────────────────
        st.markdown("### 📦 Shipment Header")
        hdr_col1, hdr_col2, hdr_col3 = st.columns(3)
        with hdr_col1:
            consignee_name = st.text_input("Consignee Name", key="shipment_consignee_name")
        with hdr_col2:
            consignee_address = st.text_input("Consignee Address", key="shipment_consignee_address")
        with hdr_col3:
            point_of_exit = st.selectbox(
                "Point of Exit",
                ["JKIA - Nairobi", "Mombasa Port", "Namanga", "Busia", "Malaba"],
                key="shipment_point_of_exit"
            )

        header_complete = bool(
            consignee_name.strip() and consignee_address.strip() and point_of_exit
        )
        if approved and not header_complete:
            st.warning("⚠ Complete the Shipment Header above to enable submission.")

        # ── Per-record packing detail + HS-code hard block ───────────────
        if approved and header_complete:
            st.markdown("### 📋 Per-Record Packing Details")
            pkg_df = pd.DataFrame([
                {
                    "Consignment_ID":     r.get("session_id", "—"),
                    "Farmer_Name":        r.get("farmer_name", "—"),
                    "Crop":               r.get("crop", "—"),
                    "Weight_KG":          r.get("weight_kg", 0),
                    "Package_Type":       r.get("package_type", "Carton"),
                    "Number_of_Packages": r.get("number_of_packages", 1),
                }
                for r in approved
            ])
            edited_pkg_df = st.data_editor(
                pkg_df,
                column_config={
                    "Package_Type": st.column_config.SelectboxColumn(
                        "Package_Type", options=["Carton", "Crate", "Pallet", "Bag", "Box"]
                    ),
                    "Number_of_Packages": st.column_config.NumberColumn(
                        "Number_of_Packages", min_value=1, step=1
                    ),
                },
                disabled=["Consignment_ID", "Farmer_Name", "Crop", "Weight_KG"],
                use_container_width=True,
                hide_index=True,
                key="packing_editor",
            )
            pkg_lookup = edited_pkg_df.set_index("Consignment_ID").to_dict("index")
            enriched = [
                {
                    **r,
                    "consignee_name":     consignee_name.strip(),
                    "consignee_address":  consignee_address.strip(),
                    "point_of_exit":      point_of_exit,
                    "package_type":       pkg_lookup.get(r.get("session_id", "—"), {}).get("Package_Type", "Carton"),
                    "number_of_packages": pkg_lookup.get(r.get("session_id", "—"), {}).get("Number_of_Packages", 1),
                }
                for r in approved
            ]

            # HARD BLOCK: records missing hs_code cannot be transmitted, even if
            # they reached approved_records via the pre-audit "Override & Approve
            # Anyway" path (which bypasses REQUIRED_FIELDS). Clean records in the
            # same batch are unaffected.
            hs_missing = [r for r in enriched if not str(r.get("hs_code","")).strip()
                          or str(r.get("hs_code","")).strip().upper() == "UNKNOWN"]
            hs_ready   = [r for r in enriched if r not in hs_missing]

            if hs_missing:
                names = "\\n".join(
                    f"- {r.get('farmer_name','—')} · {r.get('crop','—')} · {r.get('session_id','—')}"
                    for r in hs_missing
                )
                st.error(f"🛑 {len(hs_missing)} record(s) BLOCKED — missing HS code:\\n\\n{names}")
                st.caption("These likely came through the pre-audit override path. Fix the HS code in the ledger and re-run pre-audit before resubmitting.")

            approved = hs_ready
        elif not header_complete:
            approved = []

        st.markdown("---")
        portal_options = st.multiselect(
            "Target portals",
            ["KenTrade","KEPHIS","AFA IMIS"],
            default=["KenTrade","KEPHIS","AFA IMIS"]
        )'''

assert OLD in src, "Anchor block not found in app.py"
assert src.count(OLD) == 1, "Anchor block is not unique — refusing to patch ambiguously"

src = src.replace(OLD, NEW)

with open("app.py", "w") as f:
    f.write(src)

print("✅ app.py patched.")
