import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")  # Use service key for seeding
supabase = create_client(url, key)

# Insert VP-ADM invite code
result = supabase.table("invite_codes").upsert({
    "code": "VP-ADM-2024",
    "role": "admin",
    "used": False,
    "company_id": None
}).execute()

print("Invite code seeded:", result.data)
