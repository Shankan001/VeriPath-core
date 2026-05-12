import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        # Launching with a slower internal clock to handle portal redirects
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("🚀 Navigating to the TFP Sign-in Gateway...")
        try:
            # We target the direct signin URL you provided
            await page.goto("https://tfp.kenyatradenet.go.ke/TFBSEW/cusLogin/signin.cl", timeout=60000)

            print("🔎 Waiting for #j_username to appear...")
            # This is the 'Force' move: wait up to 20 seconds specifically for the box
            await page.wait_for_selector('#j_username', state="visible", timeout=20000)

            print("🔑 Injecting dummy credentials...")
            await page.fill('#j_username', 'DUMMY_USER_DDEC')
            await page.fill('#j_password', 'DUMMY_PASS_330i')
            
            print("🖱️ Engaging #tfpLoginBtn...")
            await page.click('#tfpLoginBtn')
            
            # Final proof capture
            await page.wait_for_timeout(5000)
            await page.screenshot(path="kentrade_proof.png")
            print("📸 Captured! Check 'kentrade_proof.png' in your Thunar window.")
            
        except Exception as e:
            print(f"⚠️ Debug: At time of error, URL was {page.url}")
            await page.screenshot(path="debug_error.png")
            print(f"⚠️ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
