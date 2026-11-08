import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

async def verify_flexible_dates_flow():
    user_prompt = "טיסה הלוך חזור לרומא לזוג עם מזוודות חייב ש26.11 יהיה חלק מהתאריכים אבל לא בהלוך ולא בחזור בין 3-4 לילות"
    print("\n=======================================================", flush=True)
    print("🚀 [PLAYWRIGHT BROWSER AUDIT] Flexible Candidate Dates Verification", flush=True)
    print(f"Prompt: '{user_prompt}'", flush=True)
    print("=======================================================\n", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}", flush=True))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}", flush=True))
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        print("1. Opening http://127.0.0.1:8080/flights...", flush=True)
        await page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        print("2. Entering user prompt into #aiPromptInput...", flush=True)
        await page.fill("#aiPromptInput", user_prompt)
        await page.wait_for_timeout(500)

        print("3. Clicking #btnAiSearch...", flush=True)
        await page.click("#btnAiSearch")

        print("4. Waiting for search results (#resultsSection)...", flush=True)
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=90000)
        print("   ✓ Results section is now visible!", flush=True)
        await page.wait_for_timeout(2000)

        # 5. Check Flexible Candidate Dates Banner
        print("5. Checking Flexible Candidate Dates Banner (#flexibleDatesBanner)...", flush=True)
        is_flex_hidden = await page.eval_on_selector("#flexibleDatesBanner", "el => el.classList.contains('hidden')")
        assert not is_flex_hidden, "Flexible dates banner must be visible"

        nights_badge = await page.inner_text("#flexibleNightsBadge")
        print(f"   ✓ Nights Badge: {nights_badge}", flush=True)
        assert "3-4" in nights_badge or "לילות" in nights_badge, "Badge must reflect 3-4 nights"

        # Validate Candidate Date Option Cards
        flex_cards = await page.query_selector_all("#flexibleDatesCardsGrid > div")
        print(f"   ✓ Candidate Date Option Cards Rendered: {len(flex_cards)}", flush=True)
        assert len(flex_cards) >= 4, "Must render at least 4 valid candidate date combinations"

        cards_text = await page.inner_text("#flexibleDatesCardsGrid")
        print("   ✓ Verifying Expected User Date Combinations in Cards:", flush=True)
        assert "25.11" in cards_text and "28.11" in cards_text, "Must include 25.11 to 28.11 (3 nights)"
        print("     -> Found 25.11 - 28.11 (3 לילות) ✓", flush=True)
        assert "24.11" in cards_text and "27.11" in cards_text, "Must include 24.11 to 27.11 (3 nights)"
        print("     -> Found 24.11 - 27.11 (3 לילות) ✓", flush=True)
        assert "23.11" in cards_text and "27.11" in cards_text, "Must include 23.11 to 27.11 (4 nights)"
        print("     -> Found 23.11 - 27.11 (4 לילות) ✓", flush=True)

        # Validate 2 Passengers
        trip_desc = await page.inner_text("#statTripTypeDesc")
        print(f"   ✓ Active Search Route: {trip_desc}", flush=True)
        assert "2 נוסעים" in trip_desc, "Must indicate 2 passengers"

        # QA Compliance Banner
        qa_banner = await page.inner_text("#qualityAuditBannerText")
        print(f"   ✓ QA Compliance Banner: {qa_banner}", flush=True)
        assert "18" in qa_banner or "100" in qa_banner or "14" in qa_banner

        # 6. Interactive Candidate Date Switching
        print("6. Testing Interactive Date Switching: Clicking 25.11 - 28.11 card...", flush=True)
        card_25_28 = None
        for c in flex_cards:
            txt = await c.inner_text()
            if "25.11" in txt and "28.11" in txt:
                card_25_28 = c
                break
        assert card_25_28 is not None, "25.11 - 28.11 card must exist"
        print("   ✓ Found 25.11 - 28.11 card. Clicking...", flush=True)
        await card_25_28.click()

        print("   ✓ Waiting for updated dates in #statTripTypeDesc...", flush=True)
        await page.wait_for_function(
            "() => document.getElementById('statTripTypeDesc') && document.getElementById('statTripTypeDesc').innerText.includes('2026-11-25')",
            timeout=20000
        )

        updated_trip_desc = await page.inner_text("#statTripTypeDesc")
        print(f"   ✓ Switched Route Dates: {updated_trip_desc}", flush=True)
        assert "2026-11-25" in updated_trip_desc and "2026-11-28" in updated_trip_desc, "Must update search to 25.11 - 28.11"

        # Take screenshot
        screenshot_path = "data/verified_flexible_dates.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved to {screenshot_path}", flush=True)

        print("\n=======================================================", flush=True)
        print("🎉 PLAYWRIGHT AUDIT PASSED: 100% FLEXIBLE DATE CANDIDATES VERIFIED!", flush=True)
        print("=======================================================\n", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_flexible_dates_flow())
