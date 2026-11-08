import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_js_files():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Fetch scripts
        for script_url in [
            "https://booking.bluebirdair.com/resources/aeroCRS.js",
            "https://booking.bluebirdair.com/resources/functions.js",
            "https://booking.bluebirdair.com/scripts/general/content.js"
        ]:
            print(f"\n--- Fetching {script_url} ---")
            resp = await page.goto(script_url)
            text = await resp.text()
            print(f"Length: {len(text)}")
            
            # Look for URL params, window.location.search, or 'from', 'to', 'flightFrom'
            lines = text.split("\n")
            for line in lines:
                if any(w in line for w in ["location.search", "URLSearchParams", "flightFrom", "flightTo", "flightDepart", "flightReturn", "getQueryVariable", "getUrlParameter", "GetURLParameter"]):
                    print("Match:", line.strip()[:180])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_js_files())
