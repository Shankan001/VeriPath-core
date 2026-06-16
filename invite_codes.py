import json
import os
import random
import string
from datetime import datetime

DATA_DIR        = "data"
INVITE_FILE     = os.path.join(DATA_DIR, "invite_codes.json")

ROLE_PREFIXES = {
    "exporter":           "VP-EXP",
    "compliance_officer": "VP-COM",
    "record_keeper":      "VP-REC",
    "admin":              "VP-ADM",
}

VALID_ROLES = list(ROLE_PREFIXES.keys())

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_codes() -> dict:
    _ensure_dir()
    if not os.path.exists(INVITE_FILE):
        return {}
    try:
        with open(INVITE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_codes(codes: dict) -> None:
    _ensure_dir()
    with open(INVITE_FILE, "w") as f:
        json.dump(codes, f, indent=2)

def generate_invite_code(role: str, created_by: str = "admin") -> str:
    """Generate and persist a new invite code for the given role."""
    if role not in ROLE_PREFIXES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    codes = _load_codes()
    prefix = ROLE_PREFIXES[role]
    # Ensure uniqueness
    for _ in range(20):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code   = f"{prefix}-{suffix}"
        if code not in codes:
            break
    codes[code] = {
        "role":       role,
        "created_by": created_by,
        "created_at": datetime.utcnow().isoformat(),
        "used":       False,
        "used_by":    None,
        "used_at":    None,
    }
    _save_codes(codes)
    return code

def validate_invite_code(code: str) -> tuple[bool, str, str | None]:
    """
    Returns (valid: bool, message: str, role: str | None)
    Checks format, existence, and whether already used.
    """
    code = code.strip().upper()
    # Format check
    parts = code.split("-")
    if len(parts) != 3 or parts[0] != "VP" or len(parts[2]) != 4:
        return False, "Invalid code format. Expected VP-XXX-XXXX.", None
    prefix = f"VP-{parts[1]}"
    if prefix not in ROLE_PREFIXES.values():
        return False, f"Unknown role prefix '{parts[1]}'. Valid: EXP, COM, REC, ADM.", None
    codes = _load_codes()
    if code not in codes:
        return False, "Invite code not found. Contact your administrator.", None
    entry = codes[code]
    if entry["used"]:
        return False, f"This code was already used by {entry['used_by']}.", None
    # Derive role from prefix
    role = next(r for r, p in ROLE_PREFIXES.items() if p == prefix)
    return True, "Valid invite code.", role

def consume_invite_code(code: str, username: str) -> bool:
    """Mark a code as used. Call only after successful registration."""
    code  = code.strip().upper()
    codes = _load_codes()
    if code not in codes or codes[code]["used"]:
        return False
    codes[code]["used"]    = True
    codes[code]["used_by"] = username
    codes[code]["used_at"] = datetime.utcnow().isoformat()
    _save_codes(codes)
    return True

def list_invite_codes() -> list[dict]:
    """Return all codes as a list of dicts (for admin view)."""
    codes = _load_codes()
    result = []
    for code, meta in codes.items():
        result.append({
            "Code":       code,
            "Role":       meta["role"],
            "Created By": meta["created_by"],
            "Created At": meta["created_at"][:10],
            "Used":       "✅ Yes" if meta["used"] else "⏳ Unused",
            "Used By":    meta["used_by"] or "—",
            "Used At":    meta["used_at"][:10] if meta["used_at"] else "—",
        })
    return sorted(result, key=lambda x: x["Created At"], reverse=True)

def get_role_from_code(code: str) -> str | None:
    """Quick lookup — returns role string or None."""
    valid, _, role = validate_invite_code(code)
    return role if valid else None

# ── Seed admin code on first run ──────────────────────────────
def seed_admin_code() -> str | None:
    """
    If no admin code exists yet, create one and print it.
    Call this once during setup.
    """
    codes = _load_codes()
    existing_admin = [c for c, m in codes.items() if m["role"] == "admin" and not m["used"]]
    if existing_admin:
        return existing_admin[0]
    code = generate_invite_code("admin", created_by="system")
    print(f"\n🔑 ADMIN BOOTSTRAP CODE: {code}\n   Use this to create the first admin account.\n")
    return code

if __name__ == "__main__":
    print("=== VeriPath Invite Code System ===\n")
    # Seed an admin bootstrap code
    admin_code = seed_admin_code()
    # Generate one of each role
    for role in ["exporter", "compliance_officer", "record_keeper"]:
        code = generate_invite_code(role, created_by="admin")
        print(f"Generated [{role}]: {code}")
    print("\n--- Validation Tests ---")
    # Test valid
    exp_code = generate_invite_code("exporter")
    ok, msg, role = validate_invite_code(exp_code)
    print(f"Valid code test:   {ok} | {msg} | role={role}")
    # Test bad format
    ok, msg, role = validate_invite_code("BADCODE")
    print(f"Bad format test:   {ok} | {msg}")
    # Test consume
    consume_invite_code(exp_code, "testuser")
    ok, msg, role = validate_invite_code(exp_code)
    print(f"Used code test:    {ok} | {msg}")
    print("\n--- All Codes ---")
    for entry in list_invite_codes():
        print(entry)
