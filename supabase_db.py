import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_client = None

def get_client():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def _now():
    return datetime.now(timezone.utc).isoformat()

# ── USERS ─────────────────────────────────────────────────────────────────

def load_users() -> dict:
    try:
        res = get_client().table("users").select("*").execute()
        return {r["username"]: r for r in res.data}
    except Exception as e:
        print(f"[DB] load_users error: {e}")
        return {}

def save_user(username: str, data: dict) -> bool:
    try:
        get_client().table("users").upsert({
            "username":          username,
            "full_name":         data.get("full_name",""),
            "company":           data.get("company",""),
            "role":              data.get("role","exporter"),
            "password":          data.get("password",""),
            "salt":              data.get("salt",""),
            "created_at":        data.get("created_at", _now()),
            "last_login":        data.get("last_login"),
            "invite_code_used":  data.get("invite_code_used",""),
            "subscription_tier": data.get("subscription_tier","trial"),
            "containers_used":   data.get("containers_used", 0),
        }).execute()
        return True
    except Exception as e:
        print(f"[DB] save_user error: {e}")
        return False

def get_user(username: str) -> dict | None:
    try:
        res = get_client().table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] get_user error: {e}")
        return None

def update_user_login(username: str) -> None:
    try:
        get_client().table("users").update(
            {"last_login": _now()}
        ).eq("username", username).execute()
    except Exception as e:
        print(f"[DB] update_user_login error: {e}")

# ── COMPANIES ─────────────────────────────────────────────────────────────

def _company_key(name: str) -> str:
    return name.strip().lower()

def load_companies() -> dict:
    try:
        res = get_client().table("companies").select("*").execute()
        return {r["company_key"]: r for r in res.data}
    except Exception as e:
        print(f"[DB] load_companies error: {e}")
        return {}

def get_company(company_name: str) -> dict | None:
    try:
        key = _company_key(company_name)
        res = get_client().table("companies").select("*").eq("company_key", key).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] get_company error: {e}")
        return None

def ensure_company(company_name: str, created_at: str = None) -> dict:
    key = _company_key(company_name)
    existing = get_company(company_name)
    if existing:
        return existing
    try:
        data = {
            "company_key":        key,
            "company_name":       company_name.strip(),
            "subscription_tier":  "trial",
            "trial_started_at":   created_at or _now(),
            "tier_set_at":        None,
            "tier_expires_at":    None,
            "containers_used":    0,
        }
        get_client().table("companies").insert(data).execute()
        return data
    except Exception as e:
        print(f"[DB] ensure_company error: {e}")
        return {}

def update_company_tier(company_name: str, tier: str,
                         expires_at: str) -> bool:
    try:
        key = _company_key(company_name)
        get_client().table("companies").update({
            "subscription_tier": tier,
            "tier_set_at":       _now(),
            "tier_expires_at":   expires_at,
            "containers_used":   0,
        }).eq("company_key", key).execute()
        return True
    except Exception as e:
        print(f"[DB] update_company_tier error: {e}")
        return False

def increment_company_containers(company_name: str) -> int:
    try:
        key = _company_key(company_name)
        rec = get_company(company_name)
        current = int(rec.get("containers_used", 0)) if rec else 0
        new_val = current + 1
        get_client().table("companies").update(
            {"containers_used": new_val}
        ).eq("company_key", key).execute()
        return new_val
    except Exception as e:
        print(f"[DB] increment_containers error: {e}")
        return 0

def list_companies(exporters_only: bool = False) -> list[dict]:
    try:
        companies = load_companies()
        if exporters_only:
            users = load_users()
            exporter_companies = {
                _company_key(u.get("company",""))
                for u in users.values()
                if u.get("role") == "exporter"
            }
            companies = {k: v for k, v in companies.items()
                         if k in exporter_companies}
        return [
            {
                "Company":     v.get("company_name", k),
                "Tier":        v.get("subscription_tier","trial"),
                "Trial Start": str(v.get("trial_started_at",""))[:10],
                "Expires":     str(v.get("tier_expires_at",""))[:10]
                               if v.get("tier_expires_at") else "—",
                "Containers":  v.get("containers_used", 0),
            }
            for k, v in companies.items()
        ]
    except Exception as e:
        print(f"[DB] list_companies error: {e}")
        return []

