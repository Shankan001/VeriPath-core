import json
import os
import hashlib
import secrets
from datetime import datetime, timezone
from invite_codes import validate_invite_code, consume_invite_code

DATA_DIR   = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

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

def _load_users() -> dict:
    _ensure_dir()
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_users(users: dict) -> None:
    _ensure_dir()
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def register_user(username: str, password: str,
                  full_name: str, company: str,
                  role: str = "exporter",
                  invite_code: str = "") -> tuple[bool, str]:
    username = username.strip().lower()

    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if not company.strip():
        return False, "Company name is required."

    # Invite code validation
    if not invite_code or not invite_code.strip():
        return False, "An invite code is required to register."
    code_ok, code_msg, code_role = validate_invite_code(invite_code.strip().upper())
    if not code_ok:
        return False, f"Invite code error: {code_msg}"
    if code_role != role:
        return False, (f"Invite code is for '{code_role}' role, "
                       f"but you selected '{role}'.")

    users = _load_users()
    if username in users:
        return False, "Username already exists."

    hashed, salt = _hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    users[username] = {
        "username":          username,
        "full_name":         full_name.strip(),
        "company":           company.strip(),
        "role":              role,
        "password":          hashed,
        "salt":              salt,
        "created_at":        now,
        "last_login":        None,
        "invite_code_used":  invite_code.strip().upper(),
        "subscription_tier": "trial",
        "containers_used":   0,
    }
    _save_users(users)
    consume_invite_code(invite_code.strip().upper(), username)

    # ── Auto-create company record on registration ────────────────
    try:
        from trial import ensure_company_record
        ensure_company_record(company.strip(), first_user_created_at=now)
    except Exception as e:
        pass  # Non-fatal — company record created on next login

    return True, f"Account created for {full_name}."

def login_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()
    users    = _load_users()
    if username not in users:
        return False, "Invalid username or password.", None
    user = users[username]
    if not _verify_password(password, user["password"], user["salt"]):
        return False, "Invalid username or password.", None
    users[username]["last_login"] = datetime.now(timezone.utc).isoformat()
    _save_users(users)

    # ── Ensure company record exists on every login ───────────────
    try:
        from trial import ensure_company_record
        ensure_company_record(user.get("company",""),
                              first_user_created_at=user.get("created_at"))
    except Exception:
        pass

    profile = {k: v for k, v in user.items() if k not in ("password","salt")}
    return True, f"Welcome back, {user['full_name']}.", profile

def get_user_count() -> int:
    return len(_load_users())
