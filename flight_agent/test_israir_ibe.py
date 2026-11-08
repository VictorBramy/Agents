import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_israir():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(locale="he-IL")
        await page.goto("https://www.israir.co.il/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        
        # Check forms and search URL structure
        forms = await page.query_selector_all("form")
        for i, f in enumerate(forms):
            action = await f.get_attribute("action")
            method = await f.get_attribute("method")
            print(f"Israir form {i}: action={action}, method={method}")
            
        # Check any inputs
        inps = await page.eval_on_selector_all("input, select", "els => els.map(e => ({id: e.id, name: e.name, type: e.type, val: e.value}))")
        for inp in inps:
            if any(k in (inp['id'] + inp['name']).lower() for k in ['dest', 'from', 'to', 'date', 'flight']):
                print(inp)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_israir())
