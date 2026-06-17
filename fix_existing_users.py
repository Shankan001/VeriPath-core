import json
import os

USERS_FILE = "data/users.json"

with open(USERS_FILE, "r") as f:
    users = json.load(f)

patched = 0
for username, user in users.items():
    changed = False
    if "subscription_tier" not in user:
        user["subscription_tier"] = "trial"
        changed = True
    if "containers_used" not in user:
        user["containers_used"] = 0
        changed = True
    if "invite_code_used" not in user:
        user["invite_code_used"] = "LEGACY"
        changed = True
    if changed:
        patched += 1
        print(f"  ✅ Patched: {username}")

with open(USERS_FILE, "w") as f:
    json.dump(users, f, indent=2)

print(f"\nDone. {patched} user(s) patched.")
