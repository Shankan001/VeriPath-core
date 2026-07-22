with open("whisp_check.py", "r") as f:
    content = f.read()

old = '''import os
import time
import requests

WHISP_API_KEY = os.environ.get("WHISP_API_KEY", "")'''

new = '''import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

WHISP_API_KEY = os.environ.get("WHISP_API_KEY", "")'''

if old not in content:
    print("ERROR: target not found — no changes made.")
else:
    content = content.replace(old, new)
    with open("whisp_check.py", "w") as f:
        f.write(content)
    print("Patched — whisp_check.py now loads .env directly.")
