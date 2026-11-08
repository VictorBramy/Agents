import re
from typing import Optional, Dict, List, Any

# Common airport dictionary with Hebrew & English mappings
AIRPORTS_DB: List[Dict[str, Any]] = [
    {"code": "TLV", "city_he": "תל אביב", "city_en": "Tel Aviv", "country": "ישראל", "name": "נמל התעופה בן גוריון", "country_en": "Israel"},
    {"code": "ETM", "city_he": "אילת / רמון", "city_en": "Eilat Ramon", "country": "ישראל", "name": "נמל התעופה רמון", "country_en": "Israel"},
    {"code": "ATH", "city_he": "אתונה", "city_en": "Athens", "country": "יוון", "name": "Eleftherios Venizelos", "country_en": "Greece"},
    {"code": "LCA", "city_he": "לרנקה", "city_en": "Larnaca", "country": "קפריסין", "name": "Larnaca International", "country_en": "Cyprus"},
    {"code": "PFO", "city_he": "פאפוס", "city_en": "Paphos", "country": "קפריסין", "name": "Paphos International", "country_en": "Cyprus"},
    {"code": "HER", "city_he": "כרתים (הרקליון)", "city_en": "Crete Heraklion", "country": "יוון", "name": "Heraklion Airport", "country_en": "Greece"},
    {"code": "RHO", "city_he": "רודוס", "city_en": "Rhodes", "country": "יוון", "name": "Diagoras Airport", "country_en": "Greece"},
    {"code": "FCO", "city_he": "רומא", "city_en": "Rome", "country": "איטליה", "name": "Fiumicino Leonardo da Vinci", "country_en": "Italy"},
    {"code": "CIA", "city_he": "רומא צ'אמפינו", "city_en": "Rome Ciampino", "country": "איטליה", "name": "Ciampino Airport", "country_en": "Italy"},
    {"code": "MXP", "city_he": "מילאנו מלפנסה", "city_en": "Milan Malpensa", "country": "איטליה", "name": "Malpensa Airport", "country_en": "Italy"},
    {"code": "BGY", "city_he": "מילאנו ברגמו", "city_en": "Milan Bergamo", "country": "איטליה", "name": "Orio al Serio", "country_en": "Italy"},
    {"code": "VCE", "city_he": "ונציה", "city_en": "Venice", "country": "איטליה", "name": "Marco Polo", "country_en": "Italy"},
    {"code": "PRG", "city_he": "פראג", "city_en": "Prague", "country": "צ'כיה", "name": "Vaclav Havel", "country_en": "Czech Republic"},
    {"code": "BUD", "city_he": "בודפשט", "city_en": "Budapest", "country": "הונגריה", "name": "Ferenc Liszt", "country_en": "Hungary"},
    {"code": "VIE", "city_he": "וינה", "city_en": "Vienna", "country": "אוסטריה", "name": "Vienna International", "country_en": "Austria"},
    {"code": "BER", "city_he": "ברלין", "city_en": "Berlin", "country": "גרמניה", "name": "Berlin Brandenburg", "country_en": "Germany"},
    {"code": "MUC", "city_he": "מינכן", "city_en": "Munich", "country": "גרמניה", "name": "Munich Airport", "country_en": "Germany"},
    {"code": "FRA", "city_he": "פרנקפורט", "city_en": "Frankfurt", "country": "גרמניה", "name": "Frankfurt Airport", "country_en": "Germany"},
    {"code": "PAR", "city_he": "פריז (כל הנמלים)", "city_en": "Paris All", "country": "צרפת", "name": "Paris Airports", "country_en": "France"},
    {"code": "CDG", "city_he": "פריז שארל דה גול", "city_en": "Paris CDG", "country": "צרפת", "name": "Charles de Gaulle", "country_en": "France"},
    {"code": "ORY", "city_he": "פריז אורלי", "city_en": "Paris Orly", "country": "צרפת", "name": "Paris Orly", "country_en": "France"},
    {"code": "LON", "city_he": "לונדון (כל הנמלים)", "city_en": "London All", "country": "בריטניה", "name": "London Airports", "country_en": "UK"},
    {"code": "LHR", "city_he": "לונדון הית'רו", "city_en": "London Heathrow", "country": "בריטניה", "name": "Heathrow Airport", "country_en": "UK"},
    {"code": "LGW", "city_he": "לונדון גטוויק", "city_en": "London Gatwick", "country": "בריטניה", "name": "Gatwick Airport", "country_en": "UK"},
    {"code": "LTN", "city_he": "לונדון לוטון", "city_en": "London Luton", "country": "בריטניה", "name": "Luton Airport", "country_en": "UK"},
    {"code": "STN", "city_he": "לונדון סטנסטד", "city_en": "London Stansted", "country": "בריטניה", "name": "Stansted Airport", "country_en": "UK"},
    {"code": "BCN", "city_he": "ברצלונה", "city_en": "Barcelona", "country": "ספרד", "name": "El Prat", "country_en": "Spain"},
    {"code": "MAD", "city_he": "מדריד", "city_en": "Madrid", "country": "ספרד", "name": "Barajas", "country_en": "Spain"},
    {"code": "AMS", "city_he": "אמסטרדם", "city_en": "Amsterdam", "country": "הולנד", "name": "Schiphol", "country_en": "Netherlands"},
    {"code": "WAW", "city_he": "ורשה שופן", "city_en": "Warsaw Chopin", "country": "פולין", "name": "Warsaw Chopin", "country_en": "Poland"},
    {"code": "KRK", "city_he": "קרקוב", "city_en": "Krakow", "country": "פולין", "name": "John Paul II", "country_en": "Poland"},
    {"code": "OTP", "city_he": "בוקרשט", "city_en": "Bucharest", "country": "רומניה", "name": "Henri Coanda", "country_en": "Romania"},
    {"code": "SOF", "city_he": "סופיה", "city_en": "Sofia", "country": "בולגריה", "name": "Sofia Airport", "country_en": "Bulgaria"},
    {"code": "TBS", "city_he": "טביליסי", "city_en": "Tbilisi", "country": "גיאורגיה", "name": "Shota Rustaveli", "country_en": "Georgia"},
    {"code": "BUS", "city_he": "בטומי", "city_en": "Batumi", "country": "גיאורגיה", "name": "Batumi International", "country_en": "Georgia"},
    {"code": "GYD", "city_he": "באקו", "city_en": "Baku", "country": "אזרבייג'ן", "name": "Heydar Aliyev", "country_en": "Azerbaijan"},
    {"code": "DXB", "city_he": "דובאי", "city_en": "Dubai", "country": "איחוד האמירויות", "name": "Dubai International", "country_en": "UAE"},
    {"code": "AUH", "city_he": "אבו דאבי", "city_en": "Abu Dhabi", "country": "איחוד האמירויות", "name": "Zayed International", "country_en": "UAE"},
    {"code": "LIS", "city_he": "ליסבון", "city_en": "Lisbon", "country": "פורטוגל", "name": "Humberto Delgado", "country_en": "Portugal"},
    {"code": "NYC", "city_he": "ניו יורק (כל הנמלים)", "city_en": "New York All", "country": "ארה\"ב", "name": "New York Airports", "country_en": "USA"},
    {"code": "JFK", "city_he": "ניו יורק JFK", "city_en": "New York JFK", "country": "ארה\"ב", "name": "John F. Kennedy", "country_en": "USA"},
    {"code": "EWR", "city_he": "ניו יורק ניוארק", "city_en": "Newark", "country": "ארה\"ב", "name": "Newark Liberty", "country_en": "USA"},
    {"code": "MIA", "city_he": "מיאמי", "city_en": "Miami", "country": "ארה\"ב", "name": "Miami International", "country_en": "USA"},
    {"code": "LAX", "city_he": "לוס אנג'לס", "city_en": "Los Angeles", "country": "ארה\"ב", "name": "Los Angeles International", "country_en": "USA"},
    {"code": "BKK", "city_he": "בנגקוק", "city_en": "Bangkok", "country": "תאילנד", "name": "Suvarnabhumi", "country_en": "Thailand"},
    {"code": "HKT", "city_he": "פוקט", "city_en": "Phuket", "country": "תאילנד", "name": "Phuket International", "country_en": "Thailand"},
    {"code": "TYO", "city_he": "טוקיו (כל הנמלים)", "city_en": "Tokyo All", "country": "יפן", "name": "Tokyo Airports", "country_en": "Japan"},
    {"code": "NRT", "city_he": "טוקיו נאריטה", "city_en": "Tokyo Narita", "country": "יפן", "name": "Narita Airport", "country_en": "Japan"},
    {"code": "HND", "city_he": "טוקיו האנדה", "city_en": "Tokyo Haneda", "country": "יפן", "name": "Haneda Airport", "country_en": "Japan"},
    {"code": "ZRH", "city_he": "ציריך", "city_en": "Zurich", "country": "שוויץ", "name": "Zurich Airport", "country_en": "Switzerland"},
    {"code": "GVA", "city_he": "ז'נבה", "city_en": "Geneva", "country": "שוויץ", "name": "Geneva Airport", "country_en": "Switzerland"}
]

