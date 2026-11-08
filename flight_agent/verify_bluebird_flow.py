import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def verify_bluebird_direct_booking():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(locale="he-IL")
        page = await context.new_page()
        
        print("1. Opening http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle", timeout=15000)
        
        prompt = "טיסות לוינה מ-26 בנובמבר 2026 עד 30 בנובמבר 2026 הלוך ושוב"
        print(f"2. Searching with prompt: '{prompt}'...")
        await page.fill("#aiPromptInput", prompt)
        await page.click("#btnAiSearch")
        
        print("3. Waiting for flight results...")
        await page.wait_for_selector("#flightsContainer > div", timeout=45000)
        
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"Total cards rendered: {len(cards)}")
        
        # Find Blue Bird card
        bb_card = None
        for c in cards:
            airline_el = await c.query_selector(".font-black.text-base")
            if airline_el:
                name = await airline_el.inner_text()
                if "בלו בירד" in name or "Blue Bird" in name or "bluebird" in name.lower():
                    bb_card = c
                    break
                    
        assert bb_card is not None, "Blue Bird card was not found in results!"
        print("Found Blue Bird flight card!")
        
        # Check booking button on Blue Bird card
        booking_btn = await bb_card.query_selector("a[title*='מעבר ישיר להזמנת הטיסה באתר']")
        assert booking_btn is not None, "Booking button not found on Blue Bird card!"
        
        href = await booking_btn.get_attribute("href")
        print(f"Blue Bird Booking Button Href: {href}")
        
        # ASSERT: Must point to booking.bluebirdair.com, NOT google.com!
        assert "booking.bluebirdair.com" in href, f"Href does not point to Blue Bird: {href}"
        assert "google.com" not in href, f"Href mistakenly points to Google: {href}"
        assert "2026-11-26" in href or "26-11-2026" in href or "26/11/2026" in href, "Departure date missing from Blue Bird link!"
        assert "2026-11-30" in href or "30-11-2026" in href or "30/11/2026" in href, "Return date missing from Blue Bird link!"
        assert "TLV" in href, "TLV missing from Blue Bird link!"
        assert "VIE" in href, "VIE missing from Blue Bird link!"
        
        # Also check that Google Flights comparison button is available separately
        gf_btn = await bb_card.query_selector("a[title*='Google Flights']")
        assert gf_btn is not None, "Google Flights comparison button missing on card!"
        gf_href = await gf_btn.get_attribute("href")
        print(f"Google Flights Comparison Href: {gf_href[:80]}...")
        assert "google.com" in gf_href, "Google comparison link not pointing to google!"
        
        print("4. Physically opening Blue Bird booking URL in a new page...")
        bb_page = await context.new_page()
        resp = await bb_page.goto(href, wait_until="domcontentloaded", timeout=25000)
        await bb_page.wait_for_timeout(3000)
        
        print("Target URL:", bb_page.url)
        print("Target Title:", await bb_page.title())
        assert "bluebirdair.com" in bb_page.url, "Target page is not bluebirdair.com!"
        
        print("\n=======================================================")
        print("VERIFICATION SUCCEEDED: BLUE BIRD DIRECT BOOKING WORKS 100%!")
        print("=======================================================")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_bluebird_direct_booking())
