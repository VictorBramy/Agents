import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_arkia():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(locale="he-IL")
        print("Visiting Arkia...")
        await page.goto("https://www.arkia.co.il/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)
        print("Title:", await page.title())
        print("URL:", page.url)
        
        # Check inputs, buttons or search forms
        inps = await page.eval_on_selector_all(
            "input, select, button",
            "els => els.map(e => ({id: e.id, name: e.name, type: e.type, val: e.value, text: (e.innerText || '').slice(0, 30)}))"
        )
        for i in inps:
            if any(k in (i['id'] + i['name'] + i['text']).lower() for k in ['date', 'dest', 'from', 'to', 'fly', 'flight', 'search']):
                print(i)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_arkia())
