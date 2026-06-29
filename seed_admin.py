"""
VeriPath — Seed admin account
Run once to create the first admin user.
Usage: python3 seed_admin.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from auth import register_user
from invite_codes import seed_admin_code

def main():
    print("\n🔑 VeriPath Admin Seeder")
    print("=" * 40)

    # Generate admin invite code
    code = seed_admin_code()
    if not code:
        print("❌ Could not generate admin code")
        return

    print(f"Admin invite code: {code}")
    print()

    username  = input("Admin username: ").strip()
    full_name = input("Full name: ").strip()
    company   = input("Company name: ").strip()
    password  = input("Password (min 10 chars, uppercase, number, special): ").strip()

    ok, msg = register_user(
        username  = username,
        password  = password,
        full_name = full_name,
        company   = company,
        role      = "admin",
        invite_code = code,
        module    = "🌿 VeriPath Crops",
    )
    if ok:
        print(f"\n✅ {msg}")
        print(f"   Username: {username}")
        print(f"   Role: admin")
    else:
        print(f"\n❌ {msg}")

if __name__ == "__main__":
    main()
