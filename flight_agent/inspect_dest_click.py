import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_dest_search_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(locale="en-US")
        
        await page.goto("https://booking.bluebirdair.com/Destinations/VIENNA", wait_until="networkidle", timeout=25000)
        
        # Check onclick or event listeners on the search button
        btn_info = await page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button, input[type=\"submit\"], .btn_search, a.btn'));
            return btns.map(b => ({
                text: b.innerText,
                onclick: b.getAttribute('onclick'),
                type: b.type,
                id: b.id,
                class: b.className
            }));
        }""")
        print("Buttons on Destinations/VIENNA:")
        for b in btn_info:
            print(b)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dest_search_click())
