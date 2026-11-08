import asyncio
from playwright.async_api import async_playwright

async def verify_google_query_url():
    tests = [
        ("General TLV-VIE", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30&curr=ILS&hl=iw"),
        ("El Al TLV-VIE", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+El+Al&curr=ILS&hl=iw"),
        ("Blue Bird TLV-VIE", "https://www.google.com/travel/flights?q=flights+from+TLV+to+VIE+on+2026-11-26+through+2026-11-30+with+Blue+Bird+Airways&curr=ILS&hl=iw")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="he-IL")
        for name, url in tests:
            print(f"\nVerifying {name}...")
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2500)
            
            # Extract inputs or headings
            text = await page.inner_text("body")
            
            # Check for dates
            has_dep = "26" in text
            has_ret = "30" in text
            # Check for TLV and VIE
            has_tlv = "תל אביב" in text or "TLV" in text
            has_vie = "וינה" in text or "VIE" in text
            
            print(f"[{name}] Results:")
            print(f"  - Departure date 26: {has_dep}")
            print(f"  - Return date 30: {has_ret}")
            print(f"  - TLV present: {has_tlv}")
            print(f"  - VIE present: {has_vie}")
            
            # Check if there are flight cards
            flight_elements = await page.query_selector_all("[role='listitem'], li")
            print(f"  - List elements found: {len(flight_elements)}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_google_query_url())
