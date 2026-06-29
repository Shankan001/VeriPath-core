"""
VeriPath Africa — Security Layer
Rate limiting · input sanitization · session hardening
"""

import re
import time
import hashlib
from datetime import datetime, timezone
from typing import Any

# ── Rate limiting (in-memory per session) ─────────────────────
_rate_store: dict = {}

def check_rate_limit(key: str, max_attempts: int = 5,
                     window_seconds: int = 300) -> tuple[bool, int]:
    """
    Returns (allowed, seconds_remaining).
    key = "login:{username}" or "register:{ip}"
    """
    now = time.time()
    if key not in _rate_store:
        _rate_store[key] = []

    # Clear old attempts outside window
    _rate_store[key] = [t for t in _rate_store[key]
                        if now - t < window_seconds]

    attempts = len(_rate_store[key])
    if attempts >= max_attempts:
        oldest    = _rate_store[key][0]
        remaining = int(window_seconds - (now - oldest))
        return False, remaining

    _rate_store[key].append(now)
    return True, 0

def reset_rate_limit(key: str) -> None:
    _rate_store.pop(key, None)

# ── Input sanitization ─────────────────────────────────────────
def sanitize_text(value: str, max_length: int = 255,
                  allow_spaces: bool = True) -> str:
    """Strip dangerous characters — prevent XSS and injection."""
    if not value:
        return ""
    # Remove null bytes
    value = value.replace("\x00","")
    # Remove HTML tags
    value = re.sub(r"<[^>]+>","", value)
    # Remove SQL injection patterns
    value = re.sub(
        r"(--|;|\/\*|\*\/|xp_|UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)",
        "", value, flags=re.IGNORECASE
    )
    # Strip leading/trailing whitespace
    value = value.strip()
    # Enforce max length
    return value[:max_length]

def sanitize_username(username: str) -> tuple[bool, str, str]:
    """
    Validate and sanitize username.
    Returns (valid, clean_username, error_message)
    """
    if not username:
        return False, "", "Username is required."
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "", username.strip().lower())
    if len(clean) < 3:
        return False, "", "Username must be at least 3 characters."
    if len(clean) > 50:
        return False, "", "Username must be under 50 characters."
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_\-]*$", clean):
        return False, "", "Username must start with a letter."
    return True, clean, ""

def sanitize_company(company: str) -> tuple[bool, str, str]:
    """Validate company name."""
    if not company:
        return False, "", "Company name is required."
    clean = sanitize_text(company, max_length=100)
    if len(clean) < 2:
        return False, "", "Company name too short."
    return True, clean, ""

def validate_kra_pin(pin: str) -> tuple[bool, str]:
    """Strict KRA PIN validation — A123456789B format."""
    if not pin:
        return False, "KRA PIN is required."
    pin = pin.strip().upper()
    if not re.match(r"^[A-Z]\d{9}[A-Z]$", pin):
        return False, f"Invalid KRA PIN format. Expected: A123456789B"
    return True, pin

def validate_invite_code(code: str) -> tuple[bool, str]:
    """Validate invite code format before DB lookup."""
    if not code:
        return False, "Invite code is required."
    code = code.strip().upper()
    if not re.match(r"^VP-[A-Z]{3}-[A-Z0-9]{4}$", code):
        return False, "Invalid code format. Expected: VP-XXX-XXXX"
    return True, code

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Enforce strong passwords."""
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password too long (max 128 characters)."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""

def validate_temperature(temp: float, species: str = "Goat") -> tuple[bool, str]:
    """Sanity check temperature readings — prevent garbage data."""
    limits = {
        "Goat":   (30.0, 45.0),
        "Cattle": (30.0, 45.0),
        "Sheep":  (30.0, 45.0),
    }
    lo, hi = limits.get(species, (30.0, 45.0))
    if temp < lo or temp > hi:
        return False, f"Temperature {temp}°C outside valid range ({lo}–{hi}°C)."
    return True, ""

def validate_phone_ke(phone: str) -> tuple[bool, str]:
    """Validate Kenyan phone number."""
    if not phone:
        return False, "Phone number required."
    clean = re.sub(r"[\s\-\+]", "", phone)
    if re.match(r"^(07|01)\d{8}$", clean):
        return True, "254" + clean[1:]
    if re.match(r"^254\d{9}$", clean):
        return True, clean
    return False, "Invalid Kenyan phone. Use 07XXXXXXXX or 254XXXXXXXXX."

# ── Session security ───────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = 480  # 8 hours

def check_session_timeout(login_time_iso: str) -> bool:
    """Returns True if session is still valid."""
    try:
        login_dt = datetime.fromisoformat(login_time_iso)
        if login_dt.tzinfo is None:
            login_dt = login_dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - login_dt).seconds / 60
        return elapsed < SESSION_TIMEOUT_MINUTES
    except Exception:
        return False

def generate_session_token(username: str) -> str:
    """Generate a session token for additional verification."""
    seed = f"{username}{time.time()}{datetime.now().isoformat()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

# ── Audit logging ──────────────────────────────────────────────
def log_security_event(event_type: str, username: str,
                       details: str = "", success: bool = True) -> None:
    """Log security events to Supabase."""
    try:
        from supabase_db import get_client
        get_client().table("security_audit_log").insert({
            "event_type": event_type,
            "username":   username,
            "details":    details,
            "success":    success,
            "logged_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Never let audit logging crash the app

# ── Content Security ───────────────────────────────────────────
def is_safe_url(url: str) -> bool:
    """Check URL is safe before redirecting."""
    if not url:
        return False
    dangerous = ["javascript:", "data:", "vbscript:", "file:"]
    url_lower  = url.lower().strip()
    return not any(url_lower.startswith(d) for d in dangerous)

def mask_sensitive(value: str, show_chars: int = 4) -> str:
    """Mask sensitive data for display — e.g. KRA PINs."""
    if not value or len(value) <= show_chars:
        return "****"
    return value[:show_chars] + "*" * (len(value) - show_chars)
