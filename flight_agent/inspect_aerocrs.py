import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_aerocrs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        url = "https://booking.bluebirdair.com/"
        await page.goto(url, wait_until="networkidle", timeout=25000)
        
        # Check all input and button attributes safely
        all_inps = await page.eval_on_selector_all(
            "input, select, button",
            """els => els.map(e => ({
                tag: e.tagName,
                id: e.id || '',
                name: e.name || '',
                class: e.className || '',
                val: e.value || '',
                placeholder: e.placeholder || '',
                text: (e.innerText || '').slice(0, 50).trim()
            }))"""
        )
        print("Relevant inputs/buttons:")
        for el in all_inps:
            combined = (el['id'] + ' ' + el['name'] + ' ' + el['class'] + ' ' + el['placeholder'] + ' ' + el['text']).lower()
            if any(k in combined for k in ['from', 'to', 'dep', 'ret', 'date', 'flight', 'search', 'book']):
                print(el)

        # Look at the aeroCRS.js or search functions
        fn_code = await page.evaluate("""() => {
            let res = {};
            for (let k in window) {
                if (k.toLowerCase().includes('flight') || k.toLowerCase().includes('search') || k.toLowerCase().includes('booking')) {
                    res[k] = typeof window[k];
                }
            }
            return res;
        }""")
        print("\nWindow flight/search keys:", fn_code)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_aerocrs())
