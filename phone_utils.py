"""
VeriPath — phone number normalization to E.164 for Africa's Talking / SMS delivery.
"""

import re


def normalize_kenyan_phone(raw: str) -> str | None:
    """
    Converts common Kenyan phone formats to E.164 (+254XXXXXXXXX).
    Returns None if the input can't be confidently normalized.

    Handles:
      0746098485   -> +254746098485
      +254114119015 -> +254114119015 (unchanged)
      254746098485  -> +254746098485
      746098485     -> +254746098485
    """
    if not raw:
        return None

    digits = re.sub(r"[^\d+]", "", raw.strip())

    if digits.startswith("+254") and len(digits) == 13:
        return digits
    if digits.startswith("254") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 10:
        return "+254" + digits[1:]
    if len(digits) == 9 and digits.startswith(("7", "1")):
        return "+254" + digits

    return None  # unrecognized format — flag for manual review rather than guess
