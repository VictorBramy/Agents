import asyncio
from playwright.async_api import async_playwright

async def inspect_sf_redirect():
    qs = "origin=TLV&destination=SKG&out_date=2027-10-20&direct=true&associateid=8&cabinclass=economy&alert=false&deal_airline=W6&in_date=2027-10-27&price=117&price_premium=104&flight_times=08%3A00%7C10%3A35%7C09%3A00%7C11%3A25&deal_key=8368961848be8f0fd5a937951236f520&campaign=flexible&adults=1&children=0&infants=0"
    url = f"https://fly.secretflights.co.il/redirect-page?{qs}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=12000, wait_until="domcontentloaded")
            for _ in range(8):
                await page.wait_for_timeout(1000)
                print("Current page URL:", page.url)
        except Exception as e:
            print("Goto exception:", e)
            print("Current page URL after exc:", page.url)
        await browser.close()

asyncio.run(inspect_sf_redirect())
