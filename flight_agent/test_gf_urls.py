import asyncio
from playwright.async_api import async_playwright

async def test_gf_urls():
    candidates = [
        ("Query params", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30&curr=ILS&hl=iw"),
        ("Hash flt format", "https://www.google.com/travel/flights#flt=TLV.VIE.2026-11-26*VIE.TLV.2026-11-30;c:ILS;e:1;sd:1;t:f"),
        ("Skyscanner IL", "https://www.skyscanner.co.il/transport/flights/tlv/vie/261126/261130/?adultsv2=1&cabinclass=economy&childrenv2=&ref=home"),
        ("Kayak", "https://www.kayak.co.il/flights/TLV-VIE/2026-11-26/2026-11-30?sort=price_a")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for name, url in candidates:
            print(f"\nTesting {name}: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(3000)
                text = await page.inner_text("body")
                has_dates = ("26" in text and "30" in text)
                has_nov = ("נובמבר" in text or "Nov" in text or "11" in text)
                has_flights = ("₪" in text or "טיסה" in text or "בחר" in text)
                print(f"[{name}] final_url: {page.url[:100]}")
                print(f"[{name}] has_dates={has_dates}, has_nov={has_nov}, has_flights={has_flights}")
                # Print any flight cards text or summary
                lines = [l.strip() for l in text.split("\n") if "26" in l or "נוב" in l or "Nov" in l][:4]
                print(f"[{name}] sample lines:", lines)
            except Exception as e:
                print(f"[{name}] Error: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_gf_urls())
