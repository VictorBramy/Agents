import asyncio
from playwright.async_api import async_playwright

async def inspect_urls():
    urls = [
        ("Google Flights El Al", "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjYyAkxZagUSA1RMVnIFEgNWSUUaHhIKMjAyNi0xMS0zMDICTFlqBRIDVklFcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"),
        ("Google Flights BlueBird", "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjYyAkJaagUSA1RMVnIFEgNWSUUaHhIKMjAyNi0xMS0zMDICQlpqBRIDVklFcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"),
        ("Secret Flights Redirect", "https://fly.secretflights.co.il/redirect?origin=TLV&destination=VIE&out_date=2027-06-01&direct=true&associateid=8&cabinclass=economy&alert=false&deal_airline=LY&in_date=2027-06-09&price=289&flight_times=17%3A30%7C20%3A10%7C10%3A35%7C14%3A55&deal_key=f5657c8857781d55244295dd0d12ea5d&campaign=flexible")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for name, url in urls:
            try:
                print(f"\n--- Testing {name} ---")
                resp = await page.goto(url, wait_until="networkidle", timeout=15000)
                final_url = page.url
                title = await page.title()
                print(f"Status: {resp.status if resp else 'None'}")
                print(f"Final URL: {final_url}")
                print(f"Title: {title}")
            except Exception as e:
                print(f"Error testing {name}: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_urls())
