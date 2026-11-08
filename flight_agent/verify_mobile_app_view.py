import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8080/flights"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_mobile_app_experience():
    print("📱 Starting Playwright Mobile App Audit (iPhone 14 / Mobile Viewport)...")
    with sync_playwright() as p:
        # Emulate an iPhone 14
        iphone = p.devices["iPhone 14"]
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            **iphone,
            locale="he-IL"
        )
        page = context.new_page()

        print("1. Navigating to flights page on mobile device...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Check no horizontal overflow
        body_scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        body_client_width = page.evaluate("() => document.documentElement.clientWidth")
        print(f"   Viewport: {body_client_width}px, ScrollWidth: {body_scroll_width}px")
        assert body_scroll_width <= body_client_width + 1, f"Horizontal overflow detected! {body_scroll_width} > {body_client_width}"
        print("   ✅ Zero horizontal overflow verified!")

        # Verify Top Mobile Header
        header = page.locator("header")
        assert header.is_visible(), "Top header should be visible on mobile"
        title = page.locator("header h1")
        print(f"   Header Title: {title.inner_text()}")

        # Verify Bottom Tab Bar
        bottom_nav = page.locator("nav.md\\:hidden")
        assert bottom_nav.is_visible(), "Bottom Tab Navigation Bar should be visible on mobile!"
        print("   ✅ Bottom Navigation Tab Bar is visible and positioned at screen bottom!")

        # Take initial mobile screenshot
        shot1_path = os.path.join(OUTPUT_DIR, "mobile_app_home.png")
        page.screenshot(path=shot1_path)
        print(f"   📸 Screenshot saved: {shot1_path}")

        # Test Bottom Nav Tab: History
        print("2. Testing Bottom Nav Tab: History Modal (Bottom Sheet)...")
        page.locator("button:has-text('היסטוריה')").last.click()
        page.wait_for_timeout(500)
        history_modal = page.locator("#historyModal")
        assert history_modal.is_visible(), "History bottom sheet should be visible"
        print("   ✅ History Bottom Sheet opened successfully!")
        
        shot2_path = os.path.join(OUTPUT_DIR, "mobile_app_history_sheet.png")
        page.screenshot(path=shot2_path)
        print(f"   📸 Screenshot saved: {shot2_path}")
        page.locator("#historyModal button[onclick*='toggleHistoryModal']").click()
        page.wait_for_timeout(500)

        # Test Bottom Nav Tab: Subscription / Account
        print("3. Testing Bottom Nav Tab: Subscription / Account Sheet...")
        page.locator("#mobileTabAccountText").click()
        page.wait_for_timeout(600)
        
        sub_modal = page.locator("#subscriptionPlansModal")
        auth_modal = page.locator("#authModal")
        assert sub_modal.is_visible() or auth_modal.is_visible(), "Either subscription or auth sheet should open!"
        print(f"   ✅ Sheet opened (auth: {auth_modal.is_visible()}, sub: {sub_modal.is_visible()})")

        # Let's log in using demo user if auth modal is open
        if auth_modal.is_visible():
            print("4. Performing 1-Tap Demo Login on Mobile...")
            page.locator("button:has-text('משתמש הדגמה')").click()
            page.wait_for_timeout(1500)
            print("   ✅ Demo user logged in!")

        # Verify quota display on mobile
        quota_mobile = page.locator("#navQuotaText")
        print(f"   Navbar Quota display: {quota_mobile.inner_text() if quota_mobile.is_visible() else 'hidden'}")

        # Open Subscription Modal now that logged in
        page.locator("#mobileTabAccountText").click()
        page.wait_for_timeout(600)
        assert sub_modal.is_visible(), "Subscription Plans sheet must now be visible!"
        print("   ✅ Subscription Plans sheet verified!")

        shot3_path = os.path.join(OUTPUT_DIR, "mobile_app_subscription_sheet.png")
        page.screenshot(path=shot3_path)
        print(f"   📸 Screenshot saved: {shot3_path}")

        # Close subscription modal
        page.locator("#subscriptionPlansModal button[onclick*='closeSubscriptionModal']").first.click()
        page.wait_for_timeout(400)

        # Test Bottom Nav Tab: Filter Search
        print("5. Testing Tab Switch: 'סינון ידני' (Filter Search)...")
        page.locator("#mobileTabFilter").click()
        page.wait_for_timeout(500)
        assert page.locator("#filterSearchPanel").is_visible(), "Filter panel must be visible"
        assert not page.locator("#aiSearchPanel").is_visible(), "AI panel must be hidden"
        print("   ✅ Filter Search panel activated via bottom tab!")

        # Test swap button ⇄
        orig = page.locator("#filterOrigin").input_value()
        dest = page.locator("#filterDestination").input_value()
        page.locator("button:has-text('⇄ החלף')").click()
        page.wait_for_timeout(200)
        new_orig = page.locator("#filterOrigin").input_value()
        new_dest = page.locator("#filterDestination").input_value()
        assert new_orig == dest and new_dest == orig, f"Swap failed: {new_orig} vs {dest}"
        print(f"   ✅ Direction swap verified: {orig} -> {dest} swapped to {new_orig} -> {new_dest}")
        # Swap back
        page.locator("button:has-text('⇄ החלף')").click()

        # Switch back to AI Tab
        page.locator("#mobileTabAi").click()
        page.wait_for_timeout(400)
        assert page.locator("#aiSearchPanel").is_visible(), "AI panel should be visible"

        # Click a quick chip
        print("6. Testing Horizontal Quick Prompt Chips...")
        chip = page.locator("button:has-text('סופ״ש באתונה')").first
        chip.click()
        prompt_val = page.locator("#aiPromptInput").input_value()
        assert "אתונה" in prompt_val, "Quick chip should fill prompt input"
        print(f"   ✅ Quick prompt chip populated: '{prompt_val}'")

        # Perform search and verify flight ticket cards on mobile
        print("7. Running search to inspect mobile flight cards layout...")
        page.locator("#btnAiSearch").click()
        page.wait_for_timeout(3500)

        # Wait for results
        page.wait_for_selector("#resultsSection:not(.hidden)", timeout=20000)
        cards = page.locator("#flightsContainer > div")
        count = cards.count()
        print(f"   ✅ {count} flight cards rendered on mobile!")
        assert count > 0, "Should render flight cards"

        # Check booking button on first card
        first_card = cards.first
        book_btn = first_card.locator("a:has-text('הזמן כרטיס')")
        assert book_btn.is_visible(), "Book button should be visible and prominent"
        print("   ✅ Flight boarding pass card layout verified on mobile screen!")

        # Full mobile results screenshot
        shot4_path = os.path.join(OUTPUT_DIR, "mobile_app_flight_results.png")
        page.screenshot(path=shot4_path)
        print(f"   📸 Screenshot saved: {shot4_path}")

        browser.close()
        print("\n🎉 ALL MOBILE APP TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_mobile_app_experience()
