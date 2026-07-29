"""
MRL / PHI (Pre-Harvest Interval) zero-tolerance check.

⚠ STARTER DATA — NOT VERIFIED AGAINST A CURRENT PCPB/KEPHIS DOCUMENT ⚠
The chemical names and PHI day-counts below are placeholder reference data
for demo/development purposes only. Before this gates any real shipment,
have an agronomist or licensed advisor confirm every value against current
PCPB label data — a wrong threshold in either direction is a real risk
(too strict blocks legitimate exporters, too loose lets a real violation
through).

LIMITATION — this is a self-reported system. It can only catch a chemical
that the farmer actually logged. A spray that is never logged at all
leaves no record to check here; that gap is only covered by the reactive,
lab-test-based check in vault_checks.check_mrl_red_list(), which doesn't
depend on farmer self-reporting.
"""

from datetime import datetime

# Any use of these, at any time, is flagged regardless of how close to
# harvest — not a timing question, a "should not be used on an EU-export
# crop at all" question. Matched as a substring, case-insensitive, so it
# also catches these typed into the "Other (specify below)" free-text field.
ZERO_TOLERANCE_SUBSTRINGS = [
    "chlorpyrifos",
    "dimethoate",
    "imidacloprid",     # neonicotinoid — EU-restricted
    "clothianidin",     # neonicotinoid — EU-restricted
    "thiamethoxam",     # neonicotinoid — EU-restricted
    "acetamiprid",      # neonicotinoid — EU-restricted
    "thiacloprid",      # neonicotinoid — EU-restricted
    "paraquat",
]

# Permitted chemicals with a required withholding period before harvest.
# STARTER VALUES ONLY — see warning above.
PHI_DAYS = {
    "mancozeb":            7,
    "chlorothalonil":      7,
    "copper oxychloride":  7,
    "lambda-cyhalothrin":  3,
    "cypermethrin":        3,
    "2,4-d":               14,
}


def check_phi_violations(farmer_id: str, crop: str, intake_date_str: str) -> list[str]:
    """
    Returns a list of human-readable issue strings (empty if clean).
    Always recomputes from the live farmer_activities table — never trusts
    a pre-computed flag on the batch record itself, so it can't be
    falsified by editing whatever gets uploaded to packhouse.
    """
    if not farmer_id or not crop or not intake_date_str:
        return []

    try:
        intake_date = datetime.strptime(str(intake_date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        return []

    from supabase_db import get_client
    try:
        rows = get_client().table("farmer_activities").select(
            "date, chemicals, crop, date_mismatch_flag, date_mismatch_note"
        ).eq("farmer_id", farmer_id).execute().data or []
    except Exception:
        return []

    issues = []
    for row in rows:
        if row.get("crop", "").strip().lower() != crop.strip().lower():
            continue
        chem_list = row.get("chemicals") or []
        if not chem_list:
            continue
        try:
            act_date = datetime.strptime(str(row.get("date", ""))[:10], "%Y-%m-%d").date()
        except Exception:
            continue

        days_before_harvest = (intake_date - act_date).days
        if days_before_harvest < 0:
            continue  # logged after this harvest date — not relevant to this batch

        mismatch_note = ""
        if row.get("date_mismatch_flag"):
            mismatch_note = f" ⚠ {row.get('date_mismatch_note','Logged date does not match photo timestamp')} — verify."

        for chem in chem_list:
            chem_norm = chem.strip().lower()

            if any(zt in chem_norm for zt in ZERO_TOLERANCE_SUBSTRINGS):
                issues.append(
                    f"MRL/PHI ZERO-TOLERANCE: '{chem}' logged {act_date.isoformat()} "
                    f"({days_before_harvest}d before harvest) — not permitted for EU export.{mismatch_note}"
                )
                continue

            for known_chem, phi_days in PHI_DAYS.items():
                if known_chem in chem_norm and days_before_harvest < phi_days:
                    issues.append(
                        f"MRL/PHI VIOLATION: '{chem}' logged {act_date.isoformat()} — "
                        f"needs {phi_days}d before harvest, only {days_before_harvest}d elapsed.{mismatch_note}"
                    )
                    break

    return issues
