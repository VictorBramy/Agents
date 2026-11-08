import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_bluebird():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        print("Navigating to https://www.bluebirdair.com...")
        await page.goto("https://www.bluebirdair.com", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)
        
        # Check current URL, form action, input names
        print("Current URL:", page.url)
        print("Title:", await page.title())
        
        forms = await page.query_selector_all("form")
        print(f"Forms count: {len(forms)}")
        for i, form in enumerate(forms):
            action = await form.get_attribute("action")
            method = await form.get_attribute("method")
            print(f"Form {i}: action={action}, method={method}")
            inputs = await form.query_selector_all("input, select")
            for inp in inputs:
                name = await inp.get_attribute("name")
                id_attr = await inp.get_attribute("id")
                type_attr = await inp.get_attribute("type")
                val = await inp.get_attribute("value")
                print(f"   input: name={name}, id={id_attr}, type={type_attr}, val={val}")
                
        # Also check any links or iframes with "booking" or similar
        links = await page.eval_on_selector_all(
            "a[href*='book'], a[href*='flight'], iframe",
            "els => els.map(e => ({tag: e.tagName, href: e.href || e.src}))"
        )
        print("Booking links/iframes found:", links[:10])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_bluebird())
