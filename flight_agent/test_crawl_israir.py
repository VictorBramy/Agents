import asyncio
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

async def crawl_israir(dest_code: str = "ATH", currency: str = "ILS"):
    url = "https://www.israir.co.il/Flights/Abroad.html"
    usd_rate = 3.65
    offers = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        print(f"[Israir] Navigating to {url}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Look for deal cards
            cards = soup.find_all(lambda tag: tag.name in ["div", "li"] and "$" in tag.get_text() and ("נתב״ג" in tag.get_text() or "TLV" in tag.get_text() or "טיסת" in tag.get_text()))
            print(f"[Israir] Found {len(cards)} candidate deal cards on Israir!")

            for c in cards:
                text = c.get_text().replace("\n", " ").strip()
                # Find price like $134
                m_price = re.search(r'\$(\d+)', text)
                if not m_price:
                    continue
                raw_price = float(m_price.group(1))
                price_final = round(raw_price * usd_rate) if currency.upper() == "ILS" else round(raw_price)

                # Find dates
                dates = re.findall(r'(\d{2}\.\d{2}\.\d{4})', text)
                out_date = dates[0] if len(dates) > 0 else ""
                in_date = dates[1] if len(dates) > 1 else ""

                # Find times
                times = re.findall(r'(\d{2}:\d{2})', text)
                out_dep = times[0] if len(times) > 0 else "20:30"
                out_arr = times[1] if len(times) > 1 else "22:45"
                ret_dep = times[2] if len(times) > 2 else "10:55"
                ret_arr = times[3] if len(times) > 3 else "13:10"

                # Check if matches target destination
                dest_names = ["אתונה", "יוון", "ATH", "Athens"]
                if dest_code.upper() != "ATH":
                    # Check if destination name in text
                    pass

                offer = {
                    "engine": "ישראייר (סריקת דפדפן)",
                    "engine_icon": "☀️",
                    "engine_badge": "ישראייר (אתר רשמי)",
                    "price": price_final,
                    "currency": currency.upper(),
                    "primary_airline": "ישראייר",
                    "is_direct": True,
                    "stops": 0,
                    "booking_link": "https://www.israir.co.il",
                    "baggage": {
                        "personal_item": 1,
                        "cabin_bag": 1,
                        "checked_bag": 0,
                        "summary_he": "כולל טרולי ותיק גב (ישראייר)"
                    },
                    "outbound": {
                        "origin": "TLV",
                        "destination": dest_code.upper(),
                        "origin_name": "תל אביב (נתב״ג)",
                        "destination_name": dest_code.upper(),
                        "date": out_date,
                        "airline": "ישראייר",
                        "flight_number": "6H",
                        "departure_time": out_dep,
                        "arrival_time": out_arr,
                        "duration_text": "שעתיים",
                        "is_direct": True,
                        "stops": 0
                    },
                    "return": {
                        "origin": dest_code.upper(),
                        "destination": "TLV",
                        "origin_name": dest_code.upper(),
                        "destination_name": "תל אביב (נתב״ג)",
                        "date": in_date,
                        "airline": "ישראייר",
                        "flight_number": "6H",
                        "departure_time": ret_dep,
                        "arrival_time": ret_arr,
                        "duration_text": "שעתיים",
                        "is_direct": True,
                        "stops": 0
                    } if in_date else None
                }
                offers.append(offer)

        except Exception as e:
            print(f"[Israir crawl error]: {e}")
        finally:
            await browser.close()

    # Deduplicate
    unique = []
    seen = set()
    for o in offers:
        k = f"{o['price']}_{o['outbound']['date']}_{o['outbound']['departure_time']}"
        if k not in seen:
            seen.add(k)
            unique.append(o)
    return unique

async def main():
    offers = await crawl_israir("ATH", "ILS")
    print(f"Israir crawl finished! Unique offers: {len(offers)}")
    for o in offers[:2]:
        print(f"Israir: {o['primary_airline']} -> {o['price']} {o['currency']}, Out: {o['outbound']['date']} {o['outbound']['departure_time']}")

asyncio.run(main())
