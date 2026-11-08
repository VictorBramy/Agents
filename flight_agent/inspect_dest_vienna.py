import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_dest_vienna():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        url = "https://booking.bluebirdair.com/Destinations/VIENNA"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=25000)
        print("Final URL:", page.url)
        print("Title:", await page.title())
        
        # Check inputs, buttons, booking form
        inputs = await page.eval_on_selector_all(
            "input, select, button",
            "els => els.map(e => ({tag: e.tagName, type: e.type, id: e.id, name: e.name, text: (e.innerText || '').trim(), val: e.value}))"
        )
        print(f"Total interactive elements: {len(inputs)}")
        for i in inputs:
            if any(k in (i['id'] or '').lower() or k in (i['name'] or '').lower() or k in i['text'].lower() for k in ['date', 'from', 'to', 'fly', 'book', 'search', 'dest', 'origin']):
                print(i)
                
        # Also check page scripts for AeroCRS / booking URL parameters!
        scripts = await page.eval_on_selector_all("script", "els => els.map(e => e.src || e.innerText.slice(0, 300))")
        for s in scripts:
            if "aerocrs" in s.lower() or "booking" in s.lower() or "flight" in s.lower():
                print("Script snippet:", s[:150])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dest_vienna())
