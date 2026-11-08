import asyncio
import json
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=== Testing Thessaloniki Direct Swarm Search ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="he-IL"
        )
        page = await context.new_page()

        # 1. Login with admin user xeinok2@gmail.com
        print("1. Logging in with xeinok2@gmail.com...")
        login_resp = await page.request.post(
            "http://127.0.0.1:8080/api/auth/login",
            data=json.dumps({
                "email": "xeinok2@gmail.com",
                "password": "Password123!",
                "remember_me": True
            }),
            headers={"Content-Type": "application/json"}
        )
        print(f"Login status: {login_resp.status}")
        login_data = await login_resp.json()
        token = login_data.get("token")
        print(f"Acquired token: {token[:12]}...")

        # Set cookie on context
        await context.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        
        # Reload page to have active session
        await page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 2. Perform direct search via API directly to test the backend response
        print("2. Calling direct search API for TLV -> SKG (2027-10-08 -> 2027-10-22) direct_only=True, USD...")
        search_resp = await page.request.post(
            "http://127.0.0.1:8080/api/flights/search",
            data=json.dumps({
                "origin": "TLV",
                "destination": "SKG",
                "departure_date": "2027-10-08",
                "return_date": "2027-10-22",
                "trip_type": "round-trip",
                "direct_only": True,
                "currency": "USD",
                "passengers": 1,
                "fast_mode": False
            }),
            headers={"Content-Type": "application/json"},
            timeout=90000
        )
        
        print(f"Search API status: {search_resp.status}")
        data = await search_resp.json()

        lowest_price = data.get("lowest_price")
        print(f"\n>>> Lowest Price: ${lowest_price} (Target: Must NOT be $1170!)")
        assert lowest_price is not None and lowest_price < 300, f"Error: lowest price is {lowest_price}, expected < $300!"
        print(f"PASS: Lowest price is authentic ${lowest_price}!")

        # Check subagents count
        audits = data.get("subagent_reports") or []
        print(f"\n>>> Total Subagents in Swarm: {len(audits)}")
        for a in audits:
            print(f"  - [{a.get('logo_icon', '✈️')}] {a.get('hebrew_name')}: {a.get('status_badge')} | Offers: {a.get('offers_count')}")

        # Check combined offers
        offers = data.get("combined_offers") or []
        print(f"\n>>> Total Combined Offers Found: {len(offers)}")
        for i, o in enumerate(offers[:8]):
            print(f"  {i+1}. {o.get('primary_airline')} | ${o.get('price')} | Direct: {o.get('is_direct')} | Baggage: {o.get('baggage', {}).get('summary_he')}")
            assert o.get("is_direct") is True, f"Error: offer {i} is not direct!"
            assert o.get("price") < 500, f"Error: offer {i} price {o.get('price')} is too high!"

        # Verify Israir is present
        israir_found = any("ישראייר" in o.get("primary_airline", "") or "Israir" in o.get("primary_airline", "") for o in offers)
        print(f"\n>>> Israir Present: {israir_found}")
        assert israir_found, "Error: Israir direct flights not found in Thessaloniki search!"

        # Verify Arkia is present
        arkia_found = any("ארקיע" in o.get("primary_airline", "") or "Arkia" in o.get("primary_airline", "") for o in offers)
        print(f">>> Arkia Present: {arkia_found}")
        assert arkia_found, "Error: Arkia direct flights not found in Thessaloniki search!"

        # Verify Wizz Air is present at low cost
        wizz_found = any("וויז" in o.get("primary_airline", "") or "Wizz" in o.get("primary_airline", "") for o in offers)
        print(f">>> Wizz Air Present: {wizz_found}")
        assert wizz_found, "Error: Wizz Air direct flights not found in Thessaloniki search!"

        # Check AI Advice
        ai_adv = data.get("ai_advice", {})
        print(f"\n>>> AI Best Deal: {ai_adv.get('best_deal')}")
        print(f">>> AI Verdict: {ai_adv.get('price_verdict')}")
        print(f">>> AI Summary (preview):\n{ai_adv.get('summary_markdown', '')[:250]}...")

        # 3. Web UI Visual Verification: fill in search form and trigger search
        print("\n3. Testing via Web UI and capturing screenshots...")
        await page.click("#tabFilterBtn")
        await page.wait_for_timeout(400)
        
        # Fill inputs
        await page.fill("#filterDestination", "SKG")
        await page.fill("#filterDepDate", "2027-10-08")
        await page.fill("#filterRetDate", "2027-10-22")
        await page.select_option("#filterCurrency", "USD")
        
        # Ensure direct only is checked
        is_checked = await page.is_checked("#filterDirectOnly")
        if not is_checked:
            await page.check("#filterDirectOnly")

        print("Clicking search button in web UI...")
        # Click the search button inside the filter panel
        await page.click("#filterSearchPanel button:has-text('סרוק בכל המנועים')")
        
        # Wait for search results section to become visible
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=90000)
        await page.wait_for_timeout(3000)

        # Capture Desktop screenshot
        desktop_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/thessaloniki_direct_swarm_desktop.png"
        await page.screenshot(path=desktop_shot, full_page=True)
        print(f"Captured Desktop Screenshot: {desktop_shot}")

        # Capture Mobile screenshot
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1000)
        mobile_shot = "C:/Users/A/.gemini/antigravity/brain/f8d0af8f-e11b-4f48-a1e2-498095665c80/thessaloniki_direct_swarm_mobile.png"
        await page.screenshot(path=mobile_shot, full_page=True)
        print(f"Captured Mobile Screenshot: {mobile_shot}")

        await browser.close()
        print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(main())
