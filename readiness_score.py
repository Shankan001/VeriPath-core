"""
Export Readiness Score — company-wide compliance snapshot for the Dashboard.

Combines three signals already computed elsewhere in the app into one score:
  - Farm boundary coverage (every registered farmer should have one)
  - Unresolved MRL/PHI flags (persisted by Pre-Audit — see pre_audit.py / mrl_phi.py)
  - Laboratory certificate coverage (a GlobalG.A.P/MRL cert per outgrower
    block, not currently red-listed)

This is a simple passed/total ratio across three checks — not a weighted or
regulatory-certified score. Treat the percentage as directional ("what needs
attention before shipment"), not as an official compliance rating.
"""

from supabase_db import get_client


def compute_readiness_score(company: str, role: str = "") -> dict:
    supabase = get_client()
    scoped = role != "admin"

    farmers_q = supabase.table("farmers").select("farmer_id, name")
    if scoped:
        farmers_q = farmers_q.eq("company", company)
    farmers = farmers_q.execute().data or []
    farmer_ids = {f["farmer_id"] for f in farmers}

    boundaries = supabase.table("farm_boundaries").select(
        "farmer_id, outgrower_block_id"
    ).execute().data or []
    if scoped:
        boundaries = [b for b in boundaries if b.get("farmer_id") in farmer_ids]

    farmers_with_boundary = {b["farmer_id"] for b in boundaries if b.get("farmer_id")}
    missing_boundary_farmers = [
        f["name"] for f in farmers if f["farmer_id"] not in farmers_with_boundary
    ]

    ledger_q = supabase.table("ledger").select("farmer_name, audit_status, audit_failure_reason")
    if scoped:
        ledger_q = ledger_q.eq("company", company)
    ledger_rows = ledger_q.execute().data or []
    phi_flagged = [
        r for r in ledger_rows
        if r.get("audit_status") == "flagged" and "MRL/PHI" in (r.get("audit_failure_reason") or "")
    ]

    blocks = sorted({b["outgrower_block_id"] for b in boundaries if b.get("outgrower_block_id")})
    vault_q = supabase.table("export_regulatory_vault").select(
        "outgrower_block_id, document_type, verification_status"
    )
    if scoped:
        vault_q = vault_q.eq("company", company)
    vault_rows = vault_q.execute().data or []

    mrl_status_by_block = {}
    for v in vault_rows:
        if v.get("document_type") != "GLOBALGAP_MRL":
            continue
        bid = v.get("outgrower_block_id")
        if not bid:
            continue
        if bid not in mrl_status_by_block or v.get("verification_status") != "red_listed":
            mrl_status_by_block[bid] = v.get("verification_status")

    missing_cert_blocks = [b for b in blocks if mrl_status_by_block.get(b) in (None, "red_listed")]

    total_checks = len(farmers) + len(ledger_rows) + len(blocks)
    passed = (
        (len(farmers) - len(missing_boundary_farmers))
        + (len(ledger_rows) - len(phi_flagged))
        + (len(blocks) - len(missing_cert_blocks))
    )
    score = round((passed / total_checks) * 100) if total_checks > 0 else 100

    return {
        "score": score,
        "missing_boundary_count": len(missing_boundary_farmers),
        "missing_boundary_names": missing_boundary_farmers,
        "phi_flagged_count": len(phi_flagged),
        "phi_flagged_farmers": [r.get("farmer_name", "—") for r in phi_flagged],
        "missing_cert_count": len(missing_cert_blocks),
        "missing_cert_blocks": missing_cert_blocks,
    }
