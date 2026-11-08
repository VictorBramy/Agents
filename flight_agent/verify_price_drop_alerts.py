import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8080"
ADMIN_EMAIL = "xeinok2@gmail.com"
ADMIN_PASS = "Password123!"
ARTIFACT_DIR = r"C:\Users\A\.gemini\antigravity\brain\f8d0af8f-e11b-4f48-a1e2-498095665c80"

def test_price_drop_alerts_system():
    print("[1] Launching Playwright to test Price Drop Alerts System...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # Step 1: Login as Admin
        print("[2] Logging in as admin user...")
        page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        login_res = page.request.post(
            f"{BASE_URL}/api/auth/login",
            data=json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASS, "remember_month": True}),
            headers={"Content-Type": "application/json"}
        )
        assert login_res.status == 200, f"Login failed: {login_res.text()}"
        login_data = login_res.json()
        print(f"    Admin Login OK: {login_data.get('user', {}).get('email')}")

        # Step 2: Track a new route via API
        print("[3] Adding a tracked flight with target price...")
        track_res = page.request.post(
            f"{BASE_URL}/api/flights/track",
            data=json.dumps({
                "origin": "TLV",
                "destination": "ATH",
                "departure_date": "2026-11-20",
                "return_date": "2026-11-27",
                "trip_type": "round-trip",
                "currency": "USD",
                "lowest_price_seen": 160.0,
                "best_airline": "Bluebird Airways",
                "booking_link": "https://www.bluebirdair.com",
                "target_price": 130.0,
                "user_phone": "0524845131",
                "direct_only": True,
                "passengers": 1
            }),
            headers={"Content-Type": "application/json"}
        )
        assert track_res.status == 200, f"Track route failed: {track_res.text()}"
        track_data = track_res.json()
        track_id = track_data["track_id"]
        print(f"    Tracked route created with ID: {track_id}")

        # Step 3: Directly simulate a verified price drop in DB to test drop alerts
        print("[4] Simulating verified price drop ($160 -> $115) to trigger alert status...")
        from flight_agent.db import record_price_check
        check_res = record_price_check(
            track_id=track_id,
            new_price=115.0,
            new_airline="Israir",
            booking_link="https://www.israir.co.il"
        )
        print(f"    Price check recorded: is_alert={check_res.get('is_alert')}, drop={check_res.get('price_drop_amount')}$, percent={check_res.get('price_drop_percent')}%")
        assert check_res.get("price_drop_amount") == 45.0, "Expected drop amount of 45.0"

        # Step 4: Verify summary endpoint
        print("[5] Verifying /api/flights/price-alerts/summary...")
        sum_res = page.request.get(f"{BASE_URL}/api/flights/price-alerts/summary")
        assert sum_res.status == 200
        summary = sum_res.json()
        print(f"    Summary: {summary}")
        assert summary.get("total_price_drops", 0) >= 1
        assert summary.get("total_savings", 0) >= 45.0

        # Step 5: Test Desktop UI for Tracked Flights Modal
        print("[6] Loading /flights on desktop to verify Tracked Flights Modal...")
        page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        time.sleep(1)

        # Open tracked modal
        page.click("button:has-text('מעקב')")
        time.sleep(1)
        page.wait_for_selector("#trackedModal:not(.hidden)")

        # Verify items rendered
        tracked_text = page.inner_text("#trackedModal")
        assert "TLV ⇄ ATH" in tracked_text or "ATH" in tracked_text
        assert "115" in tracked_text or "45" in tracked_text
        print("    Tracked modal correctly rendered price drop and route!")

        desktop_alert_shot = os.path.join(ARTIFACT_DIR, "verified_price_drop_alerts_desktop.png")
        page.screenshot(path=desktop_alert_shot)
        print(f"    Desktop screenshot saved: {desktop_alert_shot}")

        # Step 6: Test Desktop Admin Dashboard - Price Alerts Tab
        print("[7] Loading /admin on desktop to verify Price Alerts Monitor Tab...")
        page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        time.sleep(1)

        # Click tab 'מעקב מחירים'
        page.click("#tabBtn-alerts")
        time.sleep(1)

        admin_alerts_text = page.inner_text("#section-alerts")
        assert "מערכת מעקב מחירי טיסות והתראות" in admin_alerts_text
        assert "ATH" in admin_alerts_text
        assert "115" in admin_alerts_text or "45" in admin_alerts_text
        print("    Admin Price Drop Monitor rendered successfully!")

        admin_shot = os.path.join(ARTIFACT_DIR, "verified_admin_price_drop_monitor_desktop.png")
        page.screenshot(path=admin_shot)
        print(f"    Admin desktop screenshot saved: {admin_shot}")

        # Step 7: Test Mobile App Viewport (393x852)
        print("[8] Testing Mobile App Viewport (iPhone 14 Pro)...")
        mobile_context = browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True
        )
        mobile_page = mobile_context.new_page()

        # Login on mobile
        mobile_page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        mobile_page.request.post(
            f"{BASE_URL}/api/auth/login",
            data=json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASS, "remember_month": True}),
            headers={"Content-Type": "application/json"}
        )
        mobile_page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        time.sleep(1)

        # Click mobile bottom nav Tab 3 ("מעקב מחיר")
        print("    Opening mobile bottom sheet 'מעקב מחיר'...")
        mobile_page.evaluate("toggleTrackedModal()")
        time.sleep(1)

        mobile_alert_shot = os.path.join(ARTIFACT_DIR, "verified_price_drop_alerts_mobile.png")
        mobile_page.screenshot(path=mobile_alert_shot)
        print(f"    Mobile alert sheet screenshot saved: {mobile_alert_shot}")

        # Check admin on mobile
        print("    Checking Admin Price Drop Monitor on mobile...")
        mobile_page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        time.sleep(1)
        mobile_page.click("#tabBtn-alerts")
        time.sleep(1)

        mobile_admin_shot = os.path.join(ARTIFACT_DIR, "verified_admin_price_drop_monitor_mobile.png")
        mobile_page.screenshot(path=mobile_admin_shot)
        print(f"    Mobile admin screenshot saved: {mobile_admin_shot}")

        browser.close()

    print("\n[SUCCESS] ALL PRICE DROP ALERT SYSTEM VERIFICATIONS PASSED!")

if __name__ == "__main__":
    test_price_drop_alerts_system()
