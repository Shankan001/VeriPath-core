import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timezone
from supabase_db import get_client
from security import sanitize_text, check_rate_limit, log_security_event

SUPPORT_WHATSAPP = "254796130512"  # Joseph's number — update when dedicated line ready

CATEGORIES = [
    "🐛 Bug / something broken",
    "❓ How do I...",
    "💳 Billing / subscription",
    "🔧 Hardware issue (collar/bolus)",
    "📋 Data correction needed",
    "💡 Feature request",
    "🤝 Partnership inquiry",
    "📋 Other",
]

def _client():
    return get_client()

def save_ticket(record: dict) -> bool:
    try:
        _client().table("support_tickets").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to submit: {e}")
        return False

def load_tickets(status: str = None) -> list[dict]:
    try:
        q = _client().table("support_tickets").select("*")
        if status:
            q = q.eq("status", status)
        res = q.order("submitted_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def update_ticket(ticket_id: int, status: str, notes: str = "") -> bool:
    try:
        update = {"status": status}
        if status == "resolved":
            update["resolved_at"] = datetime.now(timezone.utc).isoformat()
        if notes:
            update["admin_notes"] = notes
        _client().table("support_tickets").update(update).eq(
            "id", ticket_id
        ).execute()
        return True
    except Exception:
        return False

def _whatsapp_support_link(username: str, company: str, prefill: str = "") -> str:
    base_msg = f"Hi VeriPath, I need help. Username: {username} | Company: {company}"
    if prefill:
        base_msg += f" | {prefill}"
    msg = urllib.parse.quote(base_msg)
    return f"https://wa.me/{SUPPORT_WHATSAPP}?text={msg}"

def render_floating_support_button(profile: dict):
    """Call this once near the top of any page to show a floating WhatsApp button."""
    username = profile.get("username","")
    company  = profile.get("company","")
    link = _whatsapp_support_link(username, company)

    st.markdown(f"""
    <a href="{link}" target="_blank" style="
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #25d366;
        color: white;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        text-decoration: none;
        z-index: 9999;
    ">💬</a>
    """, unsafe_allow_html=True)

def render_support_page(profile: dict):
    username = profile.get("username","")
    company  = profile.get("company","")
    module   = profile.get("module","🌿 VeriPath Crops")
    role     = profile.get("role","")

    st.markdown("# 🆘 Support")
    st.markdown(
        "<p style='color:#64748b'>Get help fast — WhatsApp or submit a ticket</p>",
        unsafe_allow_html=True
    )

    # ── Quick WhatsApp card ────────────────────────────────────────────
    wa_link = _whatsapp_support_link(username, company)
    st.markdown(f"""
    <div style='background:#071a0f;border:2px solid #25d366;border-radius:16px;
                padding:24px;text-align:center;margin-bottom:24px'>
        <div style='font-size:2rem'>💬</div>
        <div style='font-family:Space Mono,monospace;color:#4ade80;
                    font-size:1.1rem;font-weight:700;margin:8px 0'>
            NEED HELP RIGHT NOW?
        </div>
        <div style='color:#94a3b8;font-size:0.85rem;margin-bottom:16px'>
            Message us directly on WhatsApp — fastest response
        </div>
        <a href="{wa_link}" target="_blank" style="
            background:#25d366;color:white;padding:14px 32px;
            border-radius:10px;font-family:Space Mono,monospace;
            font-size:0.9rem;font-weight:700;text-decoration:none;
            display:inline-block">
            💬 Chat on WhatsApp
        </a>
        <div style='color:#64748b;font-size:0.75rem;margin-top:10px'>
            +254 796 130 512
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if role == "admin":
        tab_submit, tab_manage = st.tabs(["📝 Submit Ticket", "🎫 Manage Tickets"])
    else:
        tab_submit = st.container()
        tab_manage = None

    # ── Submit ticket form ─────────────────────────────────────────────
    with tab_submit:
        st.markdown("<div class='section-header'>SUBMIT A TICKET</div>",
                    unsafe_allow_html=True)
        st.markdown(
            "<small style='color:#64748b'>For non-urgent issues. "
            "We respond within 24 hours.</small>",
            unsafe_allow_html=True
        )

        with st.form("support_ticket_form"):
            category = st.selectbox("Category *", CATEGORIES)
            subject  = st.text_input(
                "Subject *",
                placeholder="Brief summary of your issue"
            )
            message  = st.text_area(
                "Details *",
                placeholder="Describe what's happening, what you expected, "
                           "and any error messages you saw...",
                height=150
            )
            priority = st.select_slider(
                "Priority",
                options=["Low","Normal","High","Urgent"],
                value="Normal"
            )
            submitted = st.form_submit_button(
                "📨 Submit Ticket", use_container_width=True, type="primary"
            )

        if submitted:
            if not subject.strip() or not message.strip():
                st.error("❌ Subject and details are required.")
            else:
                # ── Rate limit — max 5 tickets per 10 minutes per user ──
                rate_key = f"support_ticket:{username}"
                allowed, wait = check_rate_limit(
                    rate_key, max_attempts=5, window_seconds=600
                )
                if not allowed:
                    st.error(
                        f"❌ Too many tickets submitted. "
                        f"Please wait {wait} seconds before submitting again."
                    )
                    log_security_event(
                        "support_ticket_rate_limited", username,
                        f"Blocked for {wait}s", False
                    )
                else:
                    # ── Sanitize inputs ──────────────────────────────────
                    clean_subject = sanitize_text(subject, max_length=200)
                    clean_message = sanitize_text(message, max_length=2000)

                    if not clean_subject or not clean_message:
                        st.error(
                            "❌ Subject or message contained invalid content. "
                            "Please rephrase and try again."
                        )
                    else:
                        record = {
                            "username":     username,
                            "company":      sanitize_text(company, max_length=100),
                            "module":       module,
                            "category":     category,
                            "subject":      clean_subject,
                            "message":      clean_message,
                            "status":       "open",
                            "priority":     priority.lower(),
                            "submitted_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if save_ticket(record):
                            log_security_event(
                                "support_ticket_submitted", username,
                                f"Category: {category}", True
                            )
                            st.success(
                                "✅ Ticket submitted! We'll respond within 24 hours. "
                                "For urgent issues, use WhatsApp above."
                            )
                            st.balloons()

        # My tickets
        st.markdown("---")
        st.markdown("<div class='section-header'>MY TICKETS</div>",
                    unsafe_allow_html=True)
        try:
            res = (_client().table("support_tickets")
                   .select("*")
                   .eq("username", username)
                   .order("submitted_at", desc=True)
                   .execute())
            my_tickets = res.data or []
        except Exception:
            my_tickets = []

        if not my_tickets:
            st.info("No tickets submitted yet.")
        else:
            for t in my_tickets:
                status_color = {
                    "open":     "#d97706",
                    "in_progress": "#38bdf8",
                    "resolved": "#16a34a",
                }.get(t.get("status","open"), "#64748b")
                sub_date = t.get("submitted_at","")[:10]
                st.markdown(f"""
                <div style='background:#0d1224;border:1px solid {status_color};
                            border-radius:10px;padding:12px 16px;margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between'>
                        <span style='color:#e8eaf0;font-weight:600'>
                            {t.get("subject","—")}
                        </span>
                        <span style='color:{status_color};font-size:0.78rem;
                                     font-family:Space Mono,monospace'>
                            {t.get("status","open").upper()}
                        </span>
                    </div>
                    <div style='color:#64748b;font-size:0.78rem;margin-top:4px'>
                        {t.get("category","")} · {sub_date}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Admin: manage all tickets ──────────────────────────────────────
    if tab_manage is not None:
        with tab_manage:
            st.markdown("<div class='section-header'>ALL SUPPORT TICKETS</div>",
                        unsafe_allow_html=True)

            status_filter = st.selectbox(
                "Filter by status",
                ["All","open","in_progress","resolved"]
            )
            tickets = load_tickets(
                status=None if status_filter == "All" else status_filter
            )

            open_count = sum(1 for t in tickets if t.get("status")=="open")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>TOTAL TICKETS</div>
                <div class='metric-value'>{len(tickets)}</div>
            </div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>🟡 OPEN</div>
                <div class='metric-value' style='color:#d97706'>{open_count}</div>
            </div>""", unsafe_allow_html=True)
            urgent = sum(1 for t in tickets if t.get("priority")=="urgent")
            c3.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>🔴 URGENT</div>
                <div class='metric-value' style='color:#dc2626'>{urgent}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("---")

            if not tickets:
                st.info("No tickets found.")
                return

            for t in tickets:
                status_color = {
                    "open":        "#d97706",
                    "in_progress": "#38bdf8",
                    "resolved":    "#16a34a",
                }.get(t.get("status","open"), "#64748b")

                st.markdown(f"""
                <div style='background:#0d1224;border:1px solid {status_color};
                            border-radius:12px;padding:14px 18px;margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between'>
                        <span style='color:#e8eaf0;font-weight:700'>
                            {t.get("subject","—")}
                        </span>
                        <span style='color:{status_color};font-size:0.75rem;
                                     font-family:Space Mono,monospace'>
                            {t.get("status","open").upper()} ·
                            {t.get("priority","normal").upper()}
                        </span>
                    </div>
                    <div style='color:#64748b;font-size:0.78rem;margin-top:4px'>
                        {t.get("username","—")} · {t.get("company","—")} ·
                        {t.get("category","—")}
                    </div>
                    <div style='color:#94a3b8;font-size:0.85rem;margin-top:8px'>
                        {sanitize_text(t.get("message",""), max_length=200)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"Manage: {t.get('subject','—')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_status = st.selectbox(
                            "Status",
                            ["open","in_progress","resolved"],
                            index=["open","in_progress","resolved"].index(
                                t.get("status","open")
                            ),
                            key=f"status_{t['id']}"
                        )
                    with col2:
                        notes = st.text_input(
                            "Admin notes",
                            value=t.get("admin_notes","") or "",
                            key=f"notes_{t['id']}"
                        )
                    if st.button("💾 Update", key=f"update_{t['id']}"):
                        if update_ticket(t["id"], new_status, notes):
                            st.success("✅ Updated")
                            st.rerun()
