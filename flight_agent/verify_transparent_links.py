import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\A\.gemini\antigravity\brain\f8d0af8f-e11b-4f48-a1e2-498095665c80"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Test
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        
        # Login with xeinok2@gmail.com
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
        
        await context.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        
        print("Navigating to http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", timeout=20000, wait_until="networkidle")
        
        # Switch to filter search tab
        await page.click("#tabFilterBtn")
        await page.wait_for_timeout(500)
        
        # Fill in search: TLV -> SKG
        await page.fill("#filterDestination", "SKG")
        await page.fill("#filterDepDate", "2027-10-08")
        await page.fill("#filterRetDate", "2027-10-22")
        
        # Trigger search
        print("Triggering search for TLV -> SKG (08/10/2027 - 22/10/2027)...")
        await page.click("button:has-text('סרוק בכל המנועים')")
        
        # Wait for results
        await page.wait_for_selector("#resultsSection", state="visible", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Inspect rendered cards
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"Total cards rendered: {len(cards)}")
        
        verified_sf = False
        verified_direct = False
        
        for i, card in enumerate(cards[:10]):
            text = await card.inner_text()
            links = await card.query_selector_all("a")
            link_details = []
            for a in links:
                href = await a.get_attribute("href")
                t = (await a.inner_text()).strip()
                link_details.append((t, href))
            
            print(f"\n--- Card #{i+1} ---")
            print("Buttons found:")
            for t, href in link_details:
                print(f"  [{t}] -> {href[:80]}...")
            
            # Check Secret Flights attribution
            if "אותר בטיסות סודיות" in text:
                verified_sf = True
                print("  => CONFIRMED: Secret Flights badge present.")
                has_sf_deal_btn = any("צפה בדיל בטיסות סודיות" in t for t, h in link_details)
                print(f"  => 'צפה בדיל בטיסות סודיות' button present: {has_sf_deal_btn}")
                for t, href in link_details:
                    if "ישראייר" in t and "secretflights" in (href or ""):
                        print("  [ERROR] Found Israir button pointing to Secret Flights!")
                    elif "ישראייר" in t:
                        print(f"  => Verified authentic airline button: [{t}] -> {href}")

            if "אתר רשמי ישיר" in text:
                verified_direct = True
                print("  => CONFIRMED: Direct airline official site badge present.")

        # Scroll to offers list for clear view
        await page.evaluate("document.getElementById('flightsContainer').scrollIntoView()")
        await page.wait_for_timeout(1000)

        # Capture desktop screenshot
        desktop_shot = os.path.join(ARTIFACT_DIR, "verified_accurate_booking_links_desktop.png")
        await page.screenshot(path=desktop_shot, full_page=False)
        print(f"Desktop screenshot saved: {desktop_shot}")
        
        # 2. Mobile View Test
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True
        )
        await mobile_context.add_cookies([{
            "name": "flight_session_token",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://127.0.0.1:8080/flights", timeout=20000, wait_until="networkidle")
        await mobile_page.click("#tabFilterBtn")
        await mobile_page.fill("#filterDestination", "SKG")
        await mobile_page.fill("#filterDepDate", "2027-10-08")
        await mobile_page.fill("#filterRetDate", "2027-10-22")
        await mobile_page.click("button:has-text('סרוק בכל המנועים')")
        
        await mobile_page.wait_for_selector("#resultsSection", state="visible", timeout=30000)
        await mobile_page.wait_for_timeout(2000)
        
        await mobile_page.evaluate("document.getElementById('flightsContainer').scrollIntoView()")
        await mobile_page.wait_for_timeout(1000)
        
        mobile_shot = os.path.join(ARTIFACT_DIR, "verified_accurate_booking_links_mobile.png")
        await mobile_page.screenshot(path=mobile_shot, full_page=False)
        print(f"Mobile screenshot saved: {mobile_shot}")
        
        print("\n=== SUMMARY ===")
        print(f"Verified Secret Flights transparency: {verified_sf}")
        print(f"Verified Direct Airline transparency: {verified_direct}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
