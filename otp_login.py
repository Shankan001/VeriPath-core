"""
otp_login.py — Phone + OTP login via Supabase Auth (Send SMS Hook ->
Africa's Talking), matched against existing VeriPath users by phone number.

Does NOT replace username/password login or touch the app's own session
system — once the phone is verified via Supabase Auth, it looks up the
matching VeriPath user by phone and logs them into the EXISTING session
system (same as login_user() does), so nothing else in the app changes.
"""

import os
from supabase import create_client
from supabase_db import get_user_by_phone
from phone_utils import normalize_kenyan_phone
from security import log_security_event

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")


def _anon_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY not configured")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def request_otp(raw_phone: str) -> tuple[bool, str]:
    phone = normalize_kenyan_phone(raw_phone)
    if not phone:
        return False, "Enter a valid Kenyan phone number."

    try:
        client = _anon_client()
        client.auth.sign_in_with_otp({"phone": phone})
        return True, f"Code sent to {phone}."
    except Exception as e:
        print(f"[OTP] request error: {e}")
        return False, "Could not send code. Please try again."


def verify_otp_and_login(raw_phone: str, code: str) -> tuple[bool, str, dict | None]:
    phone = normalize_kenyan_phone(raw_phone)
    if not phone or not code.strip():
        return False, "Enter the phone number and the code you received.", None

    try:
        client = _anon_client()
        result = client.auth.verify_otp({"phone": phone, "token": code.strip(), "type": "sms"})
    except Exception as e:
        print(f"[OTP] verify error: {e}")
        return False, "Invalid or expired code.", None

    if not result or not result.user:
        return False, "Invalid or expired code.", None

    user = get_user_by_phone(phone)
    if not user:
        return False, (
            "Phone verified, but no VeriPath account is linked to this "
            "number yet. Register first, or contact support to link your "
            "existing account."
        ), None

    log_security_event("otp_login_success", user.get("username", "?"),
                        f"Phone: {phone}", True)

    profile = {k: v for k, v in user.items() if k not in ("password", "salt")}
    return True, f"Welcome back, {profile.get('full_name', profile.get('username',''))}.", profile
