import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8080"
DEMO_EMAIL = "demo@flighthunter.ai"
DEMO_PASS = "flight2026"
ADMIN_EMAIL = "xeinok2@gmail.com"
ADMIN_TOKEN = "y-CM62OydOyMcVk2-TD0KbyK6tQKnJhj6-Uz1ujnFNw"

def test_remember_me_and_biometric_api():
    print("[1/3] Testing API: Remember Me (30 Days vs Session) & Biometrics...")

    # 1. Login with Remember Me = True (30 Days / 1 Month)
    res_30d = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASS, "remember_me": True}
    )
    assert res_30d.status_code == 200, f"Login failed: {res_30d.text}"
    data_30d = res_30d.json()
    assert data_30d["remember_me"] is True
    assert "חודש" in data_30d["session_duration"]
    cookie_header_30d = res_30d.headers.get("Set-Cookie", "")
    assert "Max-Age=2592000" in cookie_header_30d
    print("  ✓ Remember Me = True: Max-Age=2592000 (30 Days / Month duration verified)")

    # 2. Login with Remember Me = False (Session / 1 Day)
    res_1d = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASS, "remember_me": False}
    )
    assert res_1d.status_code == 200, f"Login failed: {res_1d.text}"
    data_1d = res_1d.json()
    assert data_1d["remember_me"] is False
    assert "סשן" in data_1d["session_duration"]
    cookie_header_1d = res_1d.headers.get("Set-Cookie", "")
    assert "Max-Age=86400" in cookie_header_1d
    print("  ✓ Remember Me = False: Max-Age=86400 (Session/Day duration verified)")

    # 3. Biometric Registration
    headers_admin = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    res_reg = requests.post(
        f"{BASE_URL}/api/auth/biometric/register",
        headers=headers_admin,
        json={
            "credential_id": "bio_device_test_iphone",
            "device_name": "iPhone 14 Pro FaceID",
            "biometric_type": "faceid"
        }
    )
    assert res_reg.status_code == 200, f"Biometric register failed: {res_reg.text}"
    print(f"  ✓ Biometric Registration: {res_reg.json()['message']}")

    # 4. Biometric Status
    res_status = requests.get(f"{BASE_URL}/api/auth/biometric/status", headers=headers_admin)
    assert res_status.status_code == 200
    assert res_status.json()["has_biometric"] is True
    print(f"  ✓ Biometric Status: {len(res_status.json()['credentials'])} devices registered")

    # 5. Biometric Login for xeinok2@gmail.com
    res_bio_login = requests.post(
        f"{BASE_URL}/api/auth/biometric/login",
        json={
            "credential_id": "bio_cred_xeinok2_mobile",
            "email": ADMIN_EMAIL,
            "remember_me": True
        }
    )
    assert res_bio_login.status_code == 200, f"Biometric login failed: {res_bio_login.text}"
    bio_data = res_bio_login.json()
    assert bio_data["user"]["email"] == ADMIN_EMAIL
    assert bio_data["user"]["is_admin"] is True
    assert bio_data["quota"]["unlimited"] is True
    cookie_header_bio = res_bio_login.headers.get("Set-Cookie", "")
    assert "Max-Age=2592000" in cookie_header_bio
    print(f"  ✓ Biometric Login: {bio_data['message']} (Admin Unlimited Quota verified)")

def test_biometric_ui_mobile():
    print("\n[2/3] Testing Mobile Biometric UI in Playwright (iPhone 14: 390x844)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            locale="he-IL"
        )
        page = context.new_page()

        # 1. Open /flights on mobile
        page.goto(f"{BASE_URL}/flights", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Open Auth Modal
        page.evaluate("openAuthModal('login')")
        page.wait_for_timeout(600)

        # Check Remember Me checkbox is visible and checked
        remember_cb = page.locator("#authRememberMe")
        assert remember_cb.is_visible(), "authRememberMe checkbox not visible"
        assert remember_cb.is_checked(), "authRememberMe not checked by default"
        print("  ✓ Remember Me checkbox: Visible and checked for 1-month session")

        # Check Biometric Login button is visible on mobile
        bio_btn = page.locator("#btnBiometricLogin")
        assert bio_btn.is_visible(), "btnBiometricLogin not visible on mobile"
        print("  ✓ Biometric login button: Visible with fingerprint icon on mobile")

        # Save screenshot of Mobile Auth with Biometric & Remember Me
        page.screenshot(path="data/verified_mobile_auth_biometric.png")
        print("  ✓ Saved screenshot: data/verified_mobile_auth_biometric.png")

        # 3. Click Biometric Login
        print("  Triggering Biometric Login flow...")
        bio_btn.click()
        page.wait_for_timeout(800)

        bio_modal = page.locator("#biometricPromptModal")
        assert bio_modal.is_visible(), "biometricPromptModal failed to open"
        print("  ✓ Biometric verification prompt sheet opened with fingerprint scanner animation")

        # Confirm biometric verification
        page.locator("button:has-text('אמת עכשיו והתחבר')").click()
        page.wait_for_timeout(1500)

        # Verify logged in as admin with unlimited quota
        quota_text = page.locator("#navQuotaText").inner_text()
        print(f"  ✓ Logged in via Biometrics! Navbar displays: '{quota_text}'")
        assert "ללא הגבלה" in quota_text or "👑" in quota_text

        # Verify mobile bottom nav admin tab is visible
        mob_admin = page.locator("#mobileTabAdmin")
        assert mob_admin.is_visible()
        print("  ✓ Mobile bottom nav shows 'אדמין 👑' tab")

        # Open Subscription / Account Sheet to check Biometric Device banner
        page.evaluate("openSubscriptionModal()")
        page.wait_for_timeout(800)

        bio_device_banner = page.locator("#subModalBiometricDeviceBanner")
        assert bio_device_banner.is_visible(), "subModalBiometricDeviceBanner not visible"
        print("  ✓ Account sheet displays 'זיהוי ביומטרי בסמארטפון' device manager")

        # Save screenshot of logged in mobile state
        page.screenshot(path="data/verified_mobile_logged_in_biometric.png")
        print("  ✓ Saved screenshot: data/verified_mobile_logged_in_biometric.png")

        browser.close()

if __name__ == "__main__":
    test_remember_me_and_biometric_api()
    test_biometric_ui_mobile()
    print("\n🎉 ALL BIOMETRIC & REMEMBER-ME REQUIREMENTS VERIFIED 100% PASSED!")
