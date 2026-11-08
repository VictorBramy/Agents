from bs4 import BeautifulSoup
import json

with open("secretflights_athens.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

flight_items = soup.find_all(lambda tag: tag.get("class") and any("flight" in c for c in tag.get("class")))
print("Tags with 'flight' in class:", len(flight_items))

deals = []
for tag in flight_items[:10]:
    classes = tag.get("class")
    text = tag.get_text().strip().replace("\n", " ")
    link = tag.find("a", href=True)
    deals.append({
        "tag": tag.name,
        "classes": classes,
        "text": text[:150],
        "link": link["href"] if link else ""
    })

with open("sf_parsed_deals.json", "w", encoding="utf-8") as f:
    json.dump(deals, f, indent=2, ensure_ascii=False)

print("Saved 10 parsed deals to sf_parsed_deals.json")
