import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_bluebird_form_submit():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(locale="en-US")
        
        # Monitor all requests and navigations
        page.on("request", lambda r: print(f">> Request: {r.method} {r.url[:120]}"))
        page.on("response", lambda r: print(f"<< Response: {r.status} {r.url[:120]}"))
        
        await page.goto("https://www.bluebirdair.com/", wait_until="networkidle", timeout=25000)
        
        # Check how flightFrom, flightTo, flightDepart are filled and submitted
        btn = await page.query_selector("button:has-text('Search'), .searchFlight_btn, .btn_search, #btnSearch")
        print("Search button element:", btn)
        
        # Also check destination page button
        await page.goto("https://booking.bluebirdair.com/Destinations/VIENNA", wait_until="networkidle", timeout=25000)
        btn_dest = await page.query_selector("button:has-text('Search'), input[type='submit'], .btn_search")
        print("Dest search button element:", btn_dest)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_bluebird_form_submit())
