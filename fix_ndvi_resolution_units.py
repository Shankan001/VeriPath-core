with open("ndvi_tracker.py", "r") as f:
    content = f.read()

old = '''            "aggregationInterval": {"of": "P14D"},
            "evalscript": evalscript,
            "resx": 10,
            "resy": 10
        }'''

new = '''            "aggregationInterval": {"of": "P14D"},
            "evalscript": evalscript,
            "resx": 0.00009,
            "resy": 0.00009
        }'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("ndvi_tracker.py", "w") as f:
        f.write(content)
    print("Patched — resolution now expressed in degrees, matching CRS84 units.")
