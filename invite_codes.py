import random
import string
from datetime import datetime, timezone
from supabase_db import (
    load_invite_codes, save_invite_code,
    consume_invite_code_db, get_invite_code
)

ROLE_PREFIXES = {
    # ── Crops roles ────────────────────────────────────────────────────────
    "exporter":           "VP-EXP",
    "compliance_officer": "VP-COM",
    "record_keeper":      "VP-REC",
    "admin":              "VP-ADM",
    "agronomist":         "VP-AGR",
    "farmer":             "VP-FAR",
    # ── Livestock roles ────────────────────────────────────────────────────
    "diaspora_owner":     "VP-DIA",
    "veterinarian":       "VP-VET",
    "herdsman":           "VP-HRD",
    "farm_manager":       "VP-FMG",
}

VALID_ROLES = list(ROLE_PREFIXES.keys())

# Which roles belong to which module — used for UI grouping
MODULE_ROLE_MAP = {
    "🌿 VeriPath Crops": [
        "exporter","compliance_officer","record_keeper",
        "admin","agronomist","farmer",
    ],
    "🐄 VeriPath Livestock": [
        "diaspora_owner","veterinarian","herdsman","farm_manager","admin",
    ],
}

def generate_invite_code(role: str, created_by: str = "admin") -> str:
    if role not in ROLE_PREFIXES:
        raise ValueError(f"Invalid role: {role}")
    prefix   = ROLE_PREFIXES[role]
    existing = load_invite_codes()
    for _ in range(20):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code   = f"{prefix}-{suffix}"
        if code not in existing:
            break
    save_invite_code(code, role, created_by)
    return code

def validate_invite_code(code: str) -> tuple[bool, str, str | None]:
    code  = code.strip().upper()
    parts = code.split("-")
    if len(parts) != 3 or parts[0] != "VP" or len(parts[2]) != 4:
        return False, "Invalid code format. Expected VP-XXX-XXXX.", None
    prefix = f"VP-{parts[1]}"
    if prefix not in ROLE_PREFIXES.values():
        return False, f"Unknown role prefix '{parts[1]}'.", None
    entry = get_invite_code(code)
    if not entry:
        return False, "Invite code not found. Contact your administrator.", None
    if entry.get("used"):
        return False, f"This code was already used by {entry.get('used_by','someone')}.", None
    role = next(r for r, p in ROLE_PREFIXES.items() if p == prefix)
    return True, "Valid invite code.", role

def consume_invite_code(code: str, username: str) -> bool:
    return consume_invite_code_db(code.strip().upper(), username)

def list_invite_codes() -> list[dict]:
    codes  = load_invite_codes()
    result = []
    for code, meta in codes.items():
        role   = meta.get("role","")
        module = next(
            (m for m, roles in MODULE_ROLE_MAP.items() if role in roles),
            "—"
        )
        result.append({
            "Code":       code,
            "Role":       role,
            "Module":     module,
            "Created By": meta.get("created_by",""),
            "Created At": str(meta.get("created_at",""))[:10],
            "Used":       "✅ Yes" if meta.get("used") else "⏳ Unused",
            "Used By":    meta.get("used_by") or "—",
            "Used At":    str(meta.get("used_at",""))[:10] if meta.get("used_at") else "—",
        })
    return sorted(result, key=lambda x: x["Created At"], reverse=True)

def get_role_from_code(code: str) -> str | None:
    valid, _, role = validate_invite_code(code)
    return role if valid else None

def seed_admin_code() -> str | None:
    codes    = load_invite_codes()
    existing = [c for c, m in codes.items()
                if m.get("role") == "admin" and not m.get("used")]
    if existing:
        return existing[0]
    code = generate_invite_code("admin", created_by="system")
    print(f"\n🔑 ADMIN BOOTSTRAP CODE: {code}\n")
    return code