# Quick lookup indexes
CODE_TO_AIRPORT = {a["code"]: a for a in AIRPORTS_DB}

def search_airports(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Returns matching airports by code, city name (Hebrew/English), or country."""
    q = query.strip().lower()
    if not q:
        return AIRPORTS_DB[:limit]
    
    matches = []
    # 1. Exact code match
    for a in AIRPORTS_DB:
        if a["code"].lower() == q:
            matches.append(a)
            break
            
    # 2. Substring in code, city or country
    for a in AIRPORTS_DB:
        if a in matches:
            continue
        if (q in a["code"].lower() or 
            q in a["city_he"].lower() or 
            q in a["city_en"].lower() or 
            q in a["country"].lower() or 
            q in a["country_en"].lower()):
            matches.append(a)
            if len(matches) >= limit:
                break
                
    return matches

def resolve_airport_code(text: str) -> Optional[str]:
    """Resolves arbitrary user text into a 3-letter IATA airport code."""
    if not text:
        return None
    cleaned = text.strip()
    
    # 3-letter uppercase code
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned.upper()
        
    results = search_airports(cleaned, limit=1)
    if results:
        return results[0]["code"]

    # Bidirectional text search: check if any known city or code is inside the user's sentence
    text_lower = text.lower()
    # Primary city shortcuts
    city_priority_map = {
        "רומא": "FCO", "rome": "FCO",
        "פריז": "CDG", "paris": "CDG",
        "לונדון": "LON", "london": "LON",
        "מילאנו": "MXP", "milan": "MXP",
        "ניו יורק": "NYC", "new york": "NYC",
        "טוקיו": "TYO", "tokyo": "TYO"
    }
    for city_key, main_code in city_priority_map.items():
        if city_key in text_lower:
            return main_code

    # Priority order: longer city names first to avoid false short substring matches
    sorted_airports = sorted(AIRPORTS_DB, key=lambda a: len(a["city_he"]), reverse=True)
    for a in sorted_airports:
        # Ignore Tel Aviv/Israel as destination if departing from TLV
        if a["code"] in ["TLV", "ETM"] and ("טיסה ל" in text_lower or "חזור ל" in text_lower):
            continue
        primary_he = a["city_he"].split()[0].lower()
        primary_en = a["city_en"].split()[0].lower()
        if primary_he in text_lower or primary_en in text_lower or f" {a['code'].lower()} " in f" {text_lower} ":
            return a["code"]
        
    return None

def get_airport_display_name(code: str) -> str:
    """Returns friendly display name for an airport code."""
    if code in CODE_TO_AIRPORT:
        a = CODE_TO_AIRPORT[code]
        return f"{a['city_he']} ({code})"
    return code
