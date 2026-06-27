import streamlit as st
import pandas as pd
from invite_codes import generate_invite_code
from supabase_db import load_users
from ledger_db import load_farmers


def render_my_team(profile: dict):
    role    = profile.get("role", "")
    company = profile.get("company", "")
    username = profile.get("username", "")

    # ── RECORD KEEPER: farmer codes + own farmers only ────────────────────
    if role == "record_keeper":
        st.markdown("# My Farmers")
        st.caption("Generate VP-FAR invite codes for farmers and view the ones you registered.")
        st.markdown("---")
        st.markdown("### Generate Farmer Invite Code")

        if st.button("Generate VP-FAR Code", type="primary", use_container_width=True):
            code = generate_invite_code("farmer", created_by=username)
            st.session_state["rk_far_code"] = code
            st.rerun()

        if st.session_state.get("rk_far_code"):
            fc = st.session_state["rk_far_code"]
            st.code(fc, language=None)
            wa_link = f"https://wa.me/?text=Hello,+your+VeriPath+farmer+code+is:+{fc}"
            st.markdown(
                f"<a href='{wa_link}' target='_blank' style='"
                "background:#16a34a;color:white;padding:9px 20px;border-radius:7px;"
                "font-size:0.85rem;font-weight:700;text-decoration:none;"
                "display:inline-block;margin-top:6px'>Send via WhatsApp</a>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### Farmers You Registered")
        all_farmers = load_farmers(company)
        my_farmers  = {fid: f for fid, f in all_farmers.items()
                       if f.get("registered_by","") == username}
        if my_farmers:
            rows = []
            for fid, f in my_farmers.items():
                rows.append({
                    "ID":         fid,
                    "Name":       f["name"],
                    "County":     f["county"],
                    "Crops":      ", ".join(f.get("crops",[])),
                    "GPS":        f.get("gps","—"),
                    "Geo Status": f.get("geo_status","—"),
                    "Registered": f["registered_at"][:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("You have not registered any farmers yet.")

    # ── COMPLIANCE OFFICER: record keeper codes + RK list ────────────────
    elif role == "compliance_officer":
        st.markdown("# My Team")
        st.caption("Generate invite codes for record keepers in your company.")
        st.markdown("---")
        st.markdown("### Add Record Keeper")

        if st.button("Generate Record Keeper Code", type="primary", use_container_width=True):
            code = generate_invite_code("record_keeper", created_by=username)
            st.session_state["co_rk_code"] = code
            st.rerun()

        if st.session_state.get("co_rk_code"):
            rkc = st.session_state["co_rk_code"]
            st.code(rkc, language=None)
            wa_link = f"https://wa.me/?text=Hello,+your+VeriPath+record+keeper+code+is:+{rkc}"
            st.markdown(
                f"<a href='{wa_link}' target='_blank' style='"
                "background:#16a34a;color:white;padding:9px 20px;border-radius:7px;"
                "font-size:0.85rem;font-weight:700;text-decoration:none;"
                "display:inline-block;margin-top:6px'>Send via WhatsApp</a>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### Record Keepers")
        all_users     = load_users()
        company_lower = company.strip().lower()
        rks = [u for u in all_users.values()
               if u.get("company","").strip().lower() == company_lower
               and u.get("role") == "record_keeper"]
        if rks:
            st.dataframe(pd.DataFrame([{
                "Name":     u["full_name"],
                "Username": u["username"],
                "Joined":   u.get("created_at","")[:10],
            } for u in rks]), use_container_width=True, hide_index=True)
        else:
            st.info("No record keepers yet.")

    # ── EXPORTER / ADMIN: full team management ────────────────────────────
    elif role in ("exporter", "admin"):
        st.markdown("# My Team")
        st.caption("Manage your full team — record keepers, compliance officers, agronomists.")
        st.markdown("---")
        st.markdown("### Add Team Member")

        role_options = ["record_keeper", "compliance_officer", "agronomist"]
        role_labels  = {
            "record_keeper":      "Record Keeper",
            "compliance_officer": "Compliance Officer",
            "agronomist":         "Agronomist",
        }
        col_r, col_g = st.columns([2, 1])
        with col_r:
            team_role = st.selectbox("Role", role_options,
                                      format_func=lambda x: role_labels.get(x, x))
        with col_g:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Generate Code", type="primary", use_container_width=True):
                code = generate_invite_code(team_role, created_by=username)
                st.session_state["exp_team_code"] = code
                st.rerun()

        if st.session_state.get("exp_team_code"):
            ec = st.session_state["exp_team_code"]
            st.code(ec, language=None)
            wa_link = f"https://wa.me/?text=Hello,+your+VeriPath+invite+code+is:+{ec}"
            st.markdown(
                f"<a href='{wa_link}' target='_blank' style='"
                "background:#16a34a;color:white;padding:9px 20px;border-radius:7px;"
                "font-size:0.85rem;font-weight:700;text-decoration:none;"
                "display:inline-block;margin-top:6px'>Send via WhatsApp</a>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### Team Members")
        all_users     = load_users()
        company_lower = company.strip().lower()
        team = [u for u in all_users.values()
                if u.get("company","").strip().lower() == company_lower
                and u.get("role") in ("record_keeper","compliance_officer","agronomist")]
        if team:
            st.dataframe(pd.DataFrame([{
                "Name":     u["full_name"],
                "Role":     u["role"].replace("_"," ").title(),
                "Username": u["username"],
                "Joined":   u.get("created_at","")[:10],
            } for u in team]), use_container_width=True, hide_index=True)
        else:
            st.info("No team members yet.")

    else:
        st.error("Access restricted.")
        st.stop()
