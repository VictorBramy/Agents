import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()
        url = "https://kiwi.com/u/c7jcwx"
        print("Navigating to", url)
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(4000)

        # Accept cookies if present
        try:
            accept_btn = await page.query_selector("#cookies_accept, button:has-text('Accept')")
            if accept_btn:
                await accept_btn.click()
                print("Cookies accepted.")
        except Exception as e:
            print("Cookie error:", e)

        await page.wait_for_timeout(1000)

        # Initial price on page
        body_text_init = await page.inner_text("body")
        print("--- Initial Prices on Page ---")
        for line in body_text_init.split("\n"):
            if "₪" in line or "ILS" in line or "Total" in line:
                if line.strip():
                    print("  Init:", line.strip())

        # Fill Passenger 0 dummy info
        print("Filling Passenger 0...")
        try:
            await page.fill("input[name='passengers.0.firstname']", "Israel")
            await page.fill("input[name='passengers.0.surname']", "Israeli")
            await page.select_option("select[name='passengers.0.nationality']", "IL")
            await page.fill("input[name*='passengers.0.birthDay']", "15")
            await page.select_option("select[name*='passengers.0.birthMonth']", "5")
            await page.fill("input[name*='passengers.0.birthYear']", "1990")
            print("✓ Passenger 0 filled.")
        except Exception as e:
            print("Pax 0 error:", e)

        # Fill Passenger 1 dummy info
        print("Filling Passenger 1...")
        try:
            await page.fill("input[name='passengers.1.firstname']", "Sara")
            await page.fill("input[name='passengers.1.surname']", "Israeli")
            await page.select_option("select[name='passengers.1.nationality']", "IL")
            await page.fill("input[name*='passengers.1.birthDay']", "20")
            await page.select_option("select[name*='passengers.1.birthMonth']", "8")
            await page.fill("input[name*='passengers.1.birthYear']", "1992")
            print("✓ Passenger 1 filled.")
        except Exception as e:
            print("Pax 1 error:", e)

        # Check baggage add buttons
        add_20kg_btns = await page.query_selector_all("button[aria-label='Add 20 kg']")
        print(f"Found {len(add_20kg_btns)} 'Add 20 kg' buttons.")
        for idx, btn in enumerate(add_20kg_btns):
            print(f"Clicking 'Add 20 kg' for Passenger {idx}...")
            await btn.click()
            await page.wait_for_timeout(1500)

        # Click View price breakdown if present
        breakdown_btn = await page.query_selector("button:has-text('View price breakdown'), button:has-text('price breakdown')")
        if breakdown_btn:
            print("Clicking 'View price breakdown'...")
            await breakdown_btn.click()
            await page.wait_for_timeout(2000)

        # Print all lines with prices and baggage
        body_text_after = await page.inner_text("body")
        print("\n--- After Adding 20kg Baggage for Both Passengers ---")
        for line in body_text_after.split("\n"):
            line_str = line.strip()
            if any(k in line_str for k in ["₪", "Total", "Baggage", "baggage", "passenger", "Passenger", "Flight"]):
                if len(line_str) < 100:
                    print("  >>", line_str)

        await page.screenshot(path="data/kiwi_checkout_baggage_breakdown.png", full_page=True)
        print("Screenshot saved to data/kiwi_checkout_baggage_breakdown.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
