import json
import os
from datetime import datetime, timedelta, timezone

DATA_DIR         = "data"
USERS_FILE       = os.path.join(DATA_DIR, "users.json")
COMPANIES_FILE   = os.path.join(DATA_DIR, "companies.json")
WHATSAPP_NUMBER  = "254796130512"
TRIAL_DAYS       = 14

PRICING_TIERS = {
    "Starter": {
        "price_kes":     2_500,
        "container_cap": 5,
        "desc":          "Up to 5 consignments/month",
        "color":         "#334155",
    },
    "Growth": {
        "price_kes":     20_000,
        "container_cap": 10,
        "desc":          "Up to 10 consignments/month",
        "color":         "#0369a1",
    },
    "Enterprise": {
        "price_kes":     65_000,
        "container_cap": 50,
        "desc":          "Up to 50 consignments/month",
        "color":         "#7c3aed",
    },
    "Green Channel": {
        "price_kes":     150_000,
        "container_cap": 9_999,
        "desc":          "Unlimited + IoT + Priority Port Lane",
        "color":         "#16a34a",
    },
}

# ── Company DB helpers ────────────────────────────────────────

def _load_companies() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(COMPANIES_FILE):
        return {}
    try:
        with open(COMPANIES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_companies(companies: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COMPANIES_FILE, "w") as f:
        json.dump(companies, f, indent=2)

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

def _normalize_company(name: str) -> str:
    return name.strip().lower()

# ── Company record bootstrap ──────────────────────────────────

def ensure_company_record(company_name: str, first_user_created_at: str = None) -> dict:
    """
    Create company record if it doesn't exist.
    Trial start = first user registration date under that company.
    """
    companies = _load_companies()
    key = _normalize_company(company_name)
    if key not in companies:
        start = first_user_created_at or datetime.now(timezone.utc).isoformat()
        companies[key] = {
            "company_name":       company_name.strip(),
            "subscription_tier":  "trial",
            "trial_started_at":   start,
            "tier_set_at":        None,
            "tier_expires_at":    None,
            "containers_used":    0,
        }
        _save_companies(companies)
    return companies[key]

def get_company_record(company_name: str) -> dict:
    companies = _load_companies()
    key = _normalize_company(company_name)
    return companies.get(key, None)

# ── Core status function ──────────────────────────────────────

def get_trial_status(username: str) -> dict:
    """
    Returns company-level subscription status for the given user.
    All users under the same company share one status.
    """
    users = _load_users()
    user  = users.get(username, {})
    role  = user.get("role", "exporter")
    company_name = user.get("company", username)

    # Ensure company record exists
    rec = ensure_company_record(company_name, user.get("created_at"))

    companies = _load_companies()
    key = _normalize_company(company_name)
    rec = companies[key]

    tier = rec.get("subscription_tier", "trial")
    now  = datetime.now(timezone.utc)

    # ── Paid tier — check expiry ──────────────────────────────
    if tier != "trial":
        expires_str = rec.get("tier_expires_at")
        if expires_str:
            expires_dt  = datetime.fromisoformat(expires_str)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if now > expires_dt:
                # Subscription lapsed — drop back to trial lock
                tier = "expired_paid"
        cap = PRICING_TIERS.get(tier, {}).get("container_cap", 9_999)
        return {
            "is_trial":        False,
            "is_expired":      tier == "expired_paid",
            "is_warning":      False,
            "days_remaining":  None,
            "expiry_date":     expires_str[:10] if expires_str else "—",
            "tier":            tier,
            "container_cap":   cap,
            "containers_used": rec.get("containers_used", 0),
            "overage":         rec.get("containers_used", 0) >= cap and cap < 9_999,
            "company_name":    rec["company_name"],
            "role":            role,
        }

    # ── Trial logic ───────────────────────────────────────────
    trial_start = rec.get("trial_started_at", now.isoformat())
    start_dt    = datetime.fromisoformat(trial_start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    expiry_dt   = start_dt + timedelta(days=TRIAL_DAYS)
    delta       = expiry_dt - now
    days_left   = max(0, delta.days)

    return {
        "is_trial":        True,
        "is_expired":      days_left == 0,
        "is_warning":      0 < days_left <= 4,
        "days_remaining":  days_left,
        "expiry_date":     expiry_dt.strftime("%d %b %Y"),
        "tier":            "trial",
        "container_cap":   3,
        "containers_used": rec.get("containers_used", 0),
        "overage":         False,
        "company_name":    rec["company_name"],
        "role":            role,
    }

# ── Upgrade company subscription ──────────────────────────────

def set_company_subscription(company_name: str, tier: str, months: int = 1) -> bool:
    """
    Upgrade entire company to a paid tier.
    All users under this company immediately get access.
    """
    if tier not in PRICING_TIERS:
        return False
    companies = _load_companies()
    key = _normalize_company(company_name)
    if key not in companies:
        ensure_company_record(company_name)
        companies = _load_companies()
    now        = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30 * months)
    companies[key]["subscription_tier"] = tier
    companies[key]["tier_set_at"]       = now.isoformat()
    companies[key]["tier_expires_at"]   = expires_at.isoformat()
    companies[key]["containers_used"]   = 0
    _save_companies(companies)
    return True

def increment_container_usage(company_name: str) -> int:
    """Bump consignment count for the company. Returns new total."""
    companies = _load_companies()
    key = _normalize_company(company_name)
    if key not in companies:
        return 0
    current = int(companies[key].get("containers_used", 0))
    companies[key]["containers_used"] = current + 1
    _save_companies(companies)
    return current + 1

def reset_monthly_usage(company_name: str) -> None:
    companies = _load_companies()
    key = _normalize_company(company_name)
    if key in companies:
        companies[key]["containers_used"] = 0
        _save_companies(companies)

def list_all_companies() -> list[dict]:
    companies = _load_companies()
    result = []
    for key, rec in companies.items():
        result.append({
            "Company":     rec.get("company_name", key),
            "Tier":        rec.get("subscription_tier", "trial"),
            "Trial Start": rec.get("trial_started_at", "")[:10],
            "Expires":     rec.get("tier_expires_at", "")[:10] if rec.get("tier_expires_at") else "—",
            "Containers":  rec.get("containers_used", 0),
        })
    return sorted(result, key=lambda x: x["Company"])

# ── Streamlit UI helpers ──────────────────────────────────────

def render_trial_banner(username: str, role: str = "exporter"):
    import streamlit as st

    # Admins never see trial wall
    if role == "admin":
        return

    status = get_trial_status(username)

    # ── EXPIRED / LAPSED ─────────────────────────────────────
    if status["is_expired"]:
        label = "TRIAL EXPIRED" if status["is_trial"] else "SUBSCRIPTION EXPIRED"
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:14px;
                    padding:28px 24px;margin-bottom:24px;text-align:center'>
            <div style='font-size:1.4rem;font-weight:700;color:#f87171;
                        font-family:Space Mono,monospace'>🔒 {label}</div>
            <div style='color:#94a3b8;margin-top:8px;font-size:0.95rem'>
                Access for <b style='color:#e8eaf0'>{status["company_name"]}</b>
                expired on <b style='color:#e8eaf0'>{status["expiry_date"]}</b>.<br>
                Contact your account manager to renew.
            </div>
        </div>
        """, unsafe_allow_html=True)
        _render_pricing_tiers()
        _render_whatsapp_button(status["company_name"])
        st.stop()

    # ── WARNING (4 days left) ─────────────────────────────────
    if status["is_warning"]:
        d = status["days_remaining"]
        st.markdown(f"""
        <div style='background:#1c1400;border:2px solid #d97706;border-radius:12px;
                    padding:14px 20px;margin-bottom:20px;display:flex;
                    align-items:center;gap:16px'>
            <div style='font-size:1.5rem'>⚠️</div>
            <div>
                <b style='color:#fbbf24;font-family:Space Mono,monospace'>
                    {d} DAY{"S" if d != 1 else ""} LEFT — {status["company_name"].upper()}
                </b><br>
                <span style='color:#94a3b8;font-size:0.85rem'>
                    Trial expires {status["expiry_date"]}. Upgrade to keep your team's access.
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
                🕐 TRIAL — {status["days_remaining"]} days left · {status["company_name"]}
            </span>
            <span style='color:#64748b;font-size:0.75rem'>
                Expires {status["expiry_date"]}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── OVERAGE ───────────────────────────────────────────────
    if status["overage"]:
        st.markdown(f"""
        <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:10px;
                    padding:14px 18px;margin-bottom:16px'>
            <b style='color:#f87171'>🚨 CONSIGNMENT LIMIT REACHED</b><br>
            <span style='color:#94a3b8;font-size:0.85rem'>
                {status["containers_used"]} / {status["container_cap"]} used this month
                on the <b style='color:#e8eaf0'>{status["tier"]}</b> plan.
                Contact us to upgrade.
            </span>
        </div>
        """, unsafe_allow_html=True)
        _render_whatsapp_button(status["company_name"])

def render_container_tracker(username: str):
    import streamlit as st
    status = get_trial_status(username)
    used   = status["containers_used"]
    cap    = status["container_cap"]
    tier   = status["tier"]
    cap_label = "∞" if cap >= 9_999 else str(cap)
    pct   = min(100, int(used / cap * 100)) if cap < 9_999 else 0
    color = "#dc2626" if pct >= 90 else "#d97706" if pct >= 70 else "#16a34a"
    label = "Trial Usage" if tier == "trial" else f"{tier} Plan"
    st.sidebar.markdown(f"""
    <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                padding:10px 12px;margin-top:8px'>
        <div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;
                    text-transform:uppercase;letter-spacing:0.08em'>{label}</div>
        <div style='margin:6px 0 4px;background:#1e2d45;border-radius:4px;height:6px'>
            <div style='width:{pct}%;background:{color};height:6px;
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
            cap_label = "Unlimited" if info["container_cap"] >= 9_999 else str(info["container_cap"])
            st.markdown(f"""
            <div style='background:#0d1224;border:2px solid {info["color"]};border-radius:14px;
                        padding:20px 16px;text-align:center'>
                <div style='font-family:Space Mono,monospace;font-size:0.85rem;
                             color:{info["color"]};font-weight:700'>{name.upper()}</div>
                <div style='font-size:1.4rem;font-weight:700;color:#e8eaf0;margin:10px 0'>
                    KES {info["price_kes"]:,}
                </div>
                <div style='color:#64748b;font-size:0.75rem'>/month</div>
                <div style='color:#94a3b8;font-size:0.78rem;margin-top:8px'>{info["desc"]}</div>
                <div style='color:#64748b;font-size:0.72rem;margin-top:4px'>
                    {cap_label} consignments
                </div>
            </div>
            """, unsafe_allow_html=True)

def _render_whatsapp_button(company_name: str = ""):
    import streamlit as st
    msg     = f"Hello+VeriPath,+{company_name.replace(' ','+')}+would+like+to+upgrade."
    wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={msg}"
    st.markdown(f"""
    <div style='text-align:center;margin-top:20px'>
        <a href="{wa_link}" target="_blank"
           style='background:#16a34a;color:white;padding:14px 32px;border-radius:10px;
                  font-family:Space Mono,monospace;font-size:0.9rem;font-weight:700;
                  text-decoration:none;display:inline-block;letter-spacing:0.05em'>
            📱 UPGRADE VIA WHATSAPP
        </a>
        <div style='color:#64748b;font-size:0.75rem;margin-top:8px'>
            +254 796 130 512
        </div>
    </div>
    """, unsafe_allow_html=True)
