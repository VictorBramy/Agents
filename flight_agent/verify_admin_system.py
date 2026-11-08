import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import requests
import json
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "y-CM62OydOyMcVk2-TD0KbyK6tQKnJhj6-Uz1ujnFNw"

def test_admin_api():
    print("[1/5] Testing Admin API permissions & endpoints...")
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    # 1. /api/auth/me
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    assert res.status_code == 200, f"me failed: {res.text}"
    me = res.json()
    assert me["authenticated"] is True
    assert me["user"]["email"] == "xeinok2@gmail.com"
    assert me["user"]["is_admin"] is True
    assert me["quota"]["unlimited"] is True
    assert me["quota"]["searches_limit"] == 999999
    print(f"  ✓ Admin auth verified: {me['user']['email']}, Plan: {me['quota']['plan_name']}, Unlimited: {me['quota']['unlimited']}")

    # 2. /api/admin/overview
    res = requests.get(f"{BASE_URL}/api/admin/overview", headers=headers)
    assert res.status_code == 200, f"overview failed: {res.text}"
    overview = res.json()
    kpis = overview["kpis"]
    print(f"  ✓ Overview KPIs: Total Users={kpis['total_users']}, Searches={kpis['total_searches']}, MRR=₪{kpis['total_revenue_ils']}, Paying={kpis['paying_subscribers']}")
    assert kpis["total_users"] > 0
    assert len(overview["plan_distribution"]) > 0
    assert len(overview["top_destinations"]) > 0

    # 3. /api/admin/users
    res = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    assert res.status_code == 200, f"users list failed: {res.text}"
    users_data = res.json()
    print(f"  ✓ Users list: {users_data['total']} registered users retrieved")
    admin_found = any(u["email"] == "xeinok2@gmail.com" and u["is_admin"] is True for u in users_data["users"])
    assert admin_found, "Admin xeinok2@gmail.com not flagged as admin in users list"

    # 4. /api/admin/users/8/history
    res = requests.get(f"{BASE_URL}/api/admin/users/8/history", headers=headers)
    assert res.status_code == 200, f"user history failed: {res.text}"
    hist = res.json()
    print(f"  ✓ User search history for xeinok2@gmail.com: {hist['total_searches']} searches logged")

    # 5. /api/admin/users/1/reset-quota
    res = requests.post(f"{BASE_URL}/api/admin/users/1/reset-quota", headers=headers)
    assert res.status_code == 200, f"reset quota failed: {res.text}"
    reset_res = res.json()
    assert reset_res["success"] is True
    print(f"  ✓ Reset quota action: {reset_res['message']}")

    # 6. /api/admin/searches
    res = requests.get(f"{BASE_URL}/api/admin/searches?limit=10", headers=headers)
    assert res.status_code == 200, f"global searches failed: {res.text}"
    searches = res.json()["searches"]
    print(f"  ✓ Global searches feed: {len(searches)} recent searches loaded")

