from bs4 import BeautifulSoup
import re

with open("flight_agent/sf_page.html", "r", encoding="utf-8") as f:
    pass

# Let's inspect the HTML of the main secret flights destination page
import urllib.request
url = "https://secretflights.co.il/flights-to-thessaloniki/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        
        # Find cards or containers of deals
        print("Page title:", soup.title.string if soup.title else "No title")
        
        # Look for flight deal blocks
        deal_blocks = soup.find_all(class_=lambda c: c and any(k in c for k in ["flight", "deal", "card", "row"]))
        print("Total candidate blocks:", len(deal_blocks))
        
        # Print first 3 flight items
        redirect_links = soup.find_all("a", href=lambda h: h and "fly.secretflights.co.il/redirect" in h)
        for i, a in enumerate(redirect_links[:4]):
            parent = a.find_parent("div")
            print(f"\n--- Deal #{i+1} ---")
            print("Link text:", a.get_text(strip=True))
            print("Link href:", a.get("href"))
            print("Parent text:", parent.get_text(" | ", strip=True) if parent else "None")
except Exception as e:
    print("Error:", e)
