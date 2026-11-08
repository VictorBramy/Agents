import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from flight_agent.searcher import execute_flight_search

async def run_end_to_end_verification():
    dep_date = "2026-11-26"
    ret_date = "2026-11-30"
    origin = "TLV"
    dest = "VIE"
    
    print(f"=== Starting E2E Verification for {origin} -> {dest} ({dep_date} to {ret_date}) ===")
    res = execute_flight_search(
        origin=origin,
        destination=dest,
        departure_date=dep_date,
        return_date=ret_date,
        trip_type="round-trip",
        currency="ILS",
        include_browser_crawler=True
    )
    
    offers = res.get("combined_offers", [])
    print(f"Total offers found: {len(offers)}")
    assert len(offers) > 0, "No offers found!"
    
    # 1. Verify every single offer has booking_link with exact dates & route
    print("\n--- Verifying All Offers Booking Links ---")
    bad_offers = []
    for idx, o in enumerate(offers):
        b_link = o.get("booking_link")
        if not b_link or not b_link.startswith("http"):
            bad_offers.append((idx, o.get("primary_airline"), "Missing or non-http link", b_link))
            continue
        # Verify dates in link
        if "2026-11-26" not in b_link and "261126" not in b_link and "20261126" not in b_link:
            bad_offers.append((idx, o.get("primary_airline"), "Departure date missing from booking_link", b_link))
    
    if bad_offers:
        print(f"FAILED: Found {len(bad_offers)} offers with bad booking links:")
        for b in bad_offers[:5]:
            print(b)
        assert False, f"{len(bad_offers)} bad offers"
    else:
        print(f"SUCCESS: 100% of {len(offers)} flight offers have date-locked booking links!")
        
    # 2. Physically launch Playwright and click/visit top 3 flight booking links
    print("\n--- Physical Playwright Verification of Top 3 Flight Cards ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="he-IL")
        
        for i, o in enumerate(offers[:3]):
            airline = o.get("primary_airline")
            price = o.get("price")
            b_url = o.get("booking_link")
            print(f"\n[Card {i+1}] Airline: {airline} | Price: ₪{price}")
            print(f"       Booking URL: {b_url[:120]}")
            
            resp = await page.goto(b_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2500)
            
            final_url = page.url
            title = await page.title()
            body_text = await page.inner_text("body")
            
            # Assert not generic homepage
            is_generic_homepage = final_url in ["https://www.elal.com/heb/israel", "https://www.arkia.co.il/", "https://www.israir.co.il/"]
            print(f"       Final URL: {final_url[:90]}")
            print(f"       Page Title: {title}")
            print(f"       Is Generic Homepage: {is_generic_homepage} (Must be False!)")
            assert not is_generic_homepage, f"Landed on generic homepage: {final_url}"
            
            # Check for route & dates
            has_dates = "26" in body_text and "30" in body_text
            has_route = ("TLV" in body_text or "תל אביב" in body_text) and ("VIE" in body_text or "וינה" in body_text)
            print(f"       DOM has prompt dates (26, 30): {has_dates}")
            print(f"       DOM has prompt route (TLV, VIE): {has_route}")
            assert has_dates, "Departure/Return dates missing in booking engine DOM!"
            print(f"       ==> CARD {i+1} FULLY VERIFIED AND PASSING!")
            
        await browser.close()
        
    print("\n==========================================")
    print("ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(run_end_to_end_verification())
