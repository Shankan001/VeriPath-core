with open("qr_generator.py","r") as f:
    content = f.read()

old = '''                all_farmers = load_farmers()
                all_farmers[farmer_id] = farmer_data
                from ledger_db import save_farmers as _sf
                import os, json
                os.makedirs("data", exist_ok=True)
                with open(os.path.join("data","farmers.json"),"w") as f:
                    json.dump(all_farmers, f, indent=2)'''

new = '''                from supabase_db import save_farmer_db
                save_farmer_db(farmer_id, farmer_data)'''

if old in content:
    content = content.replace(old, new)
    print("✅ qr_generator save patched to Supabase")
else:
    print("❌ Save block not found")

with open("qr_generator.py","w") as f:
    f.write(content)
