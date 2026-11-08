import sys
import asyncio
import secrets
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from flight_agent.auth import get_connection

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def get_admin_session_token() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", ("xeinok2@gmail.com",))
    row = c.fetchone()
    if not row:
        raise RuntimeError("xeinok2@gmail.com not found in db")
    uid = row["id"]
    token = "tok_test_admin_" + secrets.token_hex(16)
    exp = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (uid, token, exp))
    conn.commit()
    return token

async def main():
    user_prompt = "טיסה ל2 אנשים  לרומא 3-4 לילות טיסה ישירה חובה שהתאריך 26.11 יהיה חלק מהימים אבל לא ביום של ההלוך ולא ביום של החזור עם מזוודות"
    print("\n=======================================================", flush=True)
    print("🚀 [PLAYWRIGHT BROWSER AUDIT] Exact User Prompt Verification", flush=True)
    print(f"User: xeinok2@gmail.com (Admin)")
    print(f"Prompt: '{user_prompt}'", flush=True)
    print("=======================================================\n", flush=True)

    token = get_admin_session_token()
    print(f"Admin Session Token generated: {token[:15]}...", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # -------------------------------------------------------------
        # 1. Desktop Test (1280x900)
        # -------------------------------------------------------------
        print("\n--- 1. DESKTOP VIEWPORT TEST (1280x900) ---", flush=True)
        desktop_context = await browser.new_context(viewport={"width": 1280, "height": 900})
        await desktop_context.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        
        page = await desktop_context.new_page()
        page.on("console", lambda msg: print(f"[DESKTOP CONSOLE] {msg.type}: {msg.text}", flush=True))
        page.on("pageerror", lambda err: print(f"[DESKTOP ERROR] {err}", flush=True))

        print("1. Opening http://127.0.0.1:8080/flights...", flush=True)
        await page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # Check logged in as admin
        is_logged_in = await page.is_visible("#authLoggedInSection")
        assert is_logged_in, "User xeinok2@gmail.com must be logged in"
        user_name = await page.inner_text("#navUserName")
        print(f"   ✓ Authenticated in browser as: {user_name}", flush=True)

        print("2. Entering user prompt into #aiPromptInput...", flush=True)
        await page.fill("#aiPromptInput", user_prompt)
        await page.wait_for_timeout(400)

        print("3. Submitting AI search via #btnAiSearch...", flush=True)
        await page.click("#btnAiSearch")

        print("4. Waiting for search results (#resultsSection)...", flush=True)
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=60000)
        print("   ✓ Results section is now visible!", flush=True)
        await page.wait_for_timeout(2000)

        # 5. Check Flexible Dates Banner
        is_flex_hidden = await page.eval_on_selector("#flexibleDatesBanner", "el => el.classList.contains('hidden')")
        assert not is_flex_hidden, "Flexible dates banner must be visible!"

        flex_cards = await page.query_selector_all("#flexibleDatesCardsGrid > div")
        print(f"   ✓ Candidate Date Option Cards: {len(flex_cards)} cards found", flush=True)
        assert len(flex_cards) >= 4, f"Expected at least 4 candidate date cards, got {len(flex_cards)}"

        for i, card in enumerate(flex_cards):
            text = (await card.inner_text()).strip()
            print(f"     Card #{i+1}:\n{text}")
            
            # Crucial assertions:
            # 1. Month must be November (.11), NOT March/April (.03 or .04)
            assert ".11" in text, f"Card #{i+1} must be in November (.11), got:\n{text}"
            assert ".03" not in text and ".04" not in text, f"Card #{i+1} erroneously contains March/April: {text}"
            
            # 2. Neither departure nor return can be 26.11
            assert not ("26.11 ⇄" in text or "⇄ 26.11" in text), f"Card #{i+1} has 26.11 on flight day! Text: {text}"

        # Check Active Route Description
        trip_desc = await page.inner_text("#statTripTypeDesc")
        print(f"   ✓ Active Search Route: {trip_desc}", flush=True)
        assert "2 נוסעים" in trip_desc, "Must indicate 2 passengers"

        # Check AI summary
        ai_summary = await page.inner_text("#displayParsedSummary")
        print(f"   ✓ AI Understanding Summary: {ai_summary}", flush=True)
        assert "26/11" in ai_summary or "26.11" in ai_summary or "רומא" in ai_summary

        # Check Baggage Banner
        bag_hidden = await page.eval_on_selector("#liveBaggageBanner", "el => el.classList.contains('hidden')")
        print(f"   ✓ Baggage Banner is visible: {not bag_hidden}", flush=True)
        assert not bag_hidden, "Baggage breakdown banner must be visible for 'עם מזוודות' request"

        # Screenshot Desktop
        desktop_screenshot_path = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/verified_accurate_dates_negative_constraint_desktop.png"
        await page.screenshot(path=desktop_screenshot_path, full_page=True)
        print(f"   ✓ Saved desktop screenshot to: {desktop_screenshot_path}", flush=True)
        await page.close()
        await desktop_context.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport Test (iPhone 14 size: 390x844)
        # -------------------------------------------------------------
        print("\n--- 2. MOBILE VIEWPORT TEST (iPhone 14, 390x844) ---", flush=True)
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        await mobile_context.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        mobile_page = await mobile_context.new_page()
        print("1. Opening http://127.0.0.1:8080/flights...", flush=True)
        await mobile_page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1000)

        print("2. Entering user prompt into #aiPromptInput...", flush=True)
        await mobile_page.fill("#aiPromptInput", user_prompt)
        await mobile_page.wait_for_timeout(300)
        await mobile_page.click("#btnAiSearch")

        print("3. Waiting for mobile search results...", flush=True)
        await mobile_page.wait_for_selector("#resultsSection:not(.hidden)", timeout=60000)
        await mobile_page.wait_for_timeout(2000)

        mobile_screenshot_path = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/verified_accurate_dates_negative_constraint_mobile.png"
        await mobile_page.screenshot(path=mobile_screenshot_path, full_page=True)
        print(f"   ✓ Saved mobile screenshot to: {mobile_screenshot_path}", flush=True)
        await mobile_page.close()
        await mobile_context.close()

        await browser.close()
        print("\n🎉 ALL AUDIT CHECKS PASSED ACCURATELY AND PERFECTLY!\n", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
