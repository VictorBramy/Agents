import asyncio
from playwright.async_api import async_playwright

async def test_direct_airlines():
    urls = [
        ("Wizz Air", "https://wizzair.com/en-gb/booking/select-flight/TLV/VIE/2026-11-26/2026-11-30/1/0/0/null"),
        ("Kiwi Deep", "https://www.kiwi.com/deep?from=TLV&to=VIE&departure=2026-11-26&return=2026-11-30&currency=ILS"),
        ("Google Flights Direct", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30&curr=ILS&hl=iw")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for name, url in urls:
            try:
                print(f"\nTesting {name}: {url}")
                await page.goto(url, wait_until="load", timeout=15000)
                await page.wait_for_timeout(3000)
                print(f"[{name}] final URL: {page.url}")
                title = await page.title()
                print(f"[{name}] title: {title}")
                text = await page.inner_text("body")
                has_dates = "26" in text and ("11" in text or "נוב" in text or "Nov" in text)
                print(f"[{name}] has_dates={has_dates}")
            except Exception as e:
                print(f"[{name}] Error: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_direct_airlines())
