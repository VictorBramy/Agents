import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_ui_flight_card_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="he-IL")
        page = await context.new_page()
        
        print("1. Navigating to http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle", timeout=15000)
        
        print("2. Submitting search for TLV -> VIE (2026-11-26 to 2026-11-30)...")
        await page.fill("#filterDestination", "VIE")
        await page.fill("#filterDepDate", "2026-11-26")
        await page.fill("#filterRetDate", "2026-11-30")
        
        # Click search
        await page.click("button:has-text('סרוק בכל המנועים')")
        
        # Wait for resultsSection to become visible
        print("3. Waiting for search results to load...")
        await page.wait_for_selector("#flightsContainer > div", timeout=45000)
        
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"Total rendered flight cards: {len(cards)}")
        assert len(cards) > 0, "No cards rendered"
        
        # Get booking buttons
        first_card = cards[0]
        airline_name = await (await first_card.query_selector(".font-black.text-base")).inner_text()
        print(f"First Card Airline: {airline_name}")
        
        booking_btn = await first_card.query_selector("a[title*='מעבר ישיר להזמנת הטיסה']")
        assert booking_btn is not None, "Booking button not found on first card!"
        
        book_href = await booking_btn.get_attribute("href")
        print(f"Booking Button Href: {book_href}")
        
        # Verify href contains prompt dates and route
        assert "2026-11-26" in book_href or "261126" in book_href, "Prompt departure date missing from href!"
        assert "2026-11-30" in book_href or "261130" in book_href, "Prompt return date missing from href!"
        assert "TLV" in book_href, "TLV missing from href!"
        assert "VIE" in book_href, "VIE missing from href!"
        
        print("4. Opening target booking URL in a new page...")
        target_page = await context.new_page()
        await target_page.goto(book_href, wait_until="networkidle", timeout=20000)
        await target_page.wait_for_timeout(2500)
        
        t_title = await target_page.title()
        t_url = target_page.url
        t_body = await target_page.inner_text("body")
        
        print(f"Target Title: {t_title}")
        print(f"Target Final URL: {t_url}")
        
        has_dates = "26" in t_body and "30" in t_body
        has_route = ("תל אביב" in t_body or "TLV" in t_body) and ("וינה" in t_body or "VIE" in t_body)
        print(f"Target DOM has prompt dates: {has_dates}")
        print(f"Target DOM has prompt route: {has_route}")
        
        assert has_dates, "Target DOM does not show prompt dates!"
        assert has_route, "Target DOM does not show prompt route!"
        
        print("\n===> PHYSICAL BROWSER UI CLICK TEST PASSED 100% SUCCESSFULLY! <===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui_flight_card_click())
