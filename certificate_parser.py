"""
VeriPath Regulatory Certificate Vault — Stage 3
Sends extracted certificate text to Claude and gets back structured JSON.
Depends on Stage 2 (pdf_extract.py) for the input text.
"""
import json
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Model choice: Sonnet handles the inconsistent formatting of real-world
# government certificates (scanned-then-OCR'd text, inconsistent spacing,
# stamps/signatures breaking up text) more reliably than Haiku.
# Swap to "claude-haiku-4-5-20251001" later if cost becomes a concern
# once volume is high and formats are proven consistent.
MODEL = "claude-sonnet-5"

FIELD_SCHEMAS = {
    "HCD_EXPORT_LICENCE": """
Extract these fields from this Horticultural Crops Directorate (HCD) export licence:
- document_number: the licence number
- holder_name: the exporter/company name the licence is issued to
- volume_or_weight: the maximum export volume/quota stated (numeric only)
- volume_unit: the unit for that volume (kg, tonnes, cartons, etc.)
- issue_date: date issued, format YYYY-MM-DD
- expiry_date: date it expires, format YYYY-MM-DD
- crop_type: what crop/produce this licence covers
""",
    "KEPHIS_PHYTOSANITARY": """
Extract these fields from this KEPHIS phytosanitary certificate:
- document_number: the certificate number
- holder_name: the exporter name on the certificate
- volume_or_weight: the consignment weight/quantity stated (numeric only)
- volume_unit: the unit (kg, cartons, etc.)
- issue_date: date issued, format YYYY-MM-DD
- expiry_date: date it expires or validity period ends, format YYYY-MM-DD
- destination_country: country the consignment is destined for
- botanical_name: the botanical/scientific name of the produce, if stated
""",
    "KRA_CERTIFICATE_ORIGIN": """
Extract these fields from this KRA Certificate of Origin:
- document_number: the certificate reference number
- holder_name: the exporter/company name
- volume_or_weight: consignment weight if stated (numeric only, else null)
- volume_unit: the unit, if stated
- issue_date: date issued, format YYYY-MM-DD
- expiry_date: if stated, else null
- origin_location: the farm/county/region of origin stated on the certificate
""",
    "GLOBALGAP_MRL": """
Extract these fields from this GlobalG.A.P / MRL (Maximum Residue Limit) test certificate:
- document_number: the certificate/report number
- holder_name: the farm or outgrower name being certified
- volume_or_weight: sample size tested, if stated (numeric only, else null)
- volume_unit: the unit, if stated
- issue_date: date issued, format YYYY-MM-DD
- expiry_date: certificate validity end date, format YYYY-MM-DD
- crop_type: the crop tested
- mrl_result: "PASS" or "FAIL" based on whether residue levels were within limits
- flagged_substances: list of any specific chemicals/substances that exceeded limits, if any (empty list if none)
"""
}


def parse_certificate(text: str, document_type: str) -> dict:
    """
    Sends extracted certificate text to Claude, returns structured data.
    """
    if document_type not in FIELD_SCHEMAS:
        return {"success": False, "data": None, "error": f"Unknown document_type: {document_type}"}

    field_instructions = FIELD_SCHEMAS[document_type]

    system_prompt = f"""You are extracting structured data from a Kenyan agricultural export regulatory document.

{field_instructions}

Respond with ONLY a valid JSON object containing exactly those fields — no preamble, no markdown code fences, no explanation.
If a field cannot be found in the text, use null for that field.
Dates must be in YYYY-MM-DD format or null.
Numeric fields must be numbers, not strings, or null.
"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Document text:\n\n{text}"}]
        )

        raw_output = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)

        return {"success": True, "data": parsed, "error": None}

    except json.JSONDecodeError as e:
        return {"success": False, "data": None, "error": f"Claude returned non-JSON output: {str(e)} | raw: {raw_output[:300]}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"API call failed: {str(e)}"}
