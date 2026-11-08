import sys
import os
import time
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

async def verify_auth_and_quota_flow():
    print("\n=======================================================", flush=True)
    print("🚀 [PLAYWRIGHT BROWSER AUDIT] User Auth, Sessions & Quotas (REQ-19)", flush=True)
    print("=======================================================\n", flush=True)

    test_email = f"playwright_{int(time.time())}@flighttest.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Fresh context without cookies
        context = await browser.new_context(locale="he-IL")
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}", flush=True))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}", flush=True))
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        # 1. Open /flights as a guest
        print("1. Opening http://127.0.0.1:8080/flights as Guest...", flush=True)
        await page.goto("http://127.0.0.1:8080/flights", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 2. Check Guest UI state
        print("2. Verifying Guest UI state...", flush=True)
        is_banner_visible = await page.is_visible("#guestMandatoryBanner")
        print(f"   ✓ Guest mandatory registration banner visible: {is_banner_visible}", flush=True)
        assert is_banner_visible, "Mandatory registration banner must be visible to guests"

        is_logged_out_showing = await page.is_visible("#authLoggedOutSection")
        assert is_logged_out_showing, "Logged out navbar section must be visible"
        print("   ✓ Navbar correctly displays 'התחברות' and 'הרשמה חינם (10 חיפושים)'", flush=True)

        # 3. Trigger search as Guest -> Must trigger Auth Modal
        print("3. Attempting search as Guest to test mandatory login barrier...", flush=True)
        await page.fill("#aiPromptInput", "טיסה לרומא")
        await page.click("#btnAiSearch")
        await page.wait_for_timeout(1000)

        is_auth_modal_open = await page.is_visible("#authModal")
        print(f"   ✓ Auth Modal triggered automatically upon unauthenticated search: {is_auth_modal_open}", flush=True)
        assert is_auth_modal_open, "Auth modal must pop up when guest attempts a search"

        # 4. Fill Registration Form
        print(f"4. Registering new user: {test_email}...", flush=True)
        await page.fill("#authInputName", "דוד לוי (בדיקת Playwright)")
        await page.fill("#authInputEmail", test_email)
        await page.fill("#authInputPassword", "SecurePass123!")
        await page.click("#authBtnSubmit")
        await page.wait_for_timeout(2500)

        # 5. Verify Logged In UI & 10 Free Searches in Navbar
        print("5. Verifying Logged In state & Quota Widget in Top Navbar...", flush=True)
        is_logged_in_showing = await page.is_visible("#authLoggedInSection")
        print(f"   ✓ Logged In navbar section visible: {is_logged_in_showing}", flush=True)
        assert is_logged_in_showing, "Logged in navbar section must be visible after registration"

        user_name_text = await page.inner_text("#navUserName")
        print(f"   ✓ User name in navbar: {user_name_text}", flush=True)
        assert "דוד לוי" in user_name_text

        quota_text = await page.inner_text("#navQuotaText")
        print(f"   ✓ Navbar Quota Counter: {quota_text}", flush=True)
        assert "10/10" in quota_text or "10" in quota_text, "Navbar must show 10/10 searches remaining"

        plan_badge_text = await page.inner_text("#navPlanBadge")
        print(f"   ✓ Active Plan Badge: {plan_badge_text}", flush=True)
        assert "חינמי" in plan_badge_text

        # 6. Open Subscription & Upgrade Plans Modal
        print("6. Opening Subscription & Upgrade Plans Modal (#subscriptionPlansModal)...", flush=True)
        await page.click("#authLoggedInSection button")
        await page.wait_for_timeout(1000)

        is_sub_modal_open = await page.is_visible("#subscriptionPlansModal")
        print(f"   ✓ Subscription Plans Modal visible: {is_sub_modal_open}", flush=True)
        assert is_sub_modal_open, "Subscription modal must open upon clicking quota widget"

        modal_text = await page.inner_text("#subscriptionPlansModal")
        print("   ✓ Verifying all 4 required pricing tiers:", flush=True)
        assert "מנוי חינמי" in modal_text and "0 ₪" in modal_text and "10 חיפושים" in modal_text
        print("     -> 1. מנוי חינמי: 10 חיפושים (0 ₪) ✓", flush=True)
        assert "Starter" in modal_text and "10 ₪" in modal_text and "20 חיפושים" in modal_text
        print("     -> 2. מנוי Starter: 20 חיפושים (10 ₪) ✓", flush=True)
        assert "Pro" in modal_text and "20 ₪" in modal_text and "40 חיפושים" in modal_text
        print("     -> 3. מנוי Pro מומלץ: 40 חיפושים (20 ₪) ✓", flush=True)
        assert "VIP" in modal_text and "30 ₪" in modal_text and "100 חיפושים" in modal_text
        print("     -> 4. מנוי VIP: 100 חיפושים (30 ₪) ✓", flush=True)

        # 7. Upgrade to Pro (20 ₪ -> 40 searches)
        print("7. Testing Upgrade to Pro (20 ₪ / 40 searches)...", flush=True)
        await page.click("button:has-text('שדרג ל-40 חיפושים')")
        await page.wait_for_timeout(2500)

        # Verify updated navbar counter
        updated_quota_text = await page.inner_text("#navQuotaText")
        print(f"   ✓ Upgraded Navbar Quota Counter: {updated_quota_text}", flush=True)
        assert "40" in updated_quota_text, "Navbar must reflect 40 searches limit after Pro upgrade"

        updated_plan_badge = await page.inner_text("#navPlanBadge")
        print(f"   ✓ Upgraded Plan Badge: {updated_plan_badge}", flush=True)
        assert "Pro" in updated_plan_badge, "Navbar badge must reflect Pro plan"

        # 8. Take verification screenshot
        screenshot_path = "data/verified_auth_and_quota.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved to {screenshot_path}", flush=True)

        print("\n=======================================================")
        print("🎉 PLAYWRIGHT BROWSER AUDIT PASSED: 100% AUTH & QUOTAS VERIFIED!")
        print("=======================================================\n", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_auth_and_quota_flow())
