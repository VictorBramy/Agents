import asyncio
import sqlite3
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8080"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "flights.db")
ARTIFACT_DIR = r"C:\Users\A\.gemini\antigravity\brain\f8d0af8f-e11b-4f48-a1e2-498095665c80"

async def run_verification():
    print("=== STARTING FULL BIT PAYMENT VERIFICATION ===")
    
    # 1. Direct Backend Verification
    print("\n--- Phase 1: Backend API Security & Bit Flow ---")
    session = requests.Session()
    
    # Create or login regular test user
    test_email = "bit_traveler@example.com"
    test_password = "SecurePassword123!"
    reg_res = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "ישראל ישראלי"
    })
    if reg_res.status_code == 400: # Already exists
        login_res = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    else:
        assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
        
    me_res = session.get(f"{BASE_URL}/api/auth/me")
    assert me_res.status_code == 200
    user_data = me_res.json()
    print(f"Logged in user: {user_data['user']['email']}, Plan: {user_data['user']['plan_tier']}, Limit: {user_data['quota']['searches_limit']}")
    
    # Reset user to free and clear any test bit payments
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("DELETE FROM bit_payments WHERE user_email = ?", (test_email,))
    c.execute("UPDATE users SET plan_tier = 'free', plan_name = 'חינמי', searches_limit = 10, is_admin = 0 WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()

    # Step 1A: Attempt direct unauthorized upgrade to 'pro' -> MUST BE REJECTED with 402
    print("Testing direct upgrade block...")
    up_res = session.post(f"{BASE_URL}/api/auth/upgrade", json={"plan_tier": "pro"})
    print(f"Direct upgrade response code: {up_res.status_code}")
    assert up_res.status_code == 402, f"Expected 402 Payment Required, got {up_res.status_code}: {up_res.text}"
    assert "0524845131" in up_res.text or "052-4845131" in up_res.text, "Response must include recipient phone 0524845131"
    print("✓ Security Check Passed: Direct unpaid upgrade is strictly blocked with 402 Payment Required.")

    # Step 1B: Submit Bit payment request to 052-4845131
    print("\nSubmitting Bit payment report for Pro (20 ILS)...")
    bit_res = session.post(f"{BASE_URL}/api/auth/bit/submit-payment", json={
        "plan_tier": "pro",
        "sender_phone": "054-9876543"
    })
    assert bit_res.status_code == 200, f"Bit submit failed: {bit_res.text}"
    bit_data = bit_res.json()
    payment_id = bit_data["payment_id"]
    print(f"✓ Bit Payment submitted: ID #{payment_id}, Target: {bit_data['target_phone']}, Amount: {bit_data['amount_ils']} ₪, Status: {bit_data['status']}")
    assert bit_data["target_phone"] == "0524845131", f"Target phone must be 0524845131, got {bit_data['target_phone']}"
    assert bit_data["amount_ils"] == 20, f"Pro plan must be 20 ILS, got {bit_data['amount_ils']}"

    # Step 1C: Check user my-payments
    my_payments = session.get(f"{BASE_URL}/api/auth/bit/my-payments").json()
    assert len(my_payments["payments"]) >= 1
    latest = my_payments["payments"][0]
    assert latest["id"] == payment_id
    assert latest["status"] == "pending"
    print(f"✓ Verified user my-payments has pending payment #{payment_id}")

    # Step 1D: Admin approval flow
    print("\nTesting Admin flow with xeinok2@gmail.com...")
    import secrets
    from datetime import datetime, timedelta
    admin_session = requests.Session()
    admin_token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(days=30)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, user_id, ip_address, user_agent, expires_at) VALUES (?, ?, ?, ?, ?)",
              (admin_token, 8, "127.0.0.1", "AdminTest", expires.isoformat()))
    conn.commit()
    conn.close()
    admin_session.cookies.set("flight_session_token", admin_token)
    
    admin_me = admin_session.get(f"{BASE_URL}/api/auth/me").json()
    assert admin_me["authenticated"] and admin_me["user"]["is_admin"], "Admin authentication failed"
    print(f"✓ Authenticated as Admin: {admin_me['user']['email']}")
    
    # Check Admin Overview
    overview = admin_session.get(f"{BASE_URL}/api/admin/overview").json()
    print(f"Admin KPI Pending Bit Payments: {overview['kpis']['pending_bit_payments']}")
    assert overview['kpis']['pending_bit_payments'] >= 1

    # Check Admin Bit Payments list
    admin_payments = admin_session.get(f"{BASE_URL}/api/admin/bit-payments").json()
    assert admin_payments["total"] >= 1
    found_payment = any(p["id"] == payment_id and p["status"] == "pending" for p in admin_payments["payments"])
    assert found_payment, f"Payment #{payment_id} not found in admin list"
    print(f"✓ Payment #{payment_id} detected in admin queue.")

    # Admin approves payment
    approve_res = admin_session.post(f"{BASE_URL}/api/admin/bit-payments/{payment_id}/approve")
    assert approve_res.status_code == 200, f"Approval failed: {approve_res.text}"
    print(f"✓ Payment approved: {approve_res.json()['message']}")

    # Check that user plan upgraded to Pro and quota is 40
    user_after = session.get(f"{BASE_URL}/api/auth/me").json()
    assert user_after["user"]["plan_tier"] == "pro", f"Expected 'pro', got {user_after['user']['plan_tier']}"
    assert user_after["quota"]["searches_limit"] == 40, f"Expected 40 limit, got {user_after['quota']['searches_limit']}"
    print(f"✓ User plan successfully upgraded! Tier: {user_after['user']['plan_tier']}, Limit: {user_after['quota']['searches_limit']}")

    # 2. Browser UI Verification with Playwright (Mobile & Desktop)
    print("\n--- Phase 2: Playwright UI Verification ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Test A: Mobile Browser on iPhone 14 (390 x 844)
        print("Testing Mobile UI (390x844)...")
        context_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_mobile = await context_mobile.new_page()
        
        # Go to flights page
        await page_mobile.goto(f"{BASE_URL}/flights")
        await page_mobile.wait_for_load_state("networkidle")
        
        import json
        user_json = json.dumps(user_after['user'])
        # Log in on mobile
        await page_mobile.evaluate(f"localStorage.setItem('xeinok_user', JSON.stringify({user_json}));")
        # Set session cookie directly
        cookies = session.cookies.get_dict()
        if "flight_session_token" in cookies:
            await context_mobile.add_cookies([{
                "name": "flight_session_token",
                "value": cookies["flight_session_token"],
                "domain": "127.0.0.1",
                "path": "/"
            }])
        await page_mobile.reload()
        await page_mobile.wait_for_load_state("networkidle")
        # Wait for user session to be active in JS
        await page_mobile.wait_for_function("() => window.currentUser !== null && window.currentUser !== undefined", timeout=5000)
        print("✓ Mobile session active: currentUser is populated")
        
        # Open Subscription Plans Modal
        await page_mobile.evaluate("openSubscriptionModal()")
        await page_mobile.wait_for_timeout(600)

        # Click VIP plan (30 ILS) to trigger Bit modal
        await page_mobile.evaluate("openBitPaymentModal('vip', 'מנוי VIP ללא דאגות (100 חיפושים)', 30)")
        await page_mobile.wait_for_timeout(600)

        # Verify Bit Modal elements
        phone_visible = await page_mobile.is_visible("text=052-4845131")
        assert phone_visible, "Recipient phone 052-4845131 must be visible in modal"
        amount_txt = await page_mobile.locator("#bitAmountDisplay").text_content()
        assert "30" in amount_txt, f"Amount must be 30, got {amount_txt}"
        print(f"✓ Bit Modal open on mobile: recipient phone 052-4845131 and amount {amount_txt} ₪ verified")

        # Fill sender phone
        await page_mobile.fill("#bitSenderPhoneInput", "052-7778899")
        
        # Capture screenshot of Bit Payment Modal
        screenshot_path1 = os.path.join(ARTIFACT_DIR, "verified_bit_payment_modal_mobile.png")
        await page_mobile.screenshot(path=screenshot_path1)
        print(f"✓ Saved mobile Bit modal screenshot to {screenshot_path1}")

        # Test B: Admin Dashboard on Desktop & Mobile
        print("\nTesting Admin Dashboard UI...")
        context_admin = await browser.new_context(viewport={"width": 1280, "height": 800})
        page_admin = await context_admin.new_page()
        
        # Set admin session cookie
        admin_cookies = admin_session.cookies.get_dict()
        if "flight_session_token" in admin_cookies:
            await context_admin.add_cookies([{
                "name": "flight_session_token",
                "value": admin_cookies["flight_session_token"],
                "domain": "127.0.0.1",
                "path": "/"
            }])

        await page_admin.goto(f"{BASE_URL}/admin")
        await page_admin.wait_for_load_state("networkidle")
        await page_admin.wait_for_timeout(800)

        # Switch to Bit tab
        await page_admin.evaluate("switchAdminTab('bit')")
        await page_admin.wait_for_timeout(600)

        # Verify target phone notice banner
        target_in_admin = await page_admin.is_visible("text=052-4845131")
        assert target_in_admin, "Target phone 052-4845131 must be visible in admin section"

        screenshot_path2 = os.path.join(ARTIFACT_DIR, "verified_admin_bit_management_desktop.png")
        await page_admin.screenshot(path=screenshot_path2)
        print(f"✓ Saved admin Bit management screenshot to {screenshot_path2}")

        # Test Mobile view for Admin
        context_admin_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_admin_mobile = await context_admin_mobile.new_page()
        if "flight_session_token" in admin_cookies:
            await context_admin_mobile.add_cookies([{
                "name": "flight_session_token",
                "value": admin_cookies["flight_session_token"],
                "domain": "127.0.0.1",
                "path": "/"
            }])
        await page_admin_mobile.goto(f"{BASE_URL}/admin")
        await page_admin_mobile.wait_for_load_state("networkidle")
        await page_admin_mobile.evaluate("switchAdminTab('bit')")
        await page_admin_mobile.wait_for_timeout(600)

        screenshot_path3 = os.path.join(ARTIFACT_DIR, "verified_admin_bit_management_mobile.png")
        await page_admin_mobile.screenshot(path=screenshot_path3)
        print(f"✓ Saved mobile admin Bit management screenshot to {screenshot_path3}")

        await browser.close()

    print("\n=== ALL BIT PAYMENT TESTS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    asyncio.run(run_verification())
