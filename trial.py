import os
from datetime import datetime, timedelta, timezone
from supabase_db import (
    get_company, ensure_company, update_company_tier,
    increment_company_containers, list_companies,
    load_users
)

WHATSAPP_NUMBER = "254796130512"
TRIAL_DAYS      = 14

PRICING_TIERS = {
    "crops": {
        "Starter": {
            "price_kes":     0,
            "container_cap": 5,
            "desc":          "Up to 5 consignments/month",
            "color":         "#334155",
        },
        "Growth": {
            "price_kes":     0,
            "container_cap": 10,
            "desc":          "Up to 10 consignments/month",
            "color":         "#0369a1",
        },
        "Enterprise": {
            "price_kes":     0,
            "container_cap": 50,
            "desc":          "Up to 50 consignments/month",
            "color":         "#7c3aed",
        },
        "Green Channel": {
            "price_kes":     0,
            "container_cap": 9_999,
            "desc":          "Unlimited + IoT + Priority Port Lane",
            "color":         "#16a34a",
        },
    },
    "livestock": {
        "Smallholder": {
            "price_kes":     0,
            "container_cap": 10,
            "desc":          "Up to 10 animals",
            "color":         "#334155",
        },
        "Herd": {
            "price_kes":     0,
            "container_cap": 50,
            "desc":          "Up to 50 animals",
            "color":         "#0369a1",
        },
        "Ranch": {
            "price_kes":     0,
            "container_cap": 200,
            "desc":          "Up to 200 animals",
            "color":         "#7c3aed",
        },
        "Enterprise": {
            "price_kes":     0,
            "container_cap": 9_999,
            "desc":          "Unlimited animals + full IoT",
            "color":         "#16a34a",
        },
    },
}

# Flat merged dict for backward compatibility
_ALL_TIERS = {**PRICING_TIERS["crops"], **PRICING_TIERS["livestock"]}

def _get_company_module(company_name: str) -> str:
    """Determine a company's module by checking any of its users' module field."""
    try:
        from supabase_db import get_client
        rows = get_client().table("users").select("module").eq(
            "company", company_name
        ).limit(1).execute().data
        if rows and rows[0].get("module"):
            return "livestock" if "Livestock" in rows[0]["module"] else "crops"
    except Exception:
        pass
    return "crops"


def _get_module(username: str) -> str:
    """Detect module from user profile."""
    try:
        from supabase_db import get_user
        user = get_user(username)
        if not user:
            return "crops"
        module = user.get("module","🌿 VeriPath Crops")
        return "livestock" if "Livestock" in module else "crops"
    except Exception:
        return "crops"

def _count_livestock(company: str) -> int:
    """Count active animals for company."""
    try:
        from supabase_db import get_client
        res = (get_client().table("animals")
               .select("id", count="exact")
               .eq("company", company)
               .eq("status", "active")
               .execute())
        return res.count or 0
    except Exception:
        return 0

def get_trial_status(username: str, module: str = None) -> dict:
    from supabase_db import get_user
    user = get_user(username)
    if not user:
        return _empty_status()

    role         = user.get("role","exporter")
    company_name = user.get("company","")
    rec          = ensure_company(company_name, user.get("created_at"))
    if not rec:
        return _empty_status()

    # Auto-detect module if not passed
    if module is None:
        mod_str = user.get("module","🌿 VeriPath Crops")
        module  = "livestock" if "Livestock" in mod_str else "crops"

    tier = rec.get("subscription_tier","trial")
    now  = datetime.now(timezone.utc)

    # Get container count based on module
    if module == "livestock":
        containers_used = _count_livestock(company_name)
        unit_label      = "animals"
        trial_cap       = 3
    else:
        containers_used = rec.get("containers_used", 0)
        unit_label      = "consignments"
        trial_cap       = 3

    if tier != "trial":
        expires_str = rec.get("tier_expires_at")
        if expires_str:
            try:
                expires_dt = datetime.fromisoformat(str(expires_str))
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                if now > expires_dt:
                    tier = "expired_paid"
            except Exception:
                pass
        cap = _ALL_TIERS.get(tier, {}).get("container_cap", 9_999)
        return {
            "is_trial":        False,
            "is_expired":      tier == "expired_paid",
            "is_warning":      False,
            "days_remaining":  None,
            "expiry_date":     str(expires_str)[:10] if expires_str else "—",
            "tier":            tier,
            "container_cap":   cap,
            "containers_used": containers_used,
            "unit_label":      unit_label,
            "overage":         containers_used >= cap and cap < 9_999,
            "company_name":    rec.get("company_name", company_name),
            "role":            role,
            "module":          module,
        }

    trial_start = rec.get("trial_started_at", now.isoformat())
    try:
        start_dt = datetime.fromisoformat(str(trial_start))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
    except Exception:
        start_dt = now

    expiry_dt = start_dt + timedelta(days=TRIAL_DAYS)
    delta     = expiry_dt - now
    days_left = max(0, delta.days)

    return {
        "is_trial":        True,
        "is_expired":      days_left == 0,
        "is_warning":      0 < days_left <= 4,
        "days_remaining":  days_left,
        "expiry_date":     expiry_dt.strftime("%d %b %Y"),
        "tier":            "trial",
        "container_cap":   trial_cap,
        "containers_used": containers_used,
        "unit_label":      unit_label,
        "overage":         False,
        "company_name":    rec.get("company_name", company_name),
        "role":            role,
        "module":          module,
    }

