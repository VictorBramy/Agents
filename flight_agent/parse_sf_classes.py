from bs4 import BeautifulSoup
import re
import json

with open("secretflights_athens.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Find elements containing deal links or booking links
links = soup.find_all("a", href=True)
booking_links = []
for a in links:
    href = a["href"]
    if any(k in href for k in ["kiwi", "skyscanner", "kayak", "booking", "whitelabel", "track", "secretflights.co.il/flight"]):
        booking_links.append({"href": href[:100], "text": a.get_text().strip()[:40]})

print("Booking links count:", len(booking_links))
for b in booking_links[:5]:
    print(b)

# Check classes with "deal" or "flight"
classes = set()
for tag in soup.find_all(True):
    for c in tag.get("class", []):
        if any(term in c.lower() for term in ["flight", "deal", "price", "card", "row", "item", "table"]):
            classes.add(c)

print("Relevant classes found:", list(classes)[:20])
