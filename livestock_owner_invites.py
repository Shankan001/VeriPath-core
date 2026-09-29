"""
livestock_owner_invites.py — lets a diaspora_owner generate invite codes
for their OWN workers (farm_manager, herdsman, or their own trusted vet),
always auto-scoped to their own company/farm identity. No manual company
entry, no checkbox — an owner can only ever invite people into their own
farm, by design.

Also shows the owner's current team with a deactivate/reactivate toggle —
deactivating only blocks future login; every record a worker already
logged stays exactly as it is, under their name.
"""

import streamlit as st
from invite_codes import generate_invite_code, load_invite_codes
from supabase_db import load_users, set_user_active

WORKER_ROLES = {
    "farm_manager": "Farm Manager",
    "herdsman": "Herdsman",
    "veterinarian": "My Trusted Vet",
}


def render_owner_invite(profile: dict):
    st.markdown("# 🔑 Invite My Team")
    st.markdown(
        "<p style='color:#64748b'>Generate invite codes for your own farm managers, "
        "herdsmen, or a trusted vet. They'll automatically be linked to your farm — "
        "nothing to configure.</p>",
        unsafe_allow_html=True,
    )

    company = profile.get("company", "")
    if not company:
        st.error("Your account has no farm identity set — contact support before inviting anyone.")
        return

    role_label = st.selectbox("Role to invite", list(WORKER_ROLES.values()))
    role_key = next(k for k, v in WORKER_ROLES.items() if v == role_label)

    if st.button("✅ Generate Code", use_container_width=True):
        code = generate_invite_code(role_key, created_by=profile["username"], target_company=company)
        st.success("New invite code generated:")
        st.code(code, language=None)
        st.markdown(
            f"<small style='color:#64748b'>Share this with your new {role_label.lower()} — "
            f"it links automatically to your farm.</small>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Codes you've generated")
    all_codes = load_invite_codes()
    mine = [c for c in all_codes.values() if c.get("created_by") == profile["username"]] \
        if isinstance(all_codes, dict) else \
        [c for c in all_codes if c.get("created_by") == profile["username"]]

    if not mine:
        st.info("You haven't generated any codes yet.")
    else:
        for c in mine:
            status = "✅ Used" if c.get("used") else "⏳ Unused"
            st.markdown(f"- `{c.get('code','?')}` — {c.get('role','?')} — {status}")

    st.markdown("---")
    st.markdown("### Your Team")

    all_users = load_users()
    company_lower = company.strip().lower()
    workers = [
        u for u in all_users.values()
        if u.get("company", "").strip().lower() == company_lower
        and u.get("role") in WORKER_ROLES.keys()
        and u.get("username") != profile["username"]
    ]

    if not workers:
        st.info("No farm managers, herdsmen, or vets on your team yet.")
    else:
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
                        &nbsp;· {WORKER_ROLES.get(u.get('role',''), u.get('role',''))} · @{u.get('username','')}
                    </span><br>
                    <span style='color:{status_color};font-size:0.78rem;font-family:Space Mono,monospace'>
                        ● {status_label}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            with col_action:
                btn_label = "🚫 Deactivate" if is_active else "✅ Reactivate"
                if st.button(btn_label, key=f"owner_toggle_{u['username']}", use_container_width=True):
                    if set_user_active(u["username"], not is_active):
                        st.success(f"{u['full_name']} {'deactivated' if is_active else 'reactivated'}.")
                        st.rerun()
                    else:
                        st.error("Failed to update status. Try again.")

        st.caption(
            "Deactivating blocks future login only — every record they "
            "already logged stays exactly as it is, under their name."
        )
