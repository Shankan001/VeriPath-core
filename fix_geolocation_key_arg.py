with open("farm_boundary_upload.py", "r") as f:
    content = f.read()

old = 'current_loc = get_geolocation(key=f"geo_{len(st.session_state[\'boundary_points\'])}")'
new = 'current_loc = get_geolocation()'

if old not in content:
    print("ERROR: target line not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("farm_boundary_upload.py", "w") as f:
        f.write(content)
    print("Patched successfully — removed invalid key argument.")
