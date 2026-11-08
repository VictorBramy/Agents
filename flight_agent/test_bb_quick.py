import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_bb_quick():
    urls = [
        ("Format DD-MM-YYYY", "https://booking.bluebirdair.com/flight-results/TLV-VIE/26-11-2026/30-11-2026/1/0/0"),
        ("Format YYYY-MM-DD", "https://booking.bluebirdair.com/flight-results/TLV-VIE/2026-11-26/2026-11-30/1/0/0"),
        ("Destination Page", "https://booking.bluebirdair.com/Destinations/VIENNA")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        for label, url in urls:
            print(f"\n--- Testing {label}: {url} ---")
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                await page.wait_for_timeout(3000)
                print("Final URL:", page.url)
                print("Title:", await page.title())
                
                # Check inputs flightFrom, flightTo, flightDepart, flightReturn
                vals = await page.evaluate("""() => {
                    return {
                        flightFrom: document.getElementById('flightFrom') ? document.getElementById('flightFrom').value : null,
                        flightTo: document.getElementById('flightTo') ? document.getElementById('flightTo').value : null,
                        flightDepart: document.getElementById('flightDepart') ? document.getElementById('flightDepart').value : null,
                        flightReturn: document.getElementById('flightReturn') ? document.getElementById('flightReturn').value : null,
                        bodySample: document.body.innerText.slice(0, 300).replace(/\\n/g, ' ')
                    };
                }""")
                print("Extracted values:", vals)
            except Exception as e:
                print("Error:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_bb_quick())