def _empty_status(module: str = "crops") -> dict:
    return {
        "is_trial": True, "is_expired": False, "is_warning": False,
        "days_remaining": 14, "expiry_date": "—", "tier": "trial",
        "container_cap": 3, "containers_used": 0,
        "unit_label": "consignments" if module == "crops" else "animals",
        "overage": False, "company_name": "—", "role": "exporter",
        "module": module,
    }

def set_company_subscription(company_name: str, tier: str,
                              months: int = 1) -> bool:
    if tier not in _ALL_TIERS:
        return False
    now        = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=30 * months)).isoformat()
    return update_company_tier(company_name, tier, expires_at)

def list_all_companies(exporters_only: bool = False) -> list[dict]:
    return list_companies(exporters_only=exporters_only)

def _slugify_tier_name(name: str) -> str:
    return name.lower().replace(" ", "_")


def get_module_tiers(module: str = "crops") -> dict:
    """
    Returns PRICING_TIERS for the given module, with price_kes overridden
    by live values from platform_settings (admin-editable), falling back
    to the hardcoded default if a setting row is missing.
    """
    base_tiers = PRICING_TIERS.get(module, PRICING_TIERS["crops"])
    try:
        from supabase_db import get_client
        rows = get_client().table("platform_settings").select(
            "setting_key, setting_value"
        ).execute().data
        price_lookup = {r["setting_key"]: r["setting_value"] for r in rows}
    except Exception:
        price_lookup = {}

    result = {}
    for tier_name, tier_data in base_tiers.items():
        key = f"price_{module}_{_slugify_tier_name(tier_name)}_kes"
        live_price = price_lookup.get(key)
        merged = dict(tier_data)
        if live_price is not None:
            try:
                merged["price_kes"] = float(live_price)
            except (ValueError, TypeError):
                pass  # keep hardcoded default if the stored value is invalid
        result[tier_name] = merged
    return result

