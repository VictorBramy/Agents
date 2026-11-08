import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_elal_booking():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(locale="he-IL")
        
        # Test El Al search URL patterns
        # Standard El Al Amadeus / custom IBE URL patterns:
        test_urls = [
            "https://www.elal.com/heb/israel",
            "https://booking.elal.com/booking/flights?origin=TLV&destination=VIE&outboundDate=2026-11-26&inboundDate=2026-11-30&adults=1",
            "https://flights.elal.com/he-il/flights-from-tel-aviv-to-vienna"
        ]
        for u in test_urls:
            print(f"\nVisiting: {u}")
            try:
                resp = await page.goto(u, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                print("Final URL:", page.url)
                print("Status:", resp.status if resp else "None")
                print("Title:", await page.title())
            except Exception as e:
                print("Error:", e)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_elal_booking())