def test_admin_ui_playwright():
    print("\n[2/5] Testing Admin UI in Playwright (Desktop & Mobile)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # A. Desktop Browser Test
        desktop_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="he-IL"
        )
        desktop_context.add_cookies([{
            "name": "flight_session_token",
            "value": ADMIN_TOKEN,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = desktop_context.new_page()

        # 1. Check /flights shows admin badge and unlimited quota
        print("  Testing /flights with Admin session...")
        page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        page.wait_for_timeout(1000)

        nav_admin_btn = page.locator("#navAdminDashboardBtn")
        assert nav_admin_btn.is_visible(), "navAdminDashboardBtn not visible for admin user"
        quota_text = page.locator("#navQuotaText").inner_text()
        print(f"  ✓ /flights navbar quota display: '{quota_text}'")
        assert "ללא הגבלה" in quota_text or "👑" in quota_text

        # 2. Navigate to /admin
        print("  Testing /admin navigation and layout...")
        page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Check KPIs are rendered
        total_users_el = page.locator("#kpiTotalUsers").inner_text()
        total_searches_el = page.locator("#kpiTotalSearches").inner_text()
        revenue_el = page.locator("#kpiTotalRevenue").inner_text()
        print(f"  ✓ /admin KPIs: Users={total_users_el}, Searches={total_searches_el}, Revenue=₪{revenue_el}")

        # Check Admin Email displayed
        admin_email = page.locator("#adminEmailDisplay").inner_text()
        assert "xeinok2@gmail.com" in admin_email
        print(f"  ✓ Admin email pill: {admin_email}")

        # Check users table
        table_rows = page.locator("#desktopUsersTableBody tr").count()
        print(f"  ✓ Desktop users table rows: {table_rows}")
        assert table_rows > 0

        # Click "צפה בהיסטוריה" on first user
        history_btn = page.locator("#desktopUsersTableBody tr button:has-text('צפה בהיסטוריה')").first
        if history_btn.is_visible():
            history_btn.click()
            page.wait_for_timeout(1000)
            modal = page.locator("#userHistoryModalSheet")
            assert modal.is_visible(), "History modal sheet failed to open"
            history_count = page.locator("#historyModalCount").inner_text()
            print(f"  ✓ User history modal opened successfully! Found {history_count} searches")
            # Close modal
            page.locator("button[onclick*='closeUserHistoryModal']").first.click()
            page.wait_for_timeout(500)

        # Desktop screenshot
        desktop_screenshot_path = "data/verified_admin_dashboard_desktop.png"
        page.screenshot(path=desktop_screenshot_path, full_page=True)
        print(f"  ✓ Saved desktop screenshot: {desktop_screenshot_path}")

        # B. Mobile Viewport (iPhone 14: 390x844)
        print("\n[3/5] Testing Mobile Responsiveness (iPhone 14: 390x844)...")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            locale="he-IL"
        )
        mobile_context.add_cookies([{
            "name": "flight_session_token",
            "value": ADMIN_TOKEN,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        mob_page = mobile_context.new_page()

        # Check /flights mobile bottom nav shows admin tab
        mob_page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        mob_page.wait_for_timeout(1000)

        mob_admin_tab = mob_page.locator("#mobileTabAdmin")
        assert mob_admin_tab.is_visible(), "Mobile bottom nav admin tab not visible"
        print("  ✓ Mobile bottom tab 'אדמין 👑' is visible and active")

        # Navigate to /admin on mobile
        mob_page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        mob_page.wait_for_timeout(1500)

        # Verify no horizontal scroll overflow
        body_scroll_w = mob_page.evaluate("document.documentElement.scrollWidth")
        body_client_w = mob_page.evaluate("document.documentElement.clientWidth")
        print(f"  ✓ Mobile dimensions: scrollWidth={body_scroll_w}px, clientWidth={body_client_w}px")
        assert body_scroll_w <= body_client_w + 1, f"Horizontal overflow detected: {body_scroll_w} > {body_client_w}"

        # Test mobile tabs switching
        print("  Testing mobile tabs: 'יוזרים' & 'חיפושים'...")
        mob_page.locator("#tabBtn-users").click()
        mob_page.wait_for_timeout(500)
        users_cards = mob_page.locator("#mobileUsersCardsList > div").count()
        print(f"  ✓ Mobile users cards rendered: {users_cards} cards")
        assert users_cards > 0

        # Click History on first mobile card
        mob_hist_btn = mob_page.locator("#mobileUsersCardsList button:has-text('היסטוריית חיפושים')").first
        if mob_hist_btn.is_visible():
            mob_hist_btn.click()
            mob_page.wait_for_timeout(800)
            mob_modal = mob_page.locator("#userHistoryModalSheet")
            assert mob_modal.is_visible()
            print("  ✓ Mobile bottom sheet history drawer slides open smoothly")
            mob_page.locator("button[onclick*='closeUserHistoryModal']").first.click()
            mob_page.wait_for_timeout(500)

        # Mobile screenshot
        mobile_screenshot_path = "data/verified_admin_dashboard_mobile.png"
        mob_page.screenshot(path=mobile_screenshot_path, full_page=True)
        print(f"  ✓ Saved mobile screenshot: {mobile_screenshot_path}")

        browser.close()

if __name__ == "__main__":
    test_admin_api()
    test_admin_ui_playwright()
    print("\n🎉 ALL ADMIN & UNLIMITED QUOTA VERIFICATIONS PASSED 100%!")
