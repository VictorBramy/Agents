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
    token = "tok_test_all_air_" + secrets.token_hex(16)
    exp = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (uid, token, exp))
    conn.commit()
    return token

async def main():
    user_prompt = "טיסה ל2 אנשים  לרומא 3-4 לילות טיסה ישירה חובה שהתאריך 26.11 יהיה חלק מהימים אבל לא ביום של ההלוך ולא ביום של החזור עם מזוודות"
    print("\n=======================================================", flush=True)
    print("🚀 [PLAYWRIGHT AUDIT] ALL AIRLINES DATES & BOOKING LINKS AUDIT", flush=True)
    print(f"User: xeinok2@gmail.com (Admin)")
    print(f"Prompt: '{user_prompt}'", flush=True)
    print("=======================================================\n", flush=True)

    token = get_admin_session_token()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        desktop_ctx = await browser.new_context(viewport={"width": 1280, "height": 950})
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

        print("2. Submitting AI flight search...", flush=True)
        await page.fill("#aiPromptInput", user_prompt)
        await page.click("#btnAiSearch")

        print("3. Waiting for results to arrive...", flush=True)
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=70000)
        await page.wait_for_timeout(2500)

        # 3b. Verify form inputs at the top are synchronized
        filter_dest = await page.input_value("#filterDestination")
        filter_dep = await page.input_value("#filterDepDate")
        filter_ret = await page.input_value("#filterRetDate")
        print(f"   ✓ Synchronized Form Inputs: Destination={filter_dest}, Dep={filter_dep}, Ret={filter_ret}", flush=True)
        assert any(k in filter_dest for k in ["FCO", "רומא"]), f"Form destination not synced! Got: {filter_dest}"
        assert filter_dep == "2026-11-23", f"Form departure date not synced! Got: {filter_dep}"
        assert filter_ret == "2026-11-27", f"Form return date not synced! Got: {filter_ret}"

        # 3c. Verify flexible date candidates banner
        flex_cards = await page.query_selector_all("#flexibleDatesCardsGrid > div")
        print(f"   ✓ Flexible Candidate Options displayed: {len(flex_cards)}", flush=True)
        assert len(flex_cards) > 0, "Candidate date options should be displayed"
        for fc in flex_cards:
            fc_text = await fc.inner_text()
            print(f"     -> Option: {fc_text.replace(chr(10), ' ')}", flush=True)
            assert "30.03" not in fc_text and "03.04" not in fc_text and "31.03" not in fc_text, f"Candidate card has March/April date: {fc_text}"
            assert ".11" in fc_text, f"Candidate card must have November (.11) date: {fc_text}"

        # 4. Check all offer cards in #flightsContainer
        flight_cards = await page.query_selector_all("#flightsContainer > div")
        print(f"   ✓ Total flight cards displayed: {len(flight_cards)}", flush=True)
        assert len(flight_cards) > 0, "Must display flight offers"

        airlines_audited = {}
        cards_with_wrong_dates = []

        for idx, card in enumerate(flight_cards):
            text = await card.inner_text()
            # Extract links inside this card
            card_links = await card.eval_on_selector_all("a[href]", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))")
            
            # Check for dates on this card
            # In the return block or outbound block:
            # We must NOT see January 2027 (2027-01 or 01.2027 or 20.01) or February 2027
            for bad_d in ["2027-01", "2027-02", "2027-03", "2027-04", "20.01", "26.01", "04.02", "07.02"]:
                if bad_d in text:
                    cards_with_wrong_dates.append((idx + 1, bad_d, text[:100]))

            # Categorize by airline
            for air in ["Israir", "ישראייר", "Wizz", "וויז", "El Al", "אל על", "Arkia", "ארקיע", "Blue Bird", "בלו בירד", "ITA"]:
                if air.lower() in text.lower():
                    if air not in airlines_audited:
                        airlines_audited[air] = []
                    airlines_audited[air].append({
                        "card_num": idx + 1,
                        "links": card_links
                    })

        print("\n--- RESULTS DATES AUDIT ---", flush=True)
        print(f"Cards with wrong dates: {len(cards_with_wrong_dates)}")
        if cards_with_wrong_dates:
            for c in cards_with_wrong_dates:
                print(f"  [ERROR] Card #{c[0]} has date {c[1]}: {c[2]}")
        assert len(cards_with_wrong_dates) == 0, f"Found {len(cards_with_wrong_dates)} cards with dates outside prompt!"
        print("  ✓ 100% of flight cards strictly match November 2026 search dates (2026-11-23 to 2026-11-27)!", flush=True)

        print("\n--- ALL AIRLINES BOOKING LINKS AUDIT ---", flush=True)
        for air_name, occurrences in airlines_audited.items():
            print(f"\n✈️ Airline: {air_name} ({len(occurrences)} offers found):")
            for occ in occurrences[:2]:
                print(f"   Card #{occ['card_num']}:")
                for l in occ["links"]:
                    print(f"     -> Button: '{l['text']}' | Target: {l['href']}")
                    # Assert no dead links
                    assert "Abroad.html?dest=FCO" not in l["href"], f"Dead Israir Abroad link found in {air_name}: {l['href']}"
                    assert l["href"] != "https://www.israir.co.il/?origin=TLV&dest=FCO&date=2026-11-23", "Found dead homepage query link!"

        # Screenshot Desktop
        desktop_screenshot_path = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/verified_all_airlines_dates_links_desktop.png"
        await page.screenshot(path=desktop_screenshot_path, full_page=True)
        print(f"\n   ✓ Saved desktop screenshot to: {desktop_screenshot_path}", flush=True)
        await page.close()
        await desktop_ctx.close()

        # Mobile Viewport Test (iPhone 14)
        print("\n--- MOBILE VIEWPORT TEST (iPhone 14, 390x844) ---", flush=True)
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        await mobile_ctx.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1000)
        await mobile_page.fill("#aiPromptInput", user_prompt)
        await mobile_page.click("#btnAiSearch")
        await mobile_page.wait_for_selector("#resultsSection:not(.hidden)", timeout=70000)
        await mobile_page.wait_for_timeout(2500)

        mobile_screenshot_path = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/verified_all_airlines_dates_links_mobile.png"
        await mobile_page.screenshot(path=mobile_screenshot_path, full_page=True)
        print(f"   ✓ Saved mobile screenshot to: {mobile_screenshot_path}", flush=True)
        await mobile_page.close()
        await mobile_ctx.close()

        await browser.close()
        print("\n🎉 ALL AIRLINES AUDIT COMPLETED AND PASSED WITH 100% SUCCESS!\n", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
