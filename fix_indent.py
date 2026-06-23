with open("app.py","r") as f:
    content = f.read()

old = '''        for _, row in df.iterrows():
            _c = row.get("county", row.get("Origin_County",""))
                coords = COUNTY_COORDS.get(_c, (-0.0236, 37.9062))
            map_data.append({'''

new = '''        for _, row in df.iterrows():
            _c = row.get("county", row.get("Origin_County",""))
            coords = COUNTY_COORDS.get(_c, (-0.0236, 37.9062))
            map_data.append({'''

if old in content:
    content = content.replace(old, new)
    print("✅ Indentation fixed")
else:
    print("❌ Block not found")

with open("app.py","w") as f:
    f.write(content)
