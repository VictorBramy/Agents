import asyncio
from playwright.async_api import async_playwright

async def inspect_dom():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Check Google Flights El Al URL
        url_gf = "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjYyAkxZagUSA1RMVnIFEgNWSUUaHhIKMjAyNi0xMS0zMDICTFlqBRIDVklFcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"
        await page.goto(url_gf, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)
        
        # Check if dates or airports are in DOM
        text = await page.inner_text("body")
        print("--- GOOGLE FLIGHTS EL AL ---")
        print("Contains TLV/נתבג:", ("נתב" in text or "TLV" in text))
        print("Contains VIE/וינה:", ("וינה" in text or "VIE" in text))
        print("Contains 26/11:", ("26" in text and "11" in text))
        print("Contains אל על:", ("אל על" in text or "El Al" in text))
        print("Any flights listed?:", ("בחר טיסה" in text or "טיסות מומלצות" in text or "תוצאות אחרות" in text or "לא נמצאו טיסות" in text))
        lines = [line.strip() for line in text.split("\n") if any(k in line for k in ["טיסה", "אל על", "₪", "לא נמצאו", "וינה", "תל אביב"])]
        print("Sample lines:", lines[:10])

        # 2. Check Secret Flights Redirect
        url_sf = "https://fly.secretflights.co.il/redirect?origin=TLV&destination=VIE&out_date=2027-06-01&direct=true&associateid=8&cabinclass=economy&alert=false&deal_airline=LY&in_date=2027-06-09&price=289&flight_times=17%3A30%7C20%3A10%7C10%3A35%7C14%3A55&deal_key=f5657c8857781d55244295dd0d12ea5d&campaign=flexible"
        print("\n--- SECRET FLIGHTS REDIRECT ---")
        await page.goto(url_sf, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(4000)
        print("SF Final URL:", page.url)
        sf_title = await page.title()
        print("SF Title:", sf_title)
        sf_text = await page.inner_text("body")
        print("SF Text excerpt:", sf_text[:300].replace('\n', ' '))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dom())
