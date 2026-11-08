import sys
import os
import asyncio
import secrets
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from flight_agent.auth import get_connection

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\A\.gemini\antigravity\brain\f8d0af8f-e11b-4f48-a1e2-498095665c80"
PROMPT = "טיסה ל2 אנשים  לפראג 3-4 לילות טיסה ישירה חובה שהתאריך 26.11 יהיה חלק מהימים אבל לא ביום של ההלוך ולא ביום של החזור עם מזוודות"

def get_admin_session_token() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", ("xeinok2@gmail.com",))
    row = c.fetchone()
    if not row:
        raise RuntimeError("xeinok2@gmail.com not found in db")
    uid = row["id"]
    token = "tok_test_prague_" + secrets.token_hex(16)
    exp = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (uid, token, exp))
    conn.commit()
    return token

async def main():
    print("=======================================================", flush=True)
    print("🚀 [PRAGUE PLAYWRIGHT AUDIT] Testing Exact User Prompt", flush=True)
    print(f"Prompt: '{PROMPT}'", flush=True)
    print("=======================================================\n", flush=True)

    token = get_admin_session_token()
    print(f"Admin Session Token generated: {token[:15]}...", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Test (1300x950)
        # -------------------------------------------------------------
        print("\n--- 1. DESKTOP VIEWPORT TEST (1300x950) ---", flush=True)
        desktop_ctx = await browser.new_context(viewport={"width": 1300, "height": 950})
        await desktop_ctx.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = await desktop_ctx.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}", flush=True))

        print("1. Opening http://127.0.0.1:8080/flights...", flush=True)
        await page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await page.wait_for_timeout(1200)

        print("2. Submitting AI flight search via #btnAiSearch...", flush=True)
        await page.fill("#aiPromptInput", PROMPT)
        await page.click("#btnAiSearch")

        print("3. Waiting for results to arrive...", flush=True)
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=70000)
        await page.wait_for_timeout(2500)

        # Form check
        filter_dest = await page.input_value("#filterDestination")
        filter_dep = await page.input_value("#filterDepDate")
        filter_ret = await page.input_value("#filterRetDate")
        print(f"   ✓ Form values: Dest={filter_dest}, Dep={filter_dep}, Ret={filter_ret}", flush=True)
        assert any(k in filter_dest for k in ["PRG", "פראג"]), f"Destination not Prague: {filter_dest}"
        assert ".11" in filter_dep or "2026-11" in filter_dep, f"Departure must be in Nov 2026: {filter_dep}"

        # Flexible dates check
        flex_cards = await page.query_selector_all("#flexibleDatesCardsGrid > div")
        print(f"   ✓ Flexible options count: {len(flex_cards)}", flush=True)
        for fc in flex_cards[:5]:
            fc_text = (await fc.inner_text()).replace("\n", " ")
            print(f"     -> Option: {fc_text}", flush=True)
            assert ".11" in fc_text, f"Candidate option must be in Nov: {fc_text}"
            assert not ("26.11 ⇄" in fc_text or "⇄ 26.11" in fc_text), f"26.11 on travel day: {fc_text}"

        # Offer cards check
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"\n   ✓ Total Offer Cards displayed: {len(cards)}", flush=True)

        wizz_phantom_count = 0
        direct_airline_buttons = []

        for i, card in enumerate(cards):
            card_text = (await card.inner_text()).strip()
            # Check for non-existent Wizz flights
            if "wizz" in card_text.lower() or "וויז" in card_text:
                wizz_phantom_count += 1
                print(f"⚠️ Warning: Found Wizz flight in card #{i+1}: {card_text[:100]}")

            # Check primary CTA button
            links = await card.query_selector_all("a[target='_blank']")
            for lnk in links:
                h = await lnk.get_attribute("href") or ""
                t = (await lnk.inner_text()).strip()
                if any(x in t for x in ["הזמן כרטיס באתר", "צפה והזמן"]):
                    direct_airline_buttons.append({"card_idx": i + 1, "text": t, "href": h})

        print(f"\n--- AUDIT OF PRIMARY AIRLINE CTA BUTTONS ---", flush=True)
        for btn in direct_airline_buttons[:8]:
            print(f"Card #{btn['card_idx']}: '{btn['text']}' -> {btn['href'][:80]}...", flush=True)
            # Crucial: Primary airline button must NOT be Google Flights!
            assert "google.com/travel" not in btn['href'], f"Error: Airline button points to Google Flights! {btn}"

        print(f"\nWizz Air phantom flights count: {wizz_phantom_count} (Expected: 0)", flush=True)
        assert wizz_phantom_count == 0, f"Error: Found {wizz_phantom_count} Wizz flights for Prague direct!"

        desktop_screenshot_path = os.path.join(ARTIFACT_DIR, "verified_prague_results_desktop.png")
        await page.screenshot(path=desktop_screenshot_path, full_page=True)
        print(f"✓ Saved desktop screenshot to: {desktop_screenshot_path}", flush=True)

        # -------------------------------------------------------------
        # 2. Mobile Viewport Test (390x844)
        # -------------------------------------------------------------
        print("\n--- 2. MOBILE VIEWPORT TEST (390x844) ---", flush=True)
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        await mobile_ctx.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        m_page = await mobile_ctx.new_page()
        await m_page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await m_page.wait_for_timeout(1000)

        await m_page.fill("#aiPromptInput", PROMPT)
        await m_page.click("#btnAiSearch")
        await m_page.wait_for_selector("#resultsSection:not(.hidden)", timeout=70000)
        await m_page.wait_for_timeout(2500)

        mobile_screenshot_path = os.path.join(ARTIFACT_DIR, "verified_prague_results_mobile.png")
        await m_page.screenshot(path=mobile_screenshot_path, full_page=True)
        print(f"✓ Saved mobile screenshot to: {mobile_screenshot_path}", flush=True)

        await browser.close()
        print("\n=======================================================", flush=True)
        print("🎉 [SUCCESS] All Prague E2E Verifications Passed 100%!", flush=True)
        print("=======================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
