import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_bluebird_urls():
    candidates = [
        "https://booking.bluebirdair.com/flight-results/TLV-VIE/26-11-2026/30-11-2026/1/0/0",
        "https://booking.bluebirdair.com/flight-results/TLV-VIE/2026-11-26/2026-11-30/1/0/0",
        "https://booking.bluebirdair.com/flight-results/TLV-ATH/20-11-2026/27-11-2026/1/0/0",
        "https://booking.bluebirdair.com/flight-results/TLV-ATH/20-11-2026/1/0/0"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        for url in candidates:
            print(f"\nTesting: {url}")
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(3000)
                print("Status:", resp.status if resp else "None")
                print("Final URL:", page.url)
                print("Title:", await page.title())
                
                # Check text on page
                text = await page.inner_text("body")
                has_dates = "26" in text or "20" in text
                has_tlv = "TLV" in text or "Tel Aviv" in text
                print(f"Has dates: {has_dates}, Has TLV: {has_tlv}")
                
                # Look for flight cards or prices
                lines = [l.strip() for l in text.split("\n") if any(k in l for k in ["€", "$", "₪", "Select", "Flight", "Direct", "TLV", "ATH", "VIE"])][:6]
                print("Sample lines:", lines)
            except Exception as e:
                print(f"Error on {url}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_bluebird_urls())
