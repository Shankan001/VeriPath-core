import json
import os
import hashlib
import secrets
from datetime import datetime
from invite_codes import validate_invite_code, consume_invite_code

DATA_DIR   = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=260_000
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
    """
    Register a new user.
    invite_code is required and must match the requested role.
    """
    username = username.strip().lower()

    # ── Basic field validation ────────────────────────────────
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    # ── Invite code validation ────────────────────────────────
    if not invite_code or not invite_code.strip():
        return False, "An invite code is required to register."
    code_ok, code_msg, code_role = validate_invite_code(invite_code.strip().upper())
    if not code_ok:
        return False, f"Invite code error: {code_msg}"
    if code_role != role:
        return False, (f"Invite code is for '{code_role}' role, "
                       f"but you selected '{role}'. Use the correct code.")

    # ── Duplicate check ───────────────────────────────────────
    users = _load_users()
    if username in users:
        return False, "Username already exists. Please choose another."

    # ── Create user ───────────────────────────────────────────
    hashed, salt = _hash_password(password)
    users[username] = {
        "username":          username,
        "full_name":         full_name.strip(),
        "company":           company.strip(),
        "role":              role,
        "password":          hashed,
        "salt":              salt,
        "created_at":        datetime.utcnow().isoformat(),
        "last_login":        None,
        "invite_code_used":  invite_code.strip().upper(),
        "subscription_tier": "trial",
        "containers_used":   0,
    }
    _save_users(users)

    # ── Consume the code so it can't be reused ────────────────
    consume_invite_code(invite_code.strip().upper(), username)

    return True, f"Account created for {full_name}."

def login_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()
    users    = _load_users()
    if username not in users:
        return False, "Invalid username or password.", None
    user = users[username]
    if not _verify_password(password, user["password"], user["salt"]):
        return False, "Invalid username or password.", None
    users[username]["last_login"] = datetime.utcnow().isoformat()
    _save_users(users)
    profile = {k: v for k, v in user.items() if k not in ("password", "salt")}
    return True, f"Welcome back, {user['full_name']}.", profile

def get_user_count() -> int:
    return len(_load_users())

if __name__ == "__main__":
    from invite_codes import generate_invite_code, seed_admin_code
    if os.path.exists(USERS_FILE):
        os.remove(USERS_FILE)
    # Seed an admin code, then register using it
    admin_code = seed_admin_code()
    ok, msg = register_user("josephm", "Veri2025!", "Joseph Memusi",
                            "VeriPath Africa", "admin", admin_code)
    print(f"Register: {ok} — {msg}")
    ok, msg, profile = login_user("josephm", "Veri2025!")
    print(f"Login:    {ok} — {msg}")
    print(f"Profile:  {profile}")
    ok, msg, _ = login_user("josephm", "wrongpassword")
    print(f"Bad pwd:  {ok} — {msg}")
    print(f"Total users: {get_user_count()}")
