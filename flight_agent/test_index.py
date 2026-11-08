import requests
from bs4 import BeautifulSoup

resp = requests.get("http://127.0.0.1:8080/")
print("HTTP status:", resp.status_code)
soup = BeautifulSoup(resp.text, "html.parser")
print("Title:", soup.title.string if soup.title else "No title")
print("Has flightsContainer?", bool(soup.find(id="flightsContainer")))
print("Has aiPromptInput?", bool(soup.find(id="aiPromptInput")))
print("Active tabs:", [b.get_text().strip() for b in soup.find_all("button") if "tab" in str(b).lower() or "ai" in str(b).lower()][:10])
