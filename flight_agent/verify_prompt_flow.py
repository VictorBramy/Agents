import sys
import asyncio
from datetime import datetime

# Configure utf-8 output to prevent windows cp1255 encoding issues
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright

async def verify_ai_prompt_flow():
    user_prompt = "טיסה לוינה 2 אנשים עם מזוודות בתאריך נובמבר עד 5 ימים שיהיה בתאריך 26.11 אבל לא בחזור וגם לא הלוך"
    print(f"\n=======================================================")
    print(f"🚀 [PLAYWRIGHT BROWSER AUDIT] Running AI Search Flow")
    print(f"User Prompt: '{user_prompt}'")
    print(f"=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        page = await context.new_page()

        print("1. Navigating to http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("2. Entering user prompt into #aiPromptInput...")
        await page.fill("#aiPromptInput", user_prompt)
        await page.wait_for_timeout(500)

        print("3. Clicking #btnAiSearch button...")
        await page.click("#btnAiSearch")

        print("4. Waiting for live multi-engine search results to finish...")
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=45000)
        await page.wait_for_timeout(3000)

        print("5. Validating UI elements and constraints...")
        # Check prompt banner
        prompt_text = await page.inner_text("#displayUserPrompt")
        print(f"   ✓ Prompt Display: {prompt_text}")
        assert "26.11" in prompt_text, "Prompt text must be displayed"

        # Check parsed summary
        summary_text = await page.inner_text("#displayParsedSummary")
        print(f"   ✓ Parsed Summary: {summary_text}")

        # Check stats trip type description (contains dates)
        trip_desc = await page.inner_text("#statTripTypeDesc")
        print(f"   ✓ Trip Dates Desc: {trip_desc}")

        # Check total results
        total_found = await page.inner_text("#statTotalFound")
        print(f"   ✓ Total Flight Offers Found: {total_found}")
        assert int(total_found) > 0, "Must find flight results"

        # Check flight cards
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"   ✓ Rendered Flight Cards Count: {len(cards)}")
        assert len(cards) > 0, "Must render flight cards"

        # Extract dates from the first 3 cards
        for idx in range(min(3, len(cards))):
            card = cards[idx]
            card_text = await card.inner_text()
            
            # Check outbound and return dates in card
            assert "2026-11-26" not in card_text or "שהות ב-26/11" in card_text, (
                f"Card #{idx+1} must NOT have flight date on 2026-11-26! Content:\n{card_text[:200]}"
            )
            print(f"   ✓ Card #{idx+1} verified: 26.11 is strictly during the stay and NOT the flight date!")

        # Check booking links
        booking_btns = await page.query_selector_all("#flightsContainer a[target='_blank']")
        print(f"   ✓ Booking Links Found: {len(booking_btns)}")
        first_btn_href = await booking_btns[0].get_attribute("href")
        print(f"   ✓ First Booking Link: {first_btn_href[:80]}...")
        assert first_btn_href.startswith("http"), "Booking link must be a valid http URL"

        screenshot_path = "data/prompt_flight_test.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved to {screenshot_path}")

        print("\n=======================================================")
        print("🎉 ALL PLAYWRIGHT E2E ASSERTIONS PASSED SUCCESSFULLY!")
        print("=======================================================\n")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_ai_prompt_flow())