def render_trial_banner(username: str, role: str = "exporter", module: str = None):
    import streamlit as st
    if role == "admin":
        return
    if module is None:
        module = _get_module(username)
    status = get_trial_status(username, module=module)

    if status["is_expired"]:
        label = "TRIAL EXPIRED" if status["is_trial"] else "SUBSCRIPTION EXPIRED"
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #dc2626;border-radius:14px;
                    padding:28px 24px;margin-bottom:24px;text-align:center'>
            <div style='font-size:1.4rem;font-weight:700;color:#f87171;
                        font-family:Space Mono,monospace'>🔒 {label}</div>
            <div style='color:#94a3b8;margin-top:8px;font-size:0.95rem'>
                Access for <b style='color:#e8eaf0'>{status["company_name"]}</b>
                expired on <b style='color:#e8eaf0'>{status["expiry_date"]}</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        _render_pricing_tiers(module)
        _render_whatsapp_button(status["company_name"])
        st.stop()

    if status["is_warning"]:
        d = status["days_remaining"]
        st.markdown(f"""
        <div style='background:#1c1400;border:2px solid #d97706;border-radius:12px;
                    padding:14px 20px;margin-bottom:20px;display:flex;
                    align-items:center;gap:16px'>
            <div style='font-size:1.5rem'>⚠</div>
            <div>
                <b style='color:#fbbf24;font-family:Space Mono,monospace'>
                    {d} DAY{"S" if d!=1 else ""} LEFT — {status["company_name"].upper()}
                </b><br>
                <span style='color:#94a3b8;font-size:0.85rem'>
                    Trial expires {status["expiry_date"]}.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif status["is_trial"]:
        unit = status["unit_label"]
        st.markdown(f"""
        <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:10px;
                    padding:10px 16px;margin-bottom:16px;display:flex;
                    justify-content:space-between;align-items:center'>
            <span style='color:#38bdf8;font-family:Space Mono,monospace;font-size:0.8rem'>
                🕐 TRIAL — {status["days_remaining"]} days left
                · {status["company_name"]}
            </span>
            <span style='color:#64748b;font-size:0.75rem'>
                Expires {status["expiry_date"]}
            </span>
        </div>
        """, unsafe_allow_html=True)

    if status["overage"]:
        unit = status["unit_label"]
        st.markdown(f"""
        <div style='background:#1a0a0a;border:1px solid #dc2626;border-radius:10px;
                    padding:14px 18px;margin-bottom:16px'>
            <b style='color:#f87171'>🚨 {unit.upper()} LIMIT REACHED</b><br>
            <span style='color:#94a3b8;font-size:0.85rem'>
                {status["containers_used"]} / {status["container_cap"]} {unit} used
                on <b style='color:#e8eaf0'>{status["tier"]}</b> plan.
            </span>
        </div>
        """, unsafe_allow_html=True)
        _render_whatsapp_button(status["company_name"])

def render_container_tracker(username: str, module: str = None,
                              role: str = None):
    import streamlit as st
    if role == "admin":
        return
    if module is None:
        module = _get_module(username)
    status = get_trial_status(username, module=module)
    if status.get("tier") in ("admin","Admin"):
        return
    used      = status["containers_used"]
    cap       = status["container_cap"]
    tier      = status["tier"]
    unit      = status["unit_label"]
    cap_label = "∞" if cap >= 9_999 else str(cap)
    pct       = min(100, int(used/cap*100)) if cap < 9_999 and cap > 0 else 0
    color     = "#dc2626" if pct >= 90 else "#d97706" if pct >= 70 else "#16a34a"
    label     = "Trial Usage" if tier == "trial" else f"{tier} Plan"

    # Module icon
    mod_icon = "🐄" if module == "livestock" else "🌿"

    st.sidebar.markdown(f"""
    <div style='background:#0d1224;border:1px solid #1e3a5f;border-radius:8px;
                padding:10px 12px;margin-top:8px'>
        <div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;
                    text-transform:uppercase;letter-spacing:0.08em'>
            {mod_icon} {label}
        </div>
        <div style='margin:6px 0 4px;background:#1e2d45;border-radius:4px;height:6px'>
            <div style='width:{pct}%;background:{color};height:6px;
                        border-radius:4px'></div>
        </div>
        <div style='font-size:0.75rem;color:#94a3b8'>
            {used} / {cap_label} {unit}
        </div>
    </div>
    """, unsafe_allow_html=True)

def _render_pricing_tiers(module: str = "crops"):
    import streamlit as st
    tiers = get_module_tiers(module)
    unit  = "animals" if module == "livestock" else "consignments"
    st.markdown(f"### 💳 Choose Your Plan")
    st.markdown(
        f"<small style='color:#64748b'>Prices set by admin. "
        f"Contact VeriPath to activate.</small>",
        unsafe_allow_html=True
    )
    cols = st.columns(len(tiers))
    for i, (name, info) in enumerate(tiers.items()):
        with cols[i]:
            cap_label = "Unlimited" if info["container_cap"] >= 9_999 else str(info["container_cap"])
            price_str = (f"KES {info['price_kes']:,}"
                         if info["price_kes"] > 0 else "Contact us")
            st.markdown(f"""
            <div style='background:#0d1224;border:2px solid {info["color"]};
                        border-radius:14px;padding:20px 16px;text-align:center'>
                <div style='font-family:Space Mono,monospace;font-size:0.85rem;
                            color:{info["color"]};font-weight:700'>{name.upper()}</div>
                <div style='font-size:1.4rem;font-weight:700;
                            color:#e8eaf0;margin:10px 0'>{price_str}</div>
                <div style='color:#64748b;font-size:0.75rem'>/month</div>
                <div style='color:#94a3b8;font-size:0.78rem;margin-top:8px'>
                    {cap_label} {unit}
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
           style='background:#16a34a;color:white;padding:14px 32px;
                  border-radius:10px;font-family:Space Mono,monospace;
                  font-size:0.9rem;font-weight:700;text-decoration:none;
                  display:inline-block'>
            📱 UPGRADE VIA WHATSAPP
        </a>
        <div style='color:#64748b;font-size:0.75rem;margin-top:8px'>
            +254 796 130 512
        </div>
    </div>
    """, unsafe_allow_html=True)
