import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_ui_ai_prompt_search_and_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="he-IL")
        page = await context.new_page()
        
        print("1. Navigating to http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle", timeout=15000)
        
        prompt_text = "חפש לי טיסות לוינה מ-26 בנובמבר 2026 עד 30 בנובמבר 2026 הלוך ושוב ישיר"
        print(f"2. Typing prompt in #aiPromptInput: '{prompt_text}'...")
        await page.fill("#aiPromptInput", prompt_text)
        
        print("3. Clicking #btnAiSearch...")
        await page.click("#btnAiSearch")
        
        print("4. Waiting for results to load...")
        await page.wait_for_selector("#flightsContainer > div", timeout=45000)
        
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"Total rendered flight cards: {len(cards)}")
        assert len(cards) > 0, "No flight cards rendered!"
        
        # Check first card
        first_card = cards[0]
        airline_name = await (await first_card.query_selector(".font-black.text-base")).inner_text()
        print(f"First Card Airline: {airline_name}")
        
        booking_btn = await first_card.query_selector("a[title*='מעבר ישיר להזמנת הטיסה']")
        assert booking_btn is not None, "Booking button not found on first card!"
        
        book_href = await booking_btn.get_attribute("href")
        print(f"Booking Button Href: {book_href}")
        
        assert "2026-11-26" in book_href or "261126" in book_href, "Prompt departure date missing from booking URL!"
        assert "2026-11-30" in book_href or "261130" in book_href, "Prompt return date missing from booking URL!"
        
        print("5. Physically clicking/opening the booking link in new page...")
        target_page = await context.new_page()
        await target_page.goto(book_href, wait_until="networkidle", timeout=20000)
        await target_page.wait_for_timeout(3000)
        
        t_title = await target_page.title()
        t_url = target_page.url
        t_body = await target_page.inner_text("body")
        
        print(f"Target Title: {t_title}")
        print(f"Target URL: {t_url}")
        
        has_dates = "26" in t_body and "30" in t_body
        has_route = ("תל אביב" in t_body or "TLV" in t_body) and ("וינה" in t_body or "VIE" in t_body)
        print(f"DOM has prompt dates (26, 30): {has_dates}")
        print(f"DOM has prompt route (TLV, VIE): {has_route}")
        
        assert has_dates, "Target DOM missing prompt dates!"
        assert has_route, "Target DOM missing prompt route!"
        
        print("\n===> VERIFICATION PASSED: USER FLOW FROM PROMPT TO BOOKING LINK IS 100% OPERATIONAL! <===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui_ai_prompt_search_and_click())
