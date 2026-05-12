import os
from playwright.sync_api import sync_playwright

# THE REAL DEAL: IEICS Portal
TARGET_URL = "https://ieics.kephis.org/login.html" 
USER = "shankan"
PASS = "sp2018"

def run_test():
    with sync_playwright() as p:
        print(f"\n--- VeriPath Live Target Test (IEICS KEPHIS) ---")
        # Headless=False so you can see the bot in action
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        page = browser.new_page()
        
        try:
            print(f"[1/3] Navigating to: {TARGET_URL}")
            page.goto(TARGET_URL, timeout=90000, wait_until="networkidle")
            
            print(f"[2/3] Injecting Credentials into Live Fields...")
            
            # Using the IDs you found: #username and #password
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", USER)
            page.fill("#password", PASS)
            
            print(f"[3/3] Clicking Log In (#login_form_submit)...")
            # Using the exact ID from your scrape: login_form_submit
            page.click("#login_form_submit")
            
            # Watch for the result
            print("[VeriPath] Watching for Dashboard or Error message...")
            page.wait_for_timeout(7000)
            
            final_url = page.url
            print(f"Post-Login URL: {final_url}")
            
            if "login" not in final_url.lower():
                print("!!! SUCCESS: We are past the front gate!")
            else:
                print("!!! STATUS: Still on login page. Likely invalid credentials.")
            
        except Exception as e:
            print(f"!!! TARGET ERROR: {e}")
            
        finally:
            print("Test complete. VeriPath Engine standing by.")
            browser.close()

if __name__ == "__main__":
    run_test()
