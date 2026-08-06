"""
quarantine_ai.py — fix suggestions for Pre-Audit Quarantine Desk flagged
records, with an optional Claude-generated one-paragraph summary on top.

Suggestions themselves are RULE-BASED, not LLM-generated — every fact used
(HS codes, which fields are EUDR-required, PHI day math) is already
computed correctly elsewhere in the app. Having an LLM guess at
compliance-critical values here would add hallucination risk with no real
benefit. Claude's only job (synthesize_action_plan) is to rephrase and
prioritize the already-correct suggestions into one readable paragraph —
it is explicitly instructed not to introduce any new facts.

NOTE: HS_CODE_MAP below is duplicated from app.py's HS_CODE_MAP, not
imported — quarantine_desk.py (which will import this file) is itself
imported BY app.py, so importing back from app.py would be circular.
Keep these two maps in sync if crops/codes change.
"""

import os
import re
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-5"

HS_CODE_MAP = {
    "Maize": "1005.90", "Coffee": "0901.11", "Tea": "0902.30", "Avocado": "0804.40",
    "French Beans": "0708.20", "Roses": "0603.11", "Macadamia Nuts": "0802.62",
    "Mango": "0804.50", "Pineapple": "0804.30", "Passion Fruit": "0810.90",
}


def _suggest_for_issue(issue: str, crop: str) -> str:
    issue = issue.strip()

    if issue.startswith("Missing: hs_code"):
        code = HS_CODE_MAP.get(crop)
        if code:
            return f"HS Code is missing — for '{crop}' the correct code is {code}. Enter it in the Review & Fix form above."
        return f"HS Code is missing, and '{crop}' isn't in our HS code reference table — verify the correct code with KRA/KenTrade before entering it manually."

    if issue.startswith("Missing: gps"):
        return "GPS is missing — required for EUDR-regulated crops (Coffee/Tea/Maize). Capture it via the Farm Boundary walk tool, or ask the packhouse agent to record it at intake."

    if issue.startswith("Missing: packhouse"):
        return "Packhouse name is missing — enter which packhouse received this batch in the Review & Fix form above."

    if issue.startswith("Missing:"):
        field = issue.split("Missing:")[1].strip()
        return f"'{field}' is missing. This isn't editable from this form — it needs to be corrected at the source (Packhouse Intake or Data Ingestion), then re-audited."

    if issue.startswith("EUDR: GPS missing"):
        return "This crop requires GPS for EUDR compliance. Capture it via the Farm Boundary walk tool, or ask the packhouse agent to record it at intake."

    if issue.startswith("EUDR:") and "risk" in issue:
        risk_level = "RED" if "RED" in issue else "AMBER" if "AMBER" in issue else "elevated"
        return (f"This crop is flagged {risk_level} for EUDR deforestation risk. Before overriding, confirm you have "
                f"a Whisp/NDVI deforestation check attached via Farm Boundary Upload — overriding without it risks "
                f"rejection at the EU port.")

    if issue.startswith("MRL/PHI ZERO-TOLERANCE"):
        return ("This uses a chemical with ZERO tolerance for EU export — this is not a timing issue and cannot be "
                "resolved by waiting longer. Check the logged activity's photo to confirm the chemical/date weren't "
                "misrecorded. If confirmed, this batch should not proceed to export.")

    if issue.startswith("MRL/PHI VIOLATION"):
        match = re.search(r"needs (\d+)d before harvest, only (\d+)d elapsed", issue)
        if match:
            needed, elapsed = int(match.group(1)), int(match.group(2))
            remaining = needed - elapsed
            return (f"Pre-harvest interval not yet satisfied — wait {remaining} more day(s) before this batch can "
                    f"safely export, or verify the logged spray date against the activity's photo (a backdating "
                    f"error would also explain this).")
        return "Pre-harvest interval violation — review the linked spray date against the harvest date."

    return f"{issue} — needs manual review; no automated suggestion available for this issue type yet."


def suggest_fixes(audit_failure_reason: str, crop: str) -> list[str]:
    """Splits the semicolon-joined audit_failure_reason and returns one
    grounded suggestion per issue. Pure lookup/rules, no API call."""
    if not audit_failure_reason:
        return []
    issues = [i.strip() for i in audit_failure_reason.split(";") if i.strip()]
    return [_suggest_for_issue(i, crop) for i in issues]


def synthesize_action_plan(suggestions: list[str], farmer_name: str) -> str:
    """Optional: asks Claude to turn the already-correct suggestions into
    one short, prioritized paragraph. Explicitly instructed not to add new
    facts — only to rephrase/prioritize what's given. Falls back to the
    raw bullet list if the API call fails, so a compliance officer is
    never blocked from seeing the underlying facts."""
    if not suggestions:
        return ""
    try:
        bullet_list = "\n".join(f"- {s}" for s in suggestions)
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=(
                "You are helping a compliance officer at a Kenyan produce exporter quickly understand "
                "what to do about a flagged shipment batch. You will be given a list of already-verified "
                "facts and recommended actions. Rewrite them as ONE short, clear paragraph (3-5 sentences), "
                "in plain language, ordered by urgency (safety/legal issues before missing-data issues). "
                "Do NOT add any new facts, numbers, or recommendations beyond what is given. "
                "Do NOT soften or omit any zero-tolerance or EUDR risk warnings."
            ),
            messages=[{"role": "user", "content": f"Farmer: {farmer_name}\n\nFacts and recommendations:\n{bullet_list}"}]
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
    except Exception as e:
        return "\n".join(f"• {s}" for s in suggestions) + f"\n\n(AI summary unavailable: {str(e)})"
