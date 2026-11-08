from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    page = b.new_page(locale="he-IL")
    
    # 1. Test Blue Bird filtered URL
    bb_url = "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjAyAkJaagUSA1RMVnIFEgNBVEgaHhIKMjAyNi0xMS0yNzICQlpqBRIDQVRIcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"
    print("Testing Blue Bird filtered Google Flights URL...")
    page.goto(bb_url, timeout=25000)
    page.wait_for_timeout(4000)
    print("Blue Bird Page Title:", page.title())
    text_bb = page.inner_text("body")
    print("Has 'לא נמצאו טיסות'?", "לא נמצאו טיסות" in text_bb or "אין טיסות" in text_bb)
    print("Body snippet:", text_bb[:400].replace("\n", " "))
    page.screenshot(path="data/screenshots/test_bb_gf.png")
    
    # 2. Test El Al filtered URL
    elal_url = "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjAyAkxZagUSA1RMVnIFEgNBVEgaHhIKMjAyNi0xMS0yNzICTFlqBRIDQVRIcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"
    print("\nTesting El Al filtered Google Flights URL...")
    page.goto(elal_url, timeout=25000)
    page.wait_for_timeout(4000)
    print("El Al Page Title:", page.title())
    text_elal = page.inner_text("body")
    print("Has 'לא נמצאו טיסות'?", "לא נמצאו טיסות" in text_elal or "אין טיסות" in text_elal)
    print("Body snippet:", text_elal[:400].replace("\n", " "))
    page.screenshot(path="data/screenshots/test_elal_gf.png")

    # 3. Test Arkia filtered URL
    arkia_url = "https://www.google.com/travel/flights/search?tfs=Gh4SCjIwMjYtMTEtMjAyAklaagUSA1RMVnIFEgNBVEgaHhIKMjAyNi0xMS0yNzICSVpqBRIDQVRIcgUSA1RMVkIBAUgBmAEB&hl=iw&curr=ILS"
    print("\nTesting Arkia filtered Google Flights URL...")
    page.goto(arkia_url, timeout=25000)
    page.wait_for_timeout(4000)
    print("Arkia Page Title:", page.title())
    text_arkia = page.inner_text("body")
    print("Has 'לא נמצאו טיסות'?", "לא נמצאו טיסות" in text_arkia or "אין טיסות" in text_arkia)
    print("Body snippet:", text_arkia[:400].replace("\n", " "))
    page.screenshot(path="data/screenshots/test_arkia_gf.png")

    b.close()
