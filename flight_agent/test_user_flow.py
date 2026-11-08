from playwright.sync_api import sync_playwright

def inspect_exact_click():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        context = b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        page = context.new_page()
        
        # 1. Open local web app
        print("1. Opening http://127.0.0.1:8080...")
        page.goto("http://127.0.0.1:8080", timeout=15000)
        page.wait_for_timeout(2000)
        page.screenshot(path="data/screenshots/test_homepage.png")
        
        # 2. Trigger AI search with prompt
        print("2. Entering prompt...")
        page.fill("#aiPromptInput", "מצא לי טיסה ישירה לאתונה בסוף נובמבר הלוך ושוב ישיר, תסרוק את כל חברות התעופה בישראל")
        page.click("#btnAiSearch")
        
        print("3. Waiting for results to appear...")
        page.wait_for_selector("#flightsContainer .bg-white", timeout=45000)
        page.wait_for_timeout(3000)
        page.screenshot(path="data/screenshots/test_results.png")
        
        # 4. Check all booking buttons in the DOM
        cards = page.query_selector_all("#flightsContainer > div")
        print(f"Found {len(cards)} cards")
        
        for idx, card in enumerate(cards[:5]):
            airline = card.query_selector(".font-black.text-base")
            airline_name = airline.inner_text() if airline else "Unknown"
            
            # Find all links on this card
            links = card.query_selector_all("a")
            print(f"\n--- Card #{idx+1}: {airline_name} ---")
            for a in links:
                href = a.get_attribute("href")
                text = a.inner_text().strip().replace("\n", " ")
                print(f"  Link text: [{text}] -> href: {href}")
                
        # 5. Let's actually click the FIRST booking button and see where it navigates!
        first_book_btn = cards[0].query_selector("a:has-text('הזמן')")
        if first_book_btn:
            book_href = first_book_btn.get_attribute("href")
            print(f"\nFirst booking button href: {book_href}")
            
            # Open in a new page just like target="_blank"
            new_page = context.new_page()
            print("Opening booking link in new page...")
            try:
                new_page.goto(book_href, timeout=30000)
                new_page.wait_for_timeout(5000)
                print("New page title:", new_page.title())
                print("New page URL:", new_page.url)
                new_page.screenshot(path="data/screenshots/test_booking_landing.png")
            except Exception as e:
                print("Error opening booking link:", e)
            new_page.close()
            
        b.close()

if __name__ == "__main__":
    inspect_exact_click()
