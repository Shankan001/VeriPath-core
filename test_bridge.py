from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Go to a site (let's use Google for the test)
        print("Connecting to the web...")
        page.goto("https://google.com")
        
        # Take a screenshot as proof
        page.screenshot(path="proof.png")
        print("Success! 'proof.png' saved. The bridge is open.")
        
        browser.close()

if __name__ == "__main__":
    run()
