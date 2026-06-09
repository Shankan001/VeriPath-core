import json
import os
import hashlib
import secrets
from datetime import datetime

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
                  full_name: str, company: str, role: str = "exporter") -> tuple[bool, str]:
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    users = _load_users()
    if username in users:
        return False, "Username already exists. Please choose another."
    hashed, salt = _hash_password(password)
    users[username] = {
        "username":   username,
        "full_name":  full_name.strip(),
        "company":    company.strip(),
        "role":       role,
        "password":   hashed,
        "salt":       salt,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
    }
    _save_users(users)
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
    if os.path.exists(USERS_FILE):
        os.remove(USERS_FILE)
    ok, msg = register_user("josephm", "Veri2025!", "Joseph Memusi", "VeriPath Africa", "admin")
    print(f"Register: {ok} — {msg}")
    ok, msg, profile = login_user("josephm", "Veri2025!")
    print(f"Login:    {ok} — {msg}")
    print(f"Profile:  {profile}")
    ok, msg, _ = login_user("josephm", "wrongpassword")
    print(f"Bad pwd:  {ok} — {msg}")
    print(f"Total users: {get_user_count()}")