# ── INVITE CODES ──────────────────────────────────────────────────────────

def load_invite_codes() -> dict:
    try:
        res = get_client().table("invite_codes").select("*").execute()
        return {r["code"]: r for r in res.data}
    except Exception as e:
        print(f"[DB] load_invite_codes error: {e}")
        return {}

def save_invite_code(code: str, role: str, created_by: str) -> bool:
    try:
        get_client().table("invite_codes").insert({
            "code":       code,
            "role":       role,
            "created_by": created_by,
            "created_at": _now(),
            "used":       False,
            "used_by":    None,
            "used_at":    None,
        }).execute()
        return True
    except Exception as e:
        print(f"[DB] save_invite_code error: {e}")
        return False

def consume_invite_code_db(code: str, username: str) -> bool:
    try:
        get_client().table("invite_codes").update({
            "used":    True,
            "used_by": username,
            "used_at": _now(),
        }).eq("code", code).execute()
        return True
    except Exception as e:
        print(f"[DB] consume_invite_code error: {e}")
        return False

def get_invite_code(code: str) -> dict | None:
    try:
        res = get_client().table("invite_codes").select("*").eq("code", code).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] get_invite_code error: {e}")
        return None

# ── FARMERS ───────────────────────────────────────────────────────────────

def load_farmers_db(company: str = None) -> dict:
    try:
        q = get_client().table("farmers").select("*")
        if company:
            q = q.eq("company", company.strip())
        res = q.execute()
        farmers = {}
        for r in res.data:
            fid = r.pop("farmer_id")
            # Parse JSONB fields
            if isinstance(r.get("crops"), str):
                r["crops"] = json.loads(r["crops"])
            if isinstance(r.get("hs_codes"), str):
                r["hs_codes"] = json.loads(r["hs_codes"])
            farmers[fid] = r
        return farmers
    except Exception as e:
        print(f"[DB] load_farmers error: {e}")
        return {}

def save_farmer_db(farmer_id: str, data: dict) -> bool:
    try:
        get_client().table("farmers").upsert({
            "farmer_id":    farmer_id,
            "company":      data.get("company",""),
            "name":         data.get("name",""),
            "phone":        data.get("phone",""),
            "id_number":    data.get("id_number",""),
            "county":       data.get("county",""),
            "sub_location": data.get("sub_location",""),
            "farm_size_ha": data.get("farm_size_ha", 0),
            "crops":        json.dumps(data.get("crops",[])),
            "hs_codes":     json.dumps(data.get("hs_codes",{})),
            "gps":          data.get("gps",""),
            "registered_at":data.get("registered_at", _now()),
            "status":       data.get("status","Active"),
        }).execute()
        return True
    except Exception as e:
        print(f"[DB] save_farmer error: {e}")
        return False

# ── LEDGER ────────────────────────────────────────────────────────────────

def load_ledger_db(company: str = None) -> list[dict]:
    try:
        q = get_client().table("ledger").select("*").order("timestamp", desc=True)
        if company:
            q = q.eq("company", company.strip())
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] load_ledger error: {e}")
        return []

def save_ledger_record_db(record: dict) -> bool:
    try:
        # Remove auto-generated fields if present
        record.pop("id", None)
        get_client().table("ledger").insert(record).execute()
        return True
    except Exception as e:
        print(f"[DB] save_ledger_record error: {e}")
        return False

def update_ledger_record_db(session_id: str, crop: str,
                              company: str, updates: dict) -> bool:
    try:
        updates["last_edited"] = _now()
        get_client().table("ledger").update(updates).eq(
            "session_id", session_id
        ).eq("crop", crop).eq("company", company.strip()).execute()
        return True
    except Exception as e:
        print(f"[DB] update_ledger_record error: {e}")
        return False

