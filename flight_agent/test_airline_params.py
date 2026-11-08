import urllib.parse
from playwright.sync_api import sync_playwright

def test_airline_deep_links():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        page = b.new_page(locale="he-IL")
        
        # 1. El Al: Check how El Al search URLs work
        # Try typical Amadeus / Sabre / custom El Al formats
        # E.g. https://flights.elal.com or https://www.elal.com/heb/israel
        print("Testing El Al...")
        page.goto("https://www.elal.com/heb/israel", timeout=15000)
        page.wait_for_timeout(2000)
        
        # 2. Check Israir
        print("Testing Israir...")
        page.goto("https://www.israir.co.il", timeout=15000)
        page.wait_for_timeout(2000)
        
        # 3. Check Arkia
        print("Testing Arkia...")
        page.goto("https://www.arkia.co.il", timeout=15000)
        page.wait_for_timeout(2000)
        
        b.close()

if __name__ == "__main__":
    test_airline_deep_links()
