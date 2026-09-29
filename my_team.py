import streamlit as st
import pandas as pd
from invite_codes import generate_invite_code
from supabase_db import load_users, set_user_active
from ledger_db import load_farmers

WORKER_ROLES = ("farm_manager", "herdsman", "veterinarian")


def _render_livestock_worker_management(viewer_username: str, company: str):
    """Shared list + deactivate/reactivate UI for farm_manager and admin
    (livestock mode). Records already logged by a deactivated worker are
    never touched — this only blocks future login."""
    st.markdown("### Team Members")
    all_users = load_users()
    company_lower = company.strip().lower()
    workers = [
        u for u in all_users.values()
        if u.get("company", "").strip().lower() == company_lower
        and u.get("role") in WORKER_ROLES
        and u.get("username") != viewer_username  # never deactivate yourself
    ]

    if not workers:
        st.info("No farm managers, herdsmen, or vets registered for this company yet.")
        return

    for u in workers:
        is_active = u.get("is_active", True)
        status_color = "#4ade80" if is_active else "#f87171"
        status_label = "Active" if is_active else "Deactivated"

        col_info, col_action = st.columns([3, 1])
        with col_info:
            st.markdown(f"""
            <div style='background:#111827;border:1px solid #1e3a5f;
                        border-radius:10px;padding:10px 16px;margin-bottom:6px'>
                <span style='color:#e8eaf0;font-weight:600'>{u.get('full_name','—')}</span>
                <span style='color:#64748b;font-size:0.8rem'>
                    &nbsp;· {u.get('role','').replace('_',' ').title()} · @{u.get('username','')}
                </span><br>
                <span style='color:{status_color};font-size:0.78rem;font-family:Space Mono,monospace'>
                    ● {status_label}
                </span>
            </div>
            """, unsafe_allow_html=True)
        with col_action:
            btn_label = "🚫 Deactivate" if is_active else "✅ Reactivate"
            if st.button(btn_label, key=f"toggle_{u['username']}", use_container_width=True):
                if set_user_active(u["username"], not is_active):
                    st.success(f"{u['full_name']} {'deactivated' if is_active else 'reactivated'}.")
                    st.rerun()
                else:
                    st.error("Failed to update status. Try again.")

    st.caption(
        "Deactivating blocks future login only — every weight, feed, cost, "
        "and milk record they already logged stays exactly as it is, under "
        "their name, as an audit trail."
    )


def render_my_team(profile: dict):
    role     = profile.get("role", "")
    company  = profile.get("company", "")
    username = profile.get("username", "")
    module   = profile.get("module", "")

    # ── ADMIN, LIVESTOCK MODULE: manage any company's workers ─────────────
    if role == "admin" and "Livestock" in module:
        st.markdown("# 👥 Team Management — Livestock")
        st.caption("Manage farm managers, herdsmen, and vets across any company.")
        st.markdown("---")

        all_users = load_users()
        companies_with_workers = sorted({
            u.get("company", "") for u in all_users.values()
            if u.get("role") in WORKER_ROLES and u.get("company")
        })
        if not companies_with_workers:
            st.info("No livestock companies with workers yet.")
            return

        selected_company = st.selectbox("Company", companies_with_workers)
        st.markdown("---")
        _render_livestock_worker_management(username, selected_company)
        return

    # ── FARM MANAGER: manage own company's workers ─────────────────────────
    if role == "farm_manager":
        st.markdown("# 👥 My Team")
        st.caption("Manage your farm's managers, herdsmen, and vets.")
        st.markdown("---")
        _render_livestock_worker_management(username, company)
        return

    # ── RECORD KEEPER: farmer codes + own farmers only ────────────────────
    if role == "record_keeper":
        st.markdown("# My Farmers")
        st.caption("Generate VP-FAR invite codes for farmers and view the ones you registered.")
        st.markdown("---")
        st.markdown("### Generate Farmer Invite Code")

        if st.button("Generate VP-FAR Code", type="primary", use_container_width=True):
            code = generate_invite_code("farmer", created_by=username, target_company=company)
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
        st.markdown("### Sign Up a Farmer On the Spot")
        st.caption("Met a farmer in the field? Generate their code right here.")

        if st.button("Generate VP-FAR Code", type="primary", use_container_width=True, key="co_far_btn"):
            far_code = generate_invite_code("farmer", created_by=username, target_company=company)
            st.session_state["co_far_code"] = far_code
            st.rerun()

        if st.session_state.get("co_far_code"):
            fc = st.session_state["co_far_code"]
            st.code(fc, language=None)
            wa_link2 = f"https://wa.me/?text=Hello,+your+VeriPath+farmer+code+is:+{fc}"
            st.markdown(
                f"<a href='{wa_link2}' target='_blank' style='"
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

    # ── EXPORTER / ADMIN (CROPS): full team management ────────────────────
    elif role in ("exporter", "admin"):
        st.markdown("# My Team")
        st.caption("Manage your full team — record keepers, compliance officers, agronomists.")
        st.markdown("---")
        st.markdown("### Add Team Member")

        role_options = ["record_keeper", "compliance_officer", "agronomist", "farmer"]
        role_labels  = {
            "record_keeper":      "Record Keeper",
            "compliance_officer": "Compliance Officer",
            "agronomist":         "Agronomist",
            "farmer":             "Farmer",
        }
        col_r, col_g = st.columns([2, 1])
        with col_r:
            team_role = st.selectbox("Role", role_options,
                                      format_func=lambda x: role_labels.get(x, x))
        with col_g:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Generate Code", type="primary", use_container_width=True):
                code = generate_invite_code(team_role, created_by=username, target_company=company)
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

    elif role == "agronomist":
        st.markdown("# My Farmers")
        st.caption("Generate VP-FAR invite codes for farmers you meet in the field.")
        st.markdown("---")
        st.markdown("### Generate Farmer Invite Code")

        if st.button("Generate VP-FAR Code", type="primary", use_container_width=True, key="agr_far_btn"):
            agr_code = generate_invite_code("farmer", created_by=username, target_company=company)
            st.session_state["agr_far_code"] = agr_code
            st.rerun()

        if st.session_state.get("agr_far_code"):
            afc = st.session_state["agr_far_code"]
            st.code(afc, language=None)
            wa_link3 = f"https://wa.me/?text=Hello,+your+VeriPath+farmer+code+is:+{afc}"
            st.markdown(
                f"<a href='{wa_link3}' target='_blank' style='"
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
    else:
        st.error("Access restricted.")
        st.stop()
