"""
VeriPath Regulatory Certificate Vault — Stage 4
Cross-check engines + VP-VISA code generation + save-to-vault orchestration.

ASSUMPTIONS TO VERIFY (marked below with # ASSUMPTION):
1. Your `consignments` table has columns `id` and a weight/volume field —
   guessed as `weight_kg`. Adjust to match your real column name.
2. PDF generation uses `fpdf2` (common, lightweight). If your app already
   uses `reportlab` or another library elsewhere, tell me and I'll rewrite
   generate_kra_pdf() to match, so you're not maintaining two PDF libraries.
"""
import random
import string
from datetime import datetime


def generate_vp_visa_code() -> str:
    """VP-VISA-XXXX — 4 random alphanumeric chars."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"VP-VISA-{suffix}"


def save_certificate_to_vault(supabase, document_type: str, parsed_data: dict,
                               raw_text: str, file_name: str, uploaded_by: str,
                               farm_latitude: float = None, farm_longitude: float = None,
                               outgrower_block_id: str = None) -> dict:
    """
    Inserts the parsed certificate into export_regulatory_vault, then
    dispatches to the correct cross-check based on document_type.
    """
    vp_visa_code = generate_vp_visa_code()

    row = {
        "vp_visa_code": vp_visa_code,
        "document_type": document_type,
        "document_number": parsed_data.get("document_number"),
        "holder_name": parsed_data.get("holder_name"),
        "volume_or_weight": parsed_data.get("volume_or_weight"),
        "volume_unit": parsed_data.get("volume_unit"),
        "expiry_date": parsed_data.get("expiry_date"),
        "issue_date": parsed_data.get("issue_date"),
        "raw_extracted_text": raw_text,
        "parsed_json": parsed_data,
        "verification_status": "pending",
        "outgrower_block_id": outgrower_block_id,
        "farm_latitude": farm_latitude,
        "farm_longitude": farm_longitude,
        "source_file_name": file_name,
        "uploaded_by": uploaded_by,
    }

    try:
        result = supabase.table("export_regulatory_vault").insert(row).execute()
        inserted = result.data[0]
        vault_id = inserted["id"]
    except Exception as e:
        return {"success": False, "error": f"Insert failed: {str(e)}"}

    if document_type == "HCD_EXPORT_LICENCE":
        check_result = check_hcd_auction_breach(supabase, vault_id)
    elif document_type == "KEPHIS_PHYTOSANITARY":
        check_result = check_kephis_vs_packhouse(supabase, vault_id, parsed_data)
    elif document_type == "GLOBALGAP_MRL":
        check_result = check_mrl_red_list(supabase, vault_id, parsed_data, outgrower_block_id)
    elif document_type == "KRA_CERTIFICATE_ORIGIN":
        check_result = {"status": "verified", "reason": None}
    else:
        check_result = {"status": "pending", "reason": "No cross-check defined for this type"}

    try:
        supabase.table("export_regulatory_vault").update({
            "verification_status": check_result["status"],
            "flag_reason": check_result.get("reason"),
        }).eq("id", vault_id).execute()
    except Exception as e:
        return {"success": False, "error": f"Cross-check ran but status update failed: {str(e)}"}

    return {
        "success": True,
        "vault_id": vault_id,
        "vp_visa_code": vp_visa_code,
        "status": check_result["status"],
        "reason": check_result.get("reason"),
    }


def check_hcd_auction_breach(supabase, vault_id: str) -> dict:
    try:
        vault_row = supabase.table("export_regulatory_vault").select("volume_or_weight").eq("id", vault_id).single().execute().data
        licence_limit = vault_row["volume_or_weight"]

        if licence_limit is None:
            return {"status": "flagged", "reason": "Licence volume limit could not be read from the document — manual review needed."}

        lots = supabase.table("auction_lot_traceability").select("volume_purchased").eq("hcd_licence_id", vault_id).execute().data
        running_total = sum(lot["volume_purchased"] for lot in lots) if lots else 0

        if lots:
            supabase.table("auction_lot_traceability").update({
                "running_total_volume": running_total,
                "licence_limit": licence_limit,
            }).eq("hcd_licence_id", vault_id).execute()

        if running_total > licence_limit:
            overage = running_total - licence_limit
            return {
                "status": "flagged",
                "reason": f"Auction purchases ({running_total}) exceed HCD licence limit ({licence_limit}) by {overage}."
            }

        return {"status": "verified", "reason": None}

    except Exception as e:
        return {"status": "flagged", "reason": f"Cross-check error: {str(e)}"}


def check_kephis_vs_packhouse(supabase, vault_id: str, parsed_data: dict, consignment_id: str = None) -> dict:
    cert_weight = parsed_data.get("volume_or_weight")

    if consignment_id is None:
        return {"status": "pending", "reason": "No linked consignment provided for weight comparison."}

    try:
        consignment = supabase.table("consignments").select("weight_kg").eq("id", consignment_id).single().execute().data
        packhouse_weight = consignment.get("weight_kg")

        if cert_weight is None or packhouse_weight is None:
            return {"status": "flagged", "reason": "Could not compare weights — one or both values missing."}

        tolerance_pct = 0.05
        diff_pct = abs(cert_weight - packhouse_weight) / packhouse_weight if packhouse_weight else 1

        if diff_pct > tolerance_pct:
            return {
                "status": "flagged",
                "reason": f"KEPHIS certificate weight ({cert_weight}) differs from packhouse record ({packhouse_weight}) by more than {int(tolerance_pct*100)}%."
            }

        return {"status": "verified", "reason": None}

    except Exception as e:
        return {"status": "flagged", "reason": f"Cross-check error: {str(e)}"}


def check_mrl_red_list(supabase, vault_id: str, parsed_data: dict, outgrower_block_id: str) -> dict:
    mrl_result = parsed_data.get("mrl_result", "").upper()

    if mrl_result != "FAIL":
        return {"status": "verified", "reason": None}

    substances = parsed_data.get("flagged_substances", [])
    substance_note = f" Flagged substances: {', '.join(substances)}." if substances else ""
    reason = f"MRL test failed for this block.{substance_note}"

    if outgrower_block_id:
        try:
            supabase.table("export_regulatory_vault").update({
                "verification_status": "red_listed",
                "flag_reason": reason,
            }).eq("outgrower_block_id", outgrower_block_id).execute()
        except Exception as e:
            return {"status": "red_listed", "reason": reason + f" (Warning: could not propagate to other block records: {str(e)})"}

    return {"status": "red_listed", "reason": reason}
