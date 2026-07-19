"""
VeriPath — Self-Service Password Reset
User enters their username, receives a 6-digit SMS code (via Africa's
Talking), enters it plus a new password to complete the reset.
Works uniformly across all roles/modules since it's built on the shared
users table and _hash_password() logic.
"""

import os
import random
import string
import requests
from datetime import datetime, timedelta, timezone
from supabase_db import get_client, get_user
from auth import _hash_password
from security import validate_password_strength

RESET_CODE_LENGTH = 6
RESET_CODE_EXPIRY_MINUTES = 10

AT_API_KEY = os.environ.get("AT_API_KEY", "")
AT_USERNAME = os.environ.get("AT_USERNAME", "sandbox")
AT_SMS_URL = (
    "https://api.sandbox.africastalking.com/version1/messaging"
    if AT_USERNAME == "sandbox"
    else "https://api.africastalking.com/version1/messaging"
)


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=RESET_CODE_LENGTH))


def _send_sms(phone: str, message: str) -> bool:
    try:
        headers = {
            "apiKey": AT_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        payload = {"username": AT_USERNAME, "to": phone, "message": message}
        resp = requests.post(AT_SMS_URL, data=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Reset] SMS send error: {e}")
        return False


def request_password_reset(username: str) -> tuple[bool, str]:
    """
    Step 1: user enters username. Looks up phone, generates + sends code.
    Always returns a generic message on failure (don't reveal whether a
    username exists, to avoid username enumeration).
    """
    username = username.strip().lower()
    user = get_user(username)
    generic_msg = "If that username exists, a reset code has been sent to the phone on file."

    if not user:
        return True, generic_msg  # don't reveal non-existence

    phone = user.get("phone", "")
    if not phone:
        return False, (
            "No phone number is on file for this account. "
            "Please contact your company admin or VeriPath support to reset your password."
        )

    code = _generate_code()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_EXPIRY_MINUTES)).isoformat()

    try:
        get_client().table("password_reset_codes").insert({
            "username": username,
            "code": code,
            "expires_at": expires_at,
        }).execute()
    except Exception as e:
        print(f"[Reset] Failed to store reset code: {e}")
        return False, "Something went wrong. Please try again."

    message = f"VeriPath password reset code: {code}. Valid for {RESET_CODE_EXPIRY_MINUTES} minutes. Do not share this code."
    sent = _send_sms(phone, message)
    if not sent:
        return False, "Failed to send SMS. Please try again or contact support."

    return True, generic_msg


def verify_and_reset_password(username: str, code: str, new_password: str) -> tuple[bool, str]:
    """Step 2: user enters the code + new password to complete the reset."""
    username = username.strip().lower()
    code = code.strip()

    valid_p, err_p = validate_password_strength(new_password)
    if not valid_p:
        return False, err_p

    try:
        rows = get_client().table("password_reset_codes").select("*").eq(
            "username", username
        ).eq("code", code).eq("used", False).order(
            "created_at", desc=True
        ).limit(1).execute().data
    except Exception as e:
        print(f"[Reset] Failed to look up reset code: {e}")
        return False, "Something went wrong. Please try again."

    if not rows:
        return False, "Invalid or already-used reset code."

    reset_row = rows[0]
    expires_at = datetime.fromisoformat(reset_row["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        return False, "This reset code has expired. Please request a new one."

    hashed, salt = _hash_password(new_password)
    try:
        get_client().table("users").update({
            "password": hashed,
            "salt": salt,
        }).eq("username", username).execute()

        get_client().table("password_reset_codes").update({
            "used": True
        }).eq("id", reset_row["id"]).execute()
    except Exception as e:
        print(f"[Reset] Failed to update password: {e}")
        return False, "Something went wrong. Please try again."

    return True, "✅ Password reset successfully. You can now sign in."
