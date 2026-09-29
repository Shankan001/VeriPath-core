"""
test_otp_login.py — standalone test of the full chain:
Supabase Auth -> Send SMS Hook -> Edge Function -> Africa's Talking -> your phone

Does NOT touch the Streamlit app. Just proves the auth flow itself works,
end to end, with a real SMS landing on a real phone.

USAGE:
  pip install supabase python-dotenv --break-system-packages
  python3 test_otp_login.py +254796130512

Needs SUPABASE_URL and SUPABASE_ANON_KEY (the anon/public key, NOT the
service key — auth sign-in should always go through the anon key) set as
environment variables, or in a .env file in the same folder.

IMPORTANT: this uses your PRODUCTION Africa's Talking config if AT_BASE_URL
was ever switched off sandbox. If you're still on sandbox mode from earlier
testing, this OTP will NOT arrive as a real SMS (same sandbox limitation as
before) - only the API call chain will be verified. Switch AT_BASE_URL /
AT_USERNAME / AT_API_KEY to your live Africa's Talking app first if you want
a real text to land on your phone.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment/.env")
    print("Get these from: Supabase Dashboard -> Project Settings -> API")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python3 test_otp_login.py +254XXXXXXXXX")
    sys.exit(1)

phone = sys.argv[1]

client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

print(f"Requesting OTP for {phone} ...")
try:
    client.auth.sign_in_with_otp({"phone": phone})
    print("Request sent. Check your phone for the SMS.")
except Exception as e:
    print("FAILED to request OTP:")
    print(e)
    sys.exit(1)

code = input("Enter the code you received (or leave blank to stop here): ").strip()

if not code:
    print("Stopping - no code entered. That's fine if you just wanted to confirm the request step worked.")
    sys.exit(0)

print("Verifying code ...")
try:
    result = client.auth.verify_otp({"phone": phone, "token": code, "type": "sms"})
    print("SUCCESS - real session issued:")
    print(f"  user id: {result.user.id}")
    print(f"  phone:   {result.user.phone}")
    print(f"  access_token (first 40 chars): {result.session.access_token[:40]}...")
except Exception as e:
    print("FAILED to verify code:")
    print(e)
    sys.exit(1)
