import json
import os
from datetime import datetime, timedelta

DATA_DIR   = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

WHATSAPP_NUMBER = "254796130512"

# ── Pricing Tiers (KES) ───────────────────────────────────────
PRICING_TIERS = {
    "Starter": {
        "price_kes":     2_500,
        "container_cap": 5,
        "desc":          "Up to 5 consignments/month",
        "color":         "#334155",
    },
    "Growth": {
        "price_kes":     7_500,
        "container_cap": 10,
        "desc":          "Up to 10 consignments/month",
        "color":         "#0369a1",
    },
    "Enterprise": {
        "price_kes":     18_000,
        "container_cap": 50,
        "desc":          "Up to 50 consignments/month",
        "color":         "#7c3aed",
    },
    "Green Channel": {
        "price_kes":     35_000,
        "container_cap": 9_999,
        "desc":          "Unlimited + IoT + Priority Port Lane",
        "color":         "#16a34a",
    },
}

TRIAL_DAYS = 14

def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_users(users: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_trial_status(username: str) -> dict:
    """
    Returns a dict with:
      - days_remaining (int)
      - is_expired (bool)
      - is_warning (bool)   → True when ≤ 4 days left (day 10+)
      - registered_at (str)
      - tier (str)          → current subscription tier
      - container_cap (int)
      - containers_used (int)
      - overage (bool)
    """
    users = _load_users()
    user  = users.get(username, {})

    registered_at = user.get("created_at", datetime.utcnow().isoformat())
    reg_dt        = datetime.fromisoformat(registered_at)
    expiry_dt     = reg_dt + timedelta(days=TRIAL_DAYS)
    now           = datetime.utcnow()
    delta         = expiry_dt - now
    days_left     = max(0, delta.days)

    tier          = user.get("subscription_tier", "trial")
    containers    = int(user.get("containers_used", 0))
    cap           = PRICING_TIERS.get(tier, {}).get("container_cap", 3) if tier != "trial" else 3

    return {
        "days_remaining":  days_left,
        "is_expired":      days_left == 0 and tier == "trial",
        "is_warning":      0 < days_left <= 4 and tier == "trial",
        "is_trial":        tier == "trial",
        "registered_at":   registered_at[:10],
        "expiry_date":     expiry_dt.strftime("%d %b %Y"),
        "tier":            tier,
        "container_cap":   cap,
        "containers_used": containers,
        "overage":         containers >= cap and tier != "trial",
    }

def increment_container_usage(username: str) -> int:
    """Bump the container count for a user. Returns new count."""
    users = _load_users()
    if username not in users:
        return 0
    current = int(users[username].get("containers_used", 0))
    users[username]["containers_used"] = current + 1
    _save_users(users)
    return current + 1

def set_subscription_tier(username: str, tier: str) -> bool:
    """Upgrade a user to a paid tier. Admin action."""
    if tier not in PRICING_TIERS:
        return False
    users = _load_users()
    if username not in users:
        return False
    users[username]["subscription_tier"] = tier
    users[username]["containers_used"]   = 0          # reset on upgrade
    users[username]["tier_set_at"]       = datetime.utcnow().isoformat()
    _save_users(users)
    return True

def reset_monthly_usage(username: str) -> None:
    """Call at billing cycle reset."""
    users = _load_users()
    if username in users:
        users[username]["containers_used"] = 0
        _save_users(users)

# ── Streamlit UI helpers ──────────────────────────────────────
def render_trial_banner(username: str, role: str = "exporter"):
    """
    Renders the appropriate banner inside a Streamlit page.
    Import and call at the top of app.py after auth.
    Admins are fully exempt from trial restrictions.
    """
    import streamlit as st

    # ── Admins see nothing ────────────────────────────────────
    if role == "admin":
        return

    status = get_trial_status(username)

    # ── EXPIRED LOCK ─────────────────────────────────────────
    if status["is_expired"]:
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:14px;
                    padding:28px 24px;margin-bottom:24px;text-align:center'>
            <div style='font-size:1.4rem;font-weight:700;color:#f87171;
                        font-family:Space Mono,monospace'>🔒 TRIAL EXPIRED</div>
            <div style='color:#94a3b8;margin-top:8px;font-size:0.95rem'>
                Your 14-day free trial ended on <b style='color:#e8eaf0'>{status["expiry_date"]}</b>.
                Upgrade to continue using VeriPath.
            </div>
        </div>
        """, unsafe_allow_html=True)
        _render_pricing_tiers()
        _render_whatsapp_button()
        st.stop()

    # ── WARNING BANNER (day 10–13) ────────────────────────────
    if status["is_warning"]:
        st.markdown(f"""
        <div style='background:#1c1400;border:2px solid #d97706;border-radius:12px;
                    padding:16px 20px;margin-bottom:20px;display:flex;
                    align-items:center;gap:16px'>
            <div style='font-size:1.5rem'>⚠️</div>
            <div>
                <b style='color:#fbbf24;font-family:Space Mono,monospace'>
                    {status["days_remaining"]} DAY{"S" if status["days_remaining"]!=1 else ""} LEFT IN TRIAL
                </b><br>
                <span style='color:#94a3b8;font-size:0.85rem'>
                    Trial expires {status["expiry_date"]}. 
                    Upgrade now to avoid losing access.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── NORMAL TRIAL BADGE ────────────────────────────────────
    elif status["is_trial"]:
        st.markdown(f"""
        <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:10px;
                    padding:10px 16px;margin-bottom:16px;display:flex;
                    justify-content:space-between;align-items:center'>
            <span style='color:#38bdf8;font-family:Space Mono,monospace;font-size:0.8rem'>
                🕐 TRIAL — {status["days_remaining"]} days remaining (expires {status["expiry_date"]})
            </span>
            <span style='color:#64748b;font-size:0.75rem'>3 consignment limit during trial</span>
        </div>
        """, unsafe_allow_html=True)

    # ── OVERAGE ALERT ─────────────────────────────────────────
    if status["overage"]:
        st.markdown(f"""
        <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:10px;
                    padding:14px 18px;margin-bottom:16px'>
            <b style='color:#f87171'>🚨 CONTAINER LIMIT REACHED</b><br>
            <span style='color:#94a3b8;font-size:0.85rem'>
                {status["containers_used"]} / {status["container_cap"]} used this month
                on your <b style='color:#e8eaf0'>{status["tier"]}</b> plan.
                Contact us to upgrade.
            </span>
        </div>
        """, unsafe_allow_html=True)
        _render_whatsapp_button()

def render_container_tracker(username: str):
    """Render a compact container usage widget in the sidebar."""
    import streamlit as st
    status = get_trial_status(username)
    if status["is_trial"]:
        used = status["containers_used"]
        cap  = 3
        pct  = min(100, int(used / cap * 100)) if cap else 0
        bar_color = "#dc2626" if pct >= 100 else "#d97706" if pct >= 66 else "#16a34a"
        st.sidebar.markdown(f"""
        <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                    padding:10px 12px;margin-top:8px'>
            <div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;
                        text-transform:uppercase;letter-spacing:0.08em'>Trial Usage</div>
            <div style='margin:6px 0 4px;background:#1e2d45;border-radius:4px;height:6px'>
                <div style='width:{pct}%;background:{bar_color};height:6px;
                             border-radius:4px;transition:width 0.3s'></div>
            </div>
            <div style='font-size:0.75rem;color:#94a3b8'>{used} / {cap} consignments</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        tier = status["tier"]
        used = status["containers_used"]
        cap  = status["container_cap"]
        cap_label = "∞" if cap >= 9999 else str(cap)
        pct  = min(100, int(used / cap * 100)) if cap < 9999 else 0
        bar_color = "#dc2626" if pct >= 90 else "#d97706" if pct >= 70 else "#16a34a"
        st.sidebar.markdown(f"""
        <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                    padding:10px 12px;margin-top:8px'>
            <div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;
                        text-transform:uppercase;letter-spacing:0.08em'>{tier} Plan</div>
            <div style='margin:6px 0 4px;background:#1e2d45;border-radius:4px;height:6px'>
                <div style='width:{pct}%;background:{bar_color};height:6px;
                             border-radius:4px;transition:width 0.3s'></div>
            </div>
            <div style='font-size:0.75rem;color:#94a3b8'>{used} / {cap_label} consignments</div>
        </div>
        """, unsafe_allow_html=True)

def _render_pricing_tiers():
    import streamlit as st
    st.markdown("### 💳 Choose Your Plan")
    cols = st.columns(len(PRICING_TIERS))
    for i, (name, info) in enumerate(PRICING_TIERS.items()):
        with cols[i]:
            cap_label = "Unlimited" if info["container_cap"] >= 9999 else str(info["container_cap"])
            st.markdown(f"""
            <div style='background:#0d1224;border:2px solid {info["color"]};border-radius:14px;
                        padding:20px 16px;text-align:center;height:180px'>
                <div style='font-family:Space Mono,monospace;font-size:0.85rem;
                             color:{info["color"]};font-weight:700'>{name.upper()}</div>
                <div style='font-size:1.4rem;font-weight:700;color:#e8eaf0;margin:10px 0'>
                    KES {info["price_kes"]:,}
                </div>
                <div style='color:#64748b;font-size:0.75rem'>/month</div>
                <div style='color:#94a3b8;font-size:0.78rem;margin-top:8px'>{info["desc"]}</div>
            </div>
            """, unsafe_allow_html=True)

def _render_whatsapp_button():
    import streamlit as st
    wa_msg  = "Hello+VeriPath,+I'd+like+to+upgrade+my+account."
    wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={wa_msg}"
    st.markdown(f"""
    <div style='text-align:center;margin-top:20px'>
        <a href="{wa_link}" target="_blank"
           style='background:#16a34a;color:white;padding:14px 32px;border-radius:10px;
                  font-family:Space Mono,monospace;font-size:0.9rem;font-weight:700;
                  text-decoration:none;display:inline-block;letter-spacing:0.05em'>
            📱 UPGRADE VIA WHATSAPP
        </a>
        <div style='color:#64748b;font-size:0.75rem;margin-top:8px'>
            WhatsApp: +254 796 130 512
        </div>
    </div>
    """, unsafe_allow_html=True)
