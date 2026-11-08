import asyncio
import urllib.parse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

SF_DEST_SLUGS = {
    "ATH": "flights-to-athens",
    "FCO": "flights-to-rome",
    "LON": "flights-to-london",
    "LTN": "flights-to-london",
    "LHR": "flights-to-london",
    "BUD": "flights-to-budapest",
    "PRG": "flights-to-prague",
    "LCA": "flights-to-larnaca",
    "PFO": "flights-to-paphos",
    "BCN": "flights-to-barcelona",
    "MAD": "flights-to-madrid",
    "PAR": "flights-to-paris",
    "CDG": "flights-to-paris",
    "VIE": "flights-to-vienna",
    "BER": "flights-to-berlin",
    "AMS": "flights-to-amsterdam",
    "DXB": "flights-to-dubai",
    "WAW": "flights-to-warsaw",
    "MXP": "flights-to-milan",
    "BGY": "flights-to-milan",
    "SOF": "flights-to-sofia",
    "TBS": "flights-to-tbilisi",
    "BUS": "flights-to-batumi",
    "RHO": "flights-to-rhodes",
    "HER": "flights-to-heraklion"
}

AIRLINE_CODES = {
    "GQ": "SKY express",
    "W6": "Wizz Air",
    "W4": "Wizz Air Malta",
    "LY": "El Al",
    "IZ": "Arkia",
    "6H": "Israir",
    "A3": "Aegean Airlines",
    "BZ": "Blue Bird Airways",
    "FR": "Ryanair",
    "PC": "Pegasus Airlines",
    "FZ": "flydubai"
}

async def crawl_secretflights(dest_code: str, currency: str = "ILS"):
    slug = SF_DEST_SLUGS.get(dest_code.upper(), f"flights-to-{dest_code.lower()}")
    url = f"https://secretflights.co.il/{slug}/"
    usd_rate = 3.65  # Approximate USD to ILS conversion

    offers = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        print(f"[SecretFlights] Navigating to {url}...")
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            redirects = soup.find_all("a", href=lambda h: h and "fly.secretflights.co.il/redirect" in h)
            print(f"[SecretFlights] Found {len(redirects)} flight redirect offers!")

            seen_keys = set()
            for a in redirects:
                parsed = urllib.parse.urlparse(a["href"])
                qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
                
                raw_price = float(qs.get("price_premium") or qs.get("price") or 0)
                if not raw_price:
                    continue

                price_ils = round(raw_price * usd_rate) if currency.upper() == "ILS" else round(raw_price)
                airline_code = qs.get("deal_airline", "")
                airline_name = AIRLINE_CODES.get(airline_code, f"חברת תעופה {airline_code}")
                out_date = qs.get("out_date", "")
                in_date = qs.get("in_date", "")
                times = qs.get("flight_times", "").split("|")

                dedup_key = f"{airline_code}_{out_date}_{in_date}_{price_ils}"
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                out_dep = times[0] if len(times) > 0 else "08:00"
                out_arr = times[1] if len(times) > 1 else "10:15"
                ret_dep = times[2] if len(times) > 2 else "18:00"
                ret_arr = times[3] if len(times) > 3 else "20:15"

                offer = {
                    "engine": "טיסות סודיות (Playwright)",
                    "engine_icon": "🕵️",
                    "engine_badge": "טיסות סודיות (נסרק פיזית)",
                    "price": price_ils,
                    "currency": currency.upper(),
                    "primary_airline": airline_name,
                    "is_direct": qs.get("direct") == "true",
                    "stops": 0 if qs.get("direct") == "true" else 1,
                    "booking_link": a["href"],
                    "baggage": {
                        "personal_item": 1,
                        "cabin_bag": 1 if airline_code in ["A3", "LY"] else 0,
                        "checked_bag": 0,
                        "summary_he": "כולל תיק גב, טרולי בתוספת תשלום"
                    },
                    "outbound": {
                        "origin": qs.get("origin", "TLV"),
                        "destination": dest_code.upper(),
                        "origin_name": "תל אביב (נתב״ג)",
                        "destination_name": dest_code.upper(),
                        "date": out_date,
                        "airline": airline_name,
                        "flight_number": airline_code,
                        "departure_time": out_dep,
                        "arrival_time": out_arr,
                        "duration_text": "שעתיים",
                        "is_direct": qs.get("direct") == "true",
                        "stops": 0
                    },
                    "return": {
                        "origin": dest_code.upper(),
                        "destination": qs.get("origin", "TLV"),
                        "origin_name": dest_code.upper(),
                        "destination_name": "תל אביב (נתב״ג)",
                        "date": in_date,
                        "airline": airline_name,
                        "flight_number": airline_code,
                        "departure_time": ret_dep,
                        "arrival_time": ret_arr,
                        "duration_text": "שעתיים",
                        "is_direct": qs.get("direct") == "true",
                        "stops": 0
                    } if in_date else None
                }
                offers.append(offer)

        except Exception as e:
            print(f"[SecretFlights error]: {e}")
        finally:
            await browser.close()

    return offers

async def main():
    offers = await crawl_secretflights("ATH", "ILS")
    print(f"Crawl finished! Total offers: {len(offers)}")
    for o in offers[:3]:
        print(f"Offer: {o['primary_airline']} -> {o['price']} {o['currency']}, Out: {o['outbound']['date']} {o['outbound']['departure_time']}, Ret: {o['return']['date'] if o['return'] else 'None'}")
        print(f"Link: {o['booking_link'][:80]}...")

asyncio.run(main())
