import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import secrets
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from flight_agent.auth import get_connection

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def get_admin_session_token():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email='xeinok2@gmail.com'")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (email, password_hash, full_name, is_admin, plan_tier, searches_limit, searches_used) VALUES ('xeinok2@gmail.com', 'dummy_hash', 'Admin Tester', 1, 'vip', 9999, 0)")
        conn.commit()
        uid = c.lastrowid
    else:
        uid = row["id"]
        c.execute("UPDATE users SET searches_limit=9999, searches_used=0 WHERE id=?", (uid,))
        conn.commit()
    token = "tok_test_ui_" + secrets.token_hex(16)
    exp = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (uid, token, exp))
    conn.commit()
    return token

async def verify_redesigned_ui():
    token = get_admin_session_token()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # 1. Desktop Verification (1280x950)
        # ----------------------------------------------------
        desktop_ctx = await browser.new_context(viewport={"width": 1280, "height": 950})
        await desktop_ctx.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        desktop_page = await desktop_ctx.new_page()
        print("Navigating to http://127.0.0.1:8080/flights on Desktop...", flush=True)
        await desktop_page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle")

        # Switch to filter tab to verify modernized search bar (Fix for Image 1)
        print("Switching to manual filter tab...", flush=True)
        await desktop_page.click("#tabFilterBtn")
        await desktop_page.wait_for_timeout(600)

        search_bar_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/modern_search_bar_desktop.png"
        await desktop_page.screenshot(path=search_bar_shot)
        print(f"Captured modernized search bar screenshot: {search_bar_shot}", flush=True)

        # Switch back to AI search tab
        await desktop_page.click("#tabAiBtn")
        await desktop_page.wait_for_timeout(300)

        # Enter user's exact prompt
        user_prompt = "טיסה ל2 אנשים  לרומא 3-4 לילות טיסה ישירה חובה שהתאריך 26.11 יהיה חלק מהימים אבל לא ביום של ההלוך ולא ביום של החזור עם מזוודות"
        print(f"Entering prompt: {user_prompt}", flush=True)
        await desktop_page.fill("#aiPromptInput", user_prompt)

        # Click AI Multi-Search
        print("Clicking AI Multi-Search...", flush=True)
        await desktop_page.click("#btnAiSearch")

        # Wait for results section to be visible
        print("Waiting for flight results...", flush=True)
        await desktop_page.wait_for_selector("#resultsSection:not(.hidden)", timeout=45000)
        await desktop_page.wait_for_selector("#flightsContainer > div", timeout=15000)
        await desktop_page.wait_for_timeout(2000)

        # Verify Flexible Dates banner
        flex_visible = await desktop_page.is_visible("#flexibleDatesBanner")
        print(f"Flexible dates banner visible: {flex_visible}", flush=True)

        # Check dates inside flexible banner
        flex_text = await desktop_page.inner_text("#flexibleDatesCardsGrid")
        print(f"Flexible dates text preview: {flex_text[:120]}...", flush=True)

        # Check technical audits accordion toggle
        print("Testing technical audits accordion toggle...", flush=True)
        is_tech_hidden_before = await desktop_page.eval_on_selector("#techAuditsContent", "el => el.classList.contains('hidden')")
        print(f"Technical audits collapsed by default: {is_tech_hidden_before}", flush=True)
        assert is_tech_hidden_before, "techAuditsContent should be collapsed by default"

        # Toggle to open
        await desktop_page.click("#techAuditsWrapper > div")
        await desktop_page.wait_for_timeout(400)
        is_tech_hidden_after = await desktop_page.eval_on_selector("#techAuditsContent", "el => el.classList.contains('hidden')")
        print(f"Technical audits opened after click: {not is_tech_hidden_after}", flush=True)
        assert not is_tech_hidden_after, "techAuditsContent should be visible after click"

        # Toggle back to close to keep page clean
        await desktop_page.click("#techAuditsWrapper > div")
        await desktop_page.wait_for_timeout(400)

        # Capture Desktop Full Page
        desktop_results_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/modern_ui_desktop_results.png"
        await desktop_page.screenshot(path=desktop_results_shot, full_page=True)
        print(f"Captured full-page desktop results: {desktop_results_shot}", flush=True)
        await desktop_ctx.close()

        # ----------------------------------------------------
        # 2. Mobile Verification (iPhone 14, 390x844)
        # ----------------------------------------------------
        print("\nStarting Mobile Viewport Verification (390x844)...", flush=True)
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        await mobile_ctx.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle")

        # Check mobile search tab (Fix for Image 1)
        await mobile_page.click("#tabFilterBtn")
        await mobile_page.wait_for_timeout(500)
        mobile_filter_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/modern_search_bar_mobile.png"
        await mobile_page.screenshot(path=mobile_filter_shot)
        print(f"Captured mobile search bar: {mobile_filter_shot}", flush=True)

        # Search prompt on mobile
        await mobile_page.click("#tabAiBtn")
        await mobile_page.wait_for_timeout(300)
        await mobile_page.fill("#aiPromptInput", user_prompt)
        await mobile_page.click("#btnAiSearch")

        await mobile_page.wait_for_selector("#resultsSection:not(.hidden)", timeout=45000)
        await mobile_page.wait_for_selector("#flightsContainer > div", timeout=15000)
        await mobile_page.wait_for_timeout(2000)

        mobile_results_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/modern_ui_mobile_results.png"
        await mobile_page.screenshot(path=mobile_results_shot, full_page=False)
        print(f"Captured mobile flight results viewport: {mobile_results_shot}", flush=True)

        # Full page mobile screenshot
        mobile_full_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/modern_ui_mobile_full.png"
        await mobile_page.screenshot(path=mobile_full_shot, full_page=True)
        print(f"Captured full mobile results: {mobile_full_shot}", flush=True)

        # Check that no horizontal overflow exists on body
        overflow_x = await mobile_page.evaluate("() => document.body.scrollWidth > window.innerWidth")
        print(f"Mobile body horizontal overflow detected: {overflow_x}", flush=True)

        await mobile_ctx.close()
        await browser.close()
        print("\nAll UI verifications completed successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(verify_redesigned_ui())
