import hashlib
import secrets
from datetime import datetime, timezone
from supabase_db import (
    get_user, save_user, update_user_login,
    load_users, ensure_company
)
from security import (
    check_rate_limit, reset_rate_limit,
    sanitize_username, sanitize_company,
    validate_password_strength,
    log_security_event,
)

def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'),
        salt.encode('utf-8'), iterations=260_000
    ).hex()
    return hashed, salt

def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    hashed, _ = _hash_password(password, salt)
    return secrets.compare_digest(hashed, stored_hash)

def register_user(username: str, password: str,
                  full_name: str, company: str,
                  role: str = "exporter",
                  invite_code: str = "",
                  module: str = "🌿 VeriPath Crops") -> tuple[bool, str]:

    # ── Sanitize inputs ────────────────────────────────────────
    valid_u, username, err_u = sanitize_username(username)
    if not valid_u:
        return False, err_u

    valid_c, company, err_c = sanitize_company(company)
    if not valid_c and role != "farmer":
        return False, err_c

    full_name = full_name.strip()[:100]
    if not full_name:
        return False, "Full name is required."

    # ── Password strength ──────────────────────────────────────
    valid_p, err_p = validate_password_strength(password)
    if not valid_p:
        return False, err_p

    # ── Invite code ────────────────────────────────────────────
    if not invite_code or not invite_code.strip():
        return False, "An invite code is required to register."

    from invite_codes import validate_invite_code, consume_invite_code
    code_ok, code_msg, code_role = validate_invite_code(
        invite_code.strip().upper()
    )
    if not code_ok:
        log_security_event("register_failed", username,
                           f"Bad invite code: {invite_code}", False)
        return False, f"Invite code error: {code_msg}"

    if code_role != role:
        return False, (f"Invite code is for '{code_role}' role, "
                       f"but you selected '{role}'.")

    # ── Duplicate check ────────────────────────────────────────
    existing = get_user(username)
    if existing:
        log_security_event("register_failed", username,
                           "Duplicate username attempt", False)
        return False, "Username already exists."

    hashed, salt = _hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    ok = save_user(username, {
        "username":          username,
        "full_name":         full_name,
        "company":           company.strip(),
        "role":              role,
        "module":            module,
        "password":          hashed,
        "salt":              salt,
        "created_at":        now,
        "last_login":        None,
        "invite_code_used":  invite_code.strip().upper(),
        "subscription_tier": "trial",
        "containers_used":   0,
    })
    if not ok:
        return False, "Failed to save user. Please try again."

    consume_invite_code(invite_code.strip().upper(), username)
    ensure_company(company.strip(), created_at=now)
    log_security_event("register_success", username,
                       f"Role: {role} · Module: {module}", True)
    return True, f"Account created for {full_name}."

def login_user(username: str,
               password: str) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()

    # ── Rate limiting — 5 attempts per 5 minutes ───────────────
    rate_key = f"login:{username}"
    allowed, wait = check_rate_limit(rate_key, max_attempts=5,
                                     window_seconds=300)
    if not allowed:
        log_security_event("login_rate_limited", username,
                           f"Blocked for {wait}s", False)
        return False, (f"Too many login attempts. "
                       f"Try again in {wait} seconds."), None

    user = get_user(username)
    if not user:
        log_security_event("login_failed", username,
                           "User not found", False)
        return False, "Invalid username or password.", None

    if not _verify_password(password, user["password"], user["salt"]):
        log_security_event("login_failed", username,
                           "Wrong password", False)
        return False, "Invalid username or password.", None

    # ── Success — reset rate limit ─────────────────────────────
    reset_rate_limit(rate_key)
    update_user_login(username)
    ensure_company(user.get("company",""),
                   created_at=user.get("created_at"))

    log_security_event("login_success", username,
                       f"Role: {user.get('role','?')}", True)

    profile = {k: v for k, v in user.items()
               if k not in ("password","salt")}
    return True, f"Welcome back, {user['full_name']}.", profile

def get_user_count() -> int:
    return len(load_users())
