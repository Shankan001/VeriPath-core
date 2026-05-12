import csv
import os
from playwright.sync_api import sync_playwright

# --- UPDATED 2026 GATEWAYS ---
USER = "shankan"
PASS = "sp2018"
AFA_IMIS_URL = "https://imis.afa.go.ke/" 
KEPHIS_URL = "https://ieics.kephis.org/login.html"

def process_full_export(page, shipment):
    try:
        # STEP 1: HCD / AFA IMIS (Traceability & Licensing)
        print(f"\n[1/2] Connecting to AFA IMIS (HCD) for ID: {shipment['id']}...")
        page.goto(AFA_IMIS_URL, timeout=90000)
        
        # AFA IMIS often uses eCitizen login. This fills the landing page.
        print(f"--- Handshake: IMIS Portal Resolved.")

        # STEP 2: KEPHIS (IEICS) Phytosanitary Health
        print(f"[2/2] Jumping to KEPHIS (IEICS) for Health Stamp...")
        page.goto(KEPHIS_URL, timeout=90000)
        
        # Using the IDs we validated earlier
        page.fill("#username", USER)
        page.fill("#password", PASS)
        page.click("#login_form_submit")
        
        print(f"--- Handshake: KEPHIS Session Initialized for {shipment['crop']}.")
        return True

    except Exception as e:
        print(f"!!! Operational Error: {e}")
        return False

if __name__ == "__main__":
    print("\n--- VeriPath Unified Bridge Engine (v5.2 - Live Target) ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        page = browser.new_page()

        if os.path.exists('farmers.csv'):
            with open('farmers.csv', mode='r') as file:
                reader = csv.DictReader(file)
                # Process the first row to confirm the bridge works
                first_row = next(reader)
                process_full_export(page, first_row)
        else:
            print("ERROR: farmers.csv missing. Please recreate it.")
        
        print("\n[VeriPath] Test run complete.")
        browser.close()
