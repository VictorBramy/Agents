import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_chrome_bluebird():
    url = "https://booking.bluebirdair.com/flight-results/TLV-VIE/2026-11-26/2026-11-30/1/0/0"
    print(f"Opening in Chrome: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        page = await context.new_page()
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(4000)
        
        print("Status:", resp.status if resp else "None")
        print("Final URL:", page.url)
        print("Title:", await page.title())
        
        body_text = await page.inner_text("body")
        print("Has TLV:", "TLV" in body_text or "Tel Aviv" in body_text)
        print("Has VIE:", "VIE" in body_text or "Vienna" in body_text)
        print("Has dates:", "26" in body_text and "30" in body_text)
        print("Body excerpt (first 500 chars):", body_text[:500].replace("\n", " "))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_chrome_bluebird())
