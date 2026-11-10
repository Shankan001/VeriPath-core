"""
Removes ledger rows with crop 'Unknown' and an implausible weight_kg,
left behind by an earlier parsing bug. Affects all companies; admin use only.

Dry run by default: only lists what would be deleted.
Pass --confirm to actually delete.

Usage:
    python cleanup_bad_weights.py             # dry run
    python cleanup_bad_weights.py --confirm   # delete
"""

import sys
from supabase_db import get_client

MAX_PLAUSIBLE_WEIGHT_KG = 50000

def main():
    confirm = "--confirm" in sys.argv
    supabase = get_client()

    rows = supabase.table("ledger").select("*").execute().data or []
    bad_rows = [
        r for r in rows
        if r.get("crop") == "Unknown" and (r.get("weight_kg") or 0) > MAX_PLAUSIBLE_WEIGHT_KG
    ]

    if not bad_rows:
        print("No matching bad rows found. Nothing to clean up.")
        return

    print(f"Found {len(bad_rows)} matching row(s):\n")
    for r in bad_rows:
        print(f"  id={r['id']:>4}  company={r.get('company',''):<15}  "
              f"farmer={r.get('farmer_name',''):<20}  weight_kg={r.get('weight_kg')}  "
              f"intake_date={r.get('intake_date')}")

    if not confirm:
        print(f"\nDRY RUN — nothing deleted. Re-run with --confirm to actually delete these {len(bad_rows)} row(s).")
        return

    print(f"\nDeleting {len(bad_rows)} row(s)...")
    for r in bad_rows:
        supabase.table("ledger").delete().eq("id", r["id"]).execute()
        print(f"  deleted id={r['id']}")

    print("\n✅ Cleanup complete.")


if __name__ == "__main__":
    main()