def delete_ledger_record_db(session_id: str, crop: str,
                              company: str) -> bool:
    try:
        get_client().table("ledger").delete().eq(
            "session_id", session_id
        ).eq("crop", crop).eq("company", company.strip()).execute()
        return True
    except Exception as e:
        print(f"[DB] delete_ledger_record error: {e}")
        return False

def clear_company_ledger_db(company: str) -> int:
    try:
        res = get_client().table("ledger").select("id").eq(
            "company", company.strip()
        ).execute()
        count = len(res.data)
        get_client().table("ledger").delete().eq(
            "company", company.strip()
        ).execute()
        return count
    except Exception as e:
        print(f"[DB] clear_company_ledger error: {e}")
        return 0

# ── CONSIGNMENTS ──────────────────────────────────────────────────────────

def load_consignments_db(company: str = None) -> list[dict]:
    try:
        q = get_client().table("consignments").select("*").order(
            "created_at", desc=True)
        if company:
            q = q.eq("company", company.strip())
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] load_consignments error: {e}")
        return []

def save_consignment_db(record: dict) -> bool:
    try:
        record.pop("id", None)
        get_client().table("consignments").insert(record).execute()
        return True
    except Exception as e:
        print(f"[DB] save_consignment error: {e}")
        return False

def clear_company_consignments_db(company: str) -> int:
    try:
        res = get_client().table("consignments").select("id").eq(
            "company", company.strip()
        ).execute()
        count = len(res.data)
        get_client().table("consignments").delete().eq(
            "company", company.strip()
        ).execute()
        return count
    except Exception as e:
        print(f"[DB] clear_company_consignments error: {e}")
        return 0

# ── TRANSMISSION LOG ──────────────────────────────────────────────────────

def save_transmission_log_db(records: list[dict], company: str) -> bool:
    try:
        for r in records:
            r.pop("id", None)
            r["company"] = company
        get_client().table("transmission_log").insert(records).execute()
        return True
    except Exception as e:
        print(f"[DB] save_transmission_log error: {e}")
        return False

def load_transmission_log_db(company: str = None) -> list[dict]:
    try:
        q = get_client().table("transmission_log").select("*").order(
            "submitted_at", desc=True)
        if company:
            q = q.eq("company", company.strip())
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] load_transmission_log error: {e}")
        return []

# ── KPI OVERRIDES ─────────────────────────────────────────────────────────

def load_kpi_overrides() -> dict:
    try:
        res = get_client().table("kpi_overrides").select("*").eq("id", 1).execute()
        return res.data[0] if res.data else {"cac_kes": 5000, "churn_rate_pct": 0.0}
    except Exception as e:
        print(f"[DB] load_kpi_overrides error: {e}")
        return {"cac_kes": 5000, "churn_rate_pct": 0.0}

def save_kpi_overrides(cac_kes: int, churn_rate_pct: float) -> bool:
    try:
        get_client().table("kpi_overrides").upsert({
            "id":             1,
            "cac_kes":        cac_kes,
            "churn_rate_pct": churn_rate_pct,
            "updated_at":     _now(),
        }).execute()
        return True
    except Exception as e:
        print(f"[DB] save_kpi_overrides error: {e}")
        return False

# ── CONNECTION TEST ───────────────────────────────────────────────────────

def test_connection() -> bool:
    try:
        get_client().table("users").select("username").limit(1).execute()
        return True
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Supabase connection...")
    if test_connection():
        print("✅ Connected to Supabase successfully")
        print(f"   URL: {SUPABASE_URL}")
    else:
        print("❌ Connection failed — check .env credentials")

def save_full_ledger_db(records: list[dict]) -> None:
    """Bulk upsert — used for migrations only."""
    try:
        for r in records:
            r.pop("id", None)
            get_client().table("ledger").upsert(r).execute()
    except Exception as e:
        print(f"[DB] save_full_ledger error: {e}")
