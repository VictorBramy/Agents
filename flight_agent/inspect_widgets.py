import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_widgets():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        await page.goto("https://www.bluebirdair.com/", wait_until="networkidle", timeout=25000)
        
        # Look for interactive elements, dropdowns, buttons with flight keywords
        elements = await page.eval_on_selector_all(
            "button, a, div[class*='search'], div[class*='flight'], div[class*='booking'], div[class*='ibe'], div[class*='widget']",
            "els => els.map(e => ({tag: e.tagName, text: e.innerText ? e.innerText.slice(0, 100).replace(/\\n/g, ' ') : '', class: e.className, id: e.id, href: e.href}))"
        )
        print(f"Found {len(elements)} relevant elements:")
        for el in elements:
            if any(k in el['text'].lower() or k in el['class'].lower() or k in (el['href'] or '').lower() for k in ['book', 'flight', 'origin', 'destination', 'from', 'to', 'athens', 'tel aviv', 'search']):
                print(el)

        # Check for destination links
        dest_links = await page.eval_on_selector_all(
            "a[href*='Destination'], a[href*='flight'], a[href*='book']",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
        )
        print("\nDestination links:")
        for dl in dest_links:
            print(dl)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_widgets())
