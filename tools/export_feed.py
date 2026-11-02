import os, sys, json, requests
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

URL = os.environ["SUPABASE_URL"].rstrip("/")
ANON = os.environ["SUPABASE_ANON_KEY"]
H = {"apikey": ANON, "Authorization": f"Bearer {ANON}"}
SLUG = sys.argv[1] if len(sys.argv) > 1 else "test-farm"
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/oldapash-site/data.json")
PREFIX = f"{URL}/storage/v1/object/public/listing-photos/"
FORBIDDEN = {"animal_tag", "company", "owner_username", "farm_location"}

def get(path):
    r = requests.get(f"{URL}/rest/v1/{path}", headers=H, timeout=30)
    r.raise_for_status()
    return r.json()

farms = get(f"public_farm_profiles?select=*&slug=eq.{SLUG}")
assert farms, f"farm '{SLUG}' not visible to anon (is_public must be true)"
f = farms[0]
rows = get(f"public_listings?select=*&farm_id=eq.{f['id']}&order=published_at.desc")

feed = {
  "farm": {k: f.get(k) for k in ("display_name","tagline","county","whatsapp_number","about")},
  "listings": [
    {"public_id": r["public_id"], "title": r.get("title"), "species": r.get("species"),
     "breed": r.get("breed"), "sex": r.get("sex"), "purpose": r.get("purpose"),
     "description": r.get("description"), "status": r.get("status"),
     "photos": [PREFIX + p for p in (r.get("photo_paths") or [])]}
    for r in rows
  ],
}
# Merge: keep fields that only live in data.json (contact, stats, inspiration,
# blurb, ...). DB values overwrite only when non-empty; gallery comes from DB.
try:
    existing = json.load(open(OUT)).get("farm", {})
except Exception:
    existing = {}
merged = dict(existing)
for k, v in feed["farm"].items():
    if v:
        merged[k] = v
merged["gallery"] = [PREFIX + p for p in (f.get("gallery_paths") or [])]
feed["farm"] = merged
blob = json.dumps(feed)
for bad in FORBIDDEN:
    assert bad not in blob, f"forbidden field '{bad}' present in feed"
json.dump(feed, open(OUT, "w"), indent=2)
print(f"wrote {OUT}: {len(feed['listings'])} listing(s)")
