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
        
        # ===============================================================
        # 1. DESKTOP TEST: Verify NO biometric options offered on computer
        # ===============================================================
        print("\n--- 1. Testing DESKTOP (Computer) View ---")
        desktop_ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        desktop_page = await desktop_ctx.new_page()
        await desktop_page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle")
        
        # Open Login Modal
        print("Opening Login modal on Desktop...")
        await desktop_page.evaluate("openAuthModal('login')")
        await desktop_page.wait_for_timeout(600)
        
        # Check biometric section visibility on Desktop
        bio_login_visible = await desktop_page.is_visible("#mobileBiometricAuthSection")
        print(f"Desktop: Biometric login section visible? {bio_login_visible} (Expected: False)")
        assert not bio_login_visible, "ERROR: Biometric login section should NOT be visible on Desktop!"
        
        desktop_auth_shot = os.path.join(ARTIFACT_DIR, "verified_desktop_auth_no_biometrics.png")
        await desktop_page.screenshot(path=desktop_auth_shot, full_page=False)
        print(f"Desktop auth screenshot saved: {desktop_auth_shot}")
        
        # Close auth modal & check Subscription modal on Desktop
        await desktop_page.evaluate("closeAuthModal()")
        await desktop_page.evaluate("openSubscriptionModal()")
        await desktop_page.wait_for_timeout(600)
        
        bio_sub_banner_visible = await desktop_page.is_visible("#subModalBiometricDeviceBanner")
        print(f"Desktop: Subscription biometric device banner visible? {bio_sub_banner_visible} (Expected: False)")
        assert not bio_sub_banner_visible, "ERROR: Biometric device banner should NOT be visible on Desktop!"
        
        desktop_sub_shot = os.path.join(ARTIFACT_DIR, "verified_desktop_subscription_no_biometrics.png")
        await desktop_page.screenshot(path=desktop_sub_shot, full_page=False)
        print(f"Desktop subscription screenshot saved: {desktop_sub_shot}")
        
        # ===============================================================
        # 2. MOBILE TEST: Verify biometric IS offered on Mobile Phone
        # ===============================================================
        print("\n--- 2. Testing MOBILE PHONE View ---")
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        )
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto("http://127.0.0.1:8080/flights", wait_until="networkidle")
        
        # Open Login Modal on Mobile
        print("Opening Login modal on Mobile Phone...")
        await mobile_page.evaluate("openAuthModal('login')")
        await mobile_page.wait_for_timeout(600)
        
        mobile_bio_visible = await mobile_page.is_visible("#mobileBiometricAuthSection")
        print(f"Mobile Phone: Biometric login section visible? {mobile_bio_visible} (Expected: True)")
        assert mobile_bio_visible, "ERROR: Biometric login section SHOULD be visible on Mobile Phone!"
        
        mobile_auth_shot = os.path.join(ARTIFACT_DIR, "verified_mobile_auth_has_biometrics.png")
        await mobile_page.screenshot(path=mobile_auth_shot, full_page=False)
        print(f"Mobile auth screenshot saved: {mobile_auth_shot}")
        
        await browser.close()
        print("\n=== ALL ASSERTIONS PASSED! Biometric is strictly reserved for mobile phones ===")

if __name__ == "__main__":
    asyncio.run(main())
