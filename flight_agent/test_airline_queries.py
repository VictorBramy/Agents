import asyncio
from playwright.async_api import async_playwright

async def test_gf_airline_query():
    queries = [
        ("El Al", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+El+Al&curr=ILS&hl=iw"),
        ("Blue Bird", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+Blue+Bird+Airways&curr=ILS&hl=iw"),
        ("Israir", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+Israir&curr=ILS&hl=iw"),
        ("Arkia", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+Arkia&curr=ILS&hl=iw"),
        ("Wizz Air", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+Wizz+Air&curr=ILS&hl=iw")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for name, url in queries:
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(2000)
                text = await page.inner_text("body")
                has_dates = ("26" in text and "30" in text)
                has_airline = (name.lower() in text.lower() or "אל על" in text or "ישראייר" in text or "ארקיע" in text)
                print(f"[{name}] final_url: {page.url[:110]}")
                print(f"[{name}] has_dates={has_dates}, has_airline={has_airline}")
                lines = [l.strip() for l in text.split("\n") if any(k in l for k in ["טיס", "₪", "26", "30", "בחר"])][:5]
                print(f"[{name}] lines: {lines}")
            except Exception as e:
                print(f"[{name}] Error: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_gf_airline_query())
