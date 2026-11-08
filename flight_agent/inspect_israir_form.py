import asyncio
from playwright.async_api import async_playwright

async def inspect_israir():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        print("Navigating to Israir...")
        await page.goto("https://www.israir.co.il", wait_until="networkidle", timeout=25000)
        
        title = await page.title()
        print("Title:", title)

        # Look for forms, inputs, destination selectors
        inputs = await page.query_selector_all("input")
        print("Total inputs:", len(inputs))
        for inp in inputs[:10]:
            name = await inp.get_attribute("name")
            id_attr = await inp.get_attribute("id")
            placeholder = await inp.get_attribute("placeholder")
            print(f"  Input: id={id_attr}, name={name}, placeholder={placeholder}")

        # Check for destination dropdown or buttons
        buttons = await page.query_selector_all("button")
        print("Total buttons:", len(buttons))
        for b in buttons[:10]:
            txt = (await b.inner_text()).strip().replace("\n", " ")
            print(f"  Button: '{txt}'")

        await browser.close()

asyncio.run(inspect_israir())
