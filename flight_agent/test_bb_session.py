import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("1. Visiting home...")
        await page.goto("https://www.bluebirdair.com/", wait_until="networkidle", timeout=20000)
        
        print("2. Navigating to flight results...")
        url = "https://booking.bluebirdair.com/flight-results/TLV-VIE/2026-11-26/2026-11-30/1/0/0"
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)
        
        print("Final URL:", page.url)
        print("Title:", await page.title())
        body = await page.inner_text("body")
        print("Has text:", len(body))
        print("Body snippet:", body[:300].replace("\n", " "))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_session())
