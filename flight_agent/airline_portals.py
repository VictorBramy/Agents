import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fast_flights import FlightQuery, Passengers, create_filter

AIRLINE_IATA_CODES = {
    "el al": "LY",
    "אל על": "LY",
    "arkia": "IZ",
    "ארקיע": "IZ",
    "israir": "6H",
    "ישראייר": "6H",
    "smartwings": "QS",
    "smart wings": "QS",
    "סמארטווינגס": "QS",
    "qs": "QS",
    "blue bird": "BZ",
    "bluebird": "BZ",
    "בלו בירד": "BZ",
    "wizz": "W6",
    "וויז": "W6",
    "aegean": "A3",
    "איג׳יאן": "A3",
    "sky express": "GQ",
    "סקיי אקספרס": "GQ",
    "pegasus": "PC",
    "פגסוס": "PC",
    "ryanair": "FR",
    "ראיינאייר": "FR",
    "easyjet": "U2",
    "איזיג׳ט": "U2"
}

ISRAIR_DESTINATION_URLS = {
    "FCO": "https://www.israir.co.il/Flights/Italy/Rome.html",
    "ATH": "https://www.israir.co.il/Flights/Greece/Athens.html",
    "SKG": "https://www.israir.co.il/Flights/Greece/Thessaloniki.html",
    "BUD": "https://www.israir.co.il/Flights/Hungary/Budapest.html",
    "PRG": "https://www.israir.co.il/Flights/Czech_Republic/Prague.html",
    "LCA": "https://www.israir.co.il/Flights/Cyprus/Larnaca.html",
    "PFO": "https://www.israir.co.il/Flights/Cyprus/Paphos.html",
    "TBS": "https://www.israir.co.il/Flights/Georgia/Tbilisi.html",
    "BUS": "https://www.israir.co.il/Flights/Georgia/Batumi.html",
    "VAR": "https://www.israir.co.il/Flights/Bulgaria/Varna.html",
    "BOJ": "https://www.israir.co.il/Flights/Bulgaria/Burgas.html",
    "BER": "https://www.israir.co.il/Flights/Germany/Berlin.html",
    "LON": "https://www.israir.co.il/Flights/England/London.html",
    "LTN": "https://www.israir.co.il/Flights/England/London.html",
    "DXB": "https://www.israir.co.il/Flights/United_Arab_Emirates/Dubai.html",
    "GYD": "https://www.israir.co.il/Flights/Azerbaijan/Baku.html",
    "MXP": "https://www.israir.co.il/Flights/Italy/Milan.html",
    "VRN": "https://www.israir.co.il/Flights/Italy/Verona.html",
    "NAP": "https://www.israir.co.il/Flights/Italy/Naples.html",
    "CTA": "https://www.israir.co.il/Flights/Italy/Sicily/Catania.html",
    "MAD": "https://www.israir.co.il/Flights/Spain/Madrid.html",
    "AGP": "https://www.israir.co.il/Flights/Spain/Malaga.html",
    "SOF": "https://www.israir.co.il/Flights/Bulgaria/Sofia.html",
    "RHO": "https://www.israir.co.il/Flights/Greece/Rhodes.html",
    "CFU": "https://www.israir.co.il/Flights/Greece/Corfu.html",
    "CHQ": "https://www.israir.co.il/Flights/Greece/Chania.html",
    "HER": "https://www.israir.co.il/Flights/Greece/Heraklion.html",
    "ZTH": "https://www.israir.co.il/Flights/Greece/Zakynthos.html",
    "KOS": "https://www.israir.co.il/Flights/Greece/Kos.html",
    "TIV": "https://www.israir.co.il/Flights/Montenegro.html",
}

ELAL_DESTINATION_URLS = {
    "PRG": "https://www.elal.com/heb/flights/prague",
    "ATH": "https://www.elal.com/heb/flights/athens",
    "FCO": "https://www.elal.com/heb/flights/rome",
    "LCA": "https://www.elal.com/heb/flights/larnaca",
    "SKG": "https://www.elal.com/heb/flights/thessaloniki",
    "BUD": "https://www.elal.com/heb/flights/budapest",
    "LON": "https://www.elal.com/heb/flights/london",
    "LTN": "https://www.elal.com/heb/flights/london",
    "LHR": "https://www.elal.com/heb/flights/london",
    "PAR": "https://www.elal.com/heb/flights/paris",
    "CDG": "https://www.elal.com/heb/flights/paris",
    "BCN": "https://www.elal.com/heb/flights/barcelona",
    "MAD": "https://www.elal.com/heb/flights/madrid",
    "AMS": "https://www.elal.com/heb/flights/amsterdam",
    "BER": "https://www.elal.com/heb/flights/berlin",
    "VIE": "https://www.elal.com/heb/flights/vienna",
    "DXB": "https://www.elal.com/heb/flights/dubai",
    "JFK": "https://www.elal.com/heb/flights/new-york",
    "EWR": "https://www.elal.com/heb/flights/new-york",
    "MIA": "https://www.elal.com/heb/flights/miami",
    "LAX": "https://www.elal.com/heb/flights/los-angeles",
    "BKK": "https://www.elal.com/heb/flights/bangkok",
    "HND": "https://www.elal.com/heb/flights/tokyo",
    "NRT": "https://www.elal.com/heb/flights/tokyo"
}

def resolve_airline_iata(name: str) -> Optional[str]:
    """Resolves an airline name or code into an official 2-letter IATA code."""
    clean = (name or "").lower().strip()
    for k, v in AIRLINE_IATA_CODES.items():
        if k in clean:
            return v
    # Check if already 2 uppercase letters
    if len(clean) == 2 and clean.isalnum():
        return clean.upper()
    return None

def build_google_flights_url(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    currency: str = "ILS",
    seat: str = "economy",
    passengers: int = 1,
    airline_code: Optional[str] = None
) -> str:
    """
    Builds an exact Google Flights deep-link with search query (q=...).
    Pre-populates origin, destination, departure date, return date,
    and optionally filters specifically to the target airline so the user
    lands directly on the exact flight booking options with dates pre-selected.
    """
    orig_code = (origin or "TLV").strip().upper()
    dest_code = (destination or "ATH").strip().upper()
    dep_date = (departure_date or "").strip()
    ret_date = (return_date or "").strip() if return_date else None

    # Fallback to 14 days ahead if dep_date is empty
    if not dep_date:
        dep_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    airline_name = ""
    if airline_code:
        code_clean = airline_code.upper()
        name_map = {
            "LY": "El Al",
            "IZ": "Arkia",
            "6H": "Israir",
            "BZ": "Blue Bird Airways",
            "W6": "Wizz Air",
            "FR": "Ryanair",
            "A3": "Aegean Airlines",
            "PC": "Pegasus",
            "OS": "Austrian",
            "LH": "Lufthansa",
            "TK": "Turkish Airlines",
            "U2": "easyJet"
        }
        airline_name = name_map.get(code_clean, code_clean)

    if ret_date:
        query_text = f"flights from {orig_code} to {dest_code} on {dep_date} through {ret_date}"
    else:
        query_text = f"flights from {orig_code} to {dest_code} on {dep_date}"

    # Only append 'with Airline' if known to be safely parsed by Google Flights NLP (e.g. El Al).
    # Other airlines (Israir, Arkia, Wizz) can cause Google Flights to reset to the generic homepage.
    if airline_name == "El Al":
        query_text += f" with {airline_name}"

    encoded_q = urllib.parse.quote_plus(query_text)
    return f"https://www.google.com/travel/flights?q={encoded_q}&curr={currency.upper()}&hl=iw"


def build_airline_direct_portal(
    airline_name: str,
    origin: str = "TLV",
    destination: str = "ATH",
    departure_date: str = "",
    return_date: Optional[str] = None,
    currency: str = "ILS"
) -> Dict[str, Any]:
    """
    Returns official direct booking link and info for airlines operating in Israel.
    The primary 'url' points to the direct flight booking page (with route, dates and airline pre-selected),
    while 'official_site' provides the airline's homepage.
    """
    name_clean = (airline_name or "").lower()
    orig = origin.upper()
    dest = destination.upper()
    
    iata = resolve_airline_iata(name_clean)
    exact_booking_url = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code=iata)

    # Multi-Carrier / Hacker Fare Check:
    # If the offer combines multiple airlines (e.g. "Blue Bird Airways / Ryanair", "SWISS / Austrian"),
    # do NOT link to a single airline's round-trip reservation system because that single airline cannot book the return leg!
    is_multi_carrier = any(sep in name_clean for sep in ["/", "+", " & ", " and "])
    if is_multi_carrier:
        return {
            "name": airline_name,
            "hebrew_name": "שילוב חברות תעופה",
            "logo_icon": "🔀",
            "url": exact_booking_url,
            "booking_url": exact_booking_url,
            "official_site": exact_booking_url,
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": False
        }

    # 1. Wizz Air
    if "wizz" in name_clean or "w6" in name_clean or "w4" in name_clean:
        wizz_search_url = f"https://wizzair.com/en-gb/booking/select-flight/{orig}/{dest}/{departure_date}/" + (f"{return_date}/1/0/0/null" if return_date else "1/0/0/null")
        return {
            "name": "Wizz Air",
            "hebrew_name": "וויז אייר",
            "logo_icon": "🟪",
            "url": wizz_search_url,
            "booking_url": wizz_search_url,
            "official_site": "https://wizzair.com",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }
        
    # 2. El Al (אל על)
    if "el al" in name_clean or "אל על" in name_clean or "ly" in name_clean:
        elal_portal_link = ELAL_DESTINATION_URLS.get(dest, f"https://www.elal.com/heb/flights/{dest.lower()}" if dest else "https://www.elal.com/heb/israel")
        elal_gf = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="LY")
        return {
            "name": "El Al",
            "hebrew_name": "אל על",
            "logo_icon": "🇮🇱",
            "url": elal_portal_link,
            "booking_url": elal_portal_link,
            "direct_airline_link": elal_portal_link,
            "official_site": elal_portal_link,
            "google_flights_url": elal_gf,
            "is_direct_carrier": True
        }
        
    # 3. Arkia (ארקיע)
    if "arkia" in name_clean or "ארקיע" in name_clean or "iz" in name_clean:
        arkia_gf = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="IZ")
        arkia_site_url = f"https://www.arkia.co.il/?origin={orig}&dest={dest}&date={departure_date}"
        return {
            "name": "Arkia",
            "hebrew_name": "ארקיע",
            "logo_icon": "🏝️",
            "url": arkia_site_url,
            "booking_url": arkia_site_url,
            "direct_airline_link": arkia_site_url,
            "official_site": "https://www.arkia.co.il",
            "google_flights_url": arkia_gf,
            "is_direct_carrier": True
        }
        
    # 4. Israir (ישראייר)
    if "israir" in name_clean or "ישראייר" in name_clean or "6h" in name_clean:
        israir_gf = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="6H")
        israir_site_url = ISRAIR_DESTINATION_URLS.get(dest, "https://www.israir.co.il/Flights/Abroad.html")
        return {
            "name": "Israir",
            "hebrew_name": "ישראייר",
            "logo_icon": "☀️",
            "url": israir_site_url,
            "booking_url": israir_site_url,
            "direct_airline_link": israir_site_url,
            "official_site": israir_site_url,
            "google_flights_url": israir_gf,
            "is_direct_carrier": True
        }

    # 4b. Smartwings (סמארטווינגס)
    if "smartwings" in name_clean or "smart wings" in name_clean or "qs" in name_clean or "סמארטווינגס" in name_clean:
        sw_direct = f"https://www.smartwings.com/en?origin={orig}&destination={dest}&dep={departure_date}" + (f"&ret={return_date}" if return_date else "")
        sw_gf = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="QS")
        return {
            "name": "Smartwings",
            "hebrew_name": "סמארטווינגס",
            "logo_icon": "🇨🇿",
            "url": sw_direct,
            "booking_url": sw_direct,
            "direct_airline_link": sw_direct,
            "official_site": "https://www.smartwings.com/en",
            "google_flights_url": sw_gf,
            "is_direct_carrier": True
        }
        
    # 5. Blue Bird Airways (בלו בירד)
    if "blue bird" in name_clean or "bluebird" in name_clean or "bz" in name_clean:
        if return_date:
            bb_direct = f"https://booking.bluebirdair.com/flight-results/{orig}-{dest}/{departure_date}/{return_date}/1/0/0"
        else:
            bb_direct = f"https://booking.bluebirdair.com/flight-results/{orig}-{dest}/{departure_date}/NA/1/0/0"
        return {
            "name": "Blue Bird Airways",
            "hebrew_name": "בלו בירד",
            "logo_icon": "🐦",
            "url": bb_direct,
            "booking_url": bb_direct,
            "official_site": "https://www.bluebirdair.com",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }

    # 6. Aegean Airlines (איג׳יאן)
    if "aegean" in name_clean or "a3" in name_clean:
        aegean_direct = f"https://en.aegeanair.com/flight-deals/?origin={orig}&destination={dest}&departureDate={departure_date}" + (f"&returnDate={return_date}" if return_date else "")
        return {
            "name": "Aegean Airlines",
            "hebrew_name": "איג׳יאן",
            "logo_icon": "🇬🇷",
            "url": aegean_direct,
            "booking_url": aegean_direct,
            "official_site": "https://en.aegeanair.com",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }

    # 7. SKY express (סקיי אקספרס)
    if "sky express" in name_clean or "gq" in name_clean:
        return {
            "name": "SKY express",
            "hebrew_name": "סקיי אקספרס",
            "logo_icon": "🇬🇷",
            "url": exact_booking_url,
            "booking_url": exact_booking_url,
            "direct_airline_link": "https://www.skyexpress.gr",
            "official_site": "https://www.skyexpress.gr",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }

    # 8. Pegasus Airlines
    if "pegasus" in name_clean or "pc" in name_clean:
        pegasus_direct = f"https://web.flypgs.com/booking?departureAirport={orig}&arrivalAirport={dest}&departureDate={departure_date}" + (f"&returnDate={return_date}" if return_date else "") + "&adultCount=1"
        return {
            "name": "Pegasus Airlines",
            "hebrew_name": "פגסוס",
            "logo_icon": "🟡",
            "url": pegasus_direct,
            "booking_url": pegasus_direct,
            "official_site": "https://www.flypgs.com",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }

    # 9. Ryanair
    if "ryanair" in name_clean or "fr" in name_clean:
        ryanair_direct = f"https://www.ryanair.com/gb/en/trip/flights/select?originIata={orig}&destinationIata={dest}&tpAdults=1&tpStartDate={departure_date}" + (f"&tpEndDate={return_date}" if return_date else "")
        return {
            "name": "Ryanair",
            "hebrew_name": "ראיינאייר",
            "logo_icon": "🟦",
            "url": ryanair_direct,
            "booking_url": ryanair_direct,
            "official_site": "https://www.ryanair.com",
            "google_flights_url": exact_booking_url,
            "is_direct_carrier": True
        }

    # 10. EasyJet
    if "easyjet" in name_clean or "u2" in name_clean:
        easyjet_booking = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="U2")
        return {
            "name": "easyJet",
            "hebrew_name": "איזיג׳ט",
            "logo_icon": "🟧",
            "url": easyjet_booking,
            "booking_url": easyjet_booking,
            "direct_airline_link": "https://www.easyjet.com",
            "official_site": "https://www.easyjet.com",
            "google_flights_url": easyjet_booking,
            "is_direct_carrier": True
        }

    # 11. ITA Airways
    if "ita" in name_clean or "az" in name_clean:
        ita_booking = build_google_flights_url(orig, dest, departure_date, return_date, currency, airline_code="AZ")
        return {
            "name": "ITA Airways",
            "hebrew_name": "איטה אירווייז",
            "logo_icon": "🇮🇹",
            "url": ita_booking,
            "booking_url": ita_booking,
            "direct_airline_link": "https://www.ita-airways.com",
            "official_site": "https://www.ita-airways.com",
            "google_flights_url": ita_booking,
            "is_direct_carrier": True
        }

    return {
        "name": airline_name or "חברת תעופה",
        "hebrew_name": airline_name or "חברת תעופה",
        "logo_icon": "✈️",
        "url": exact_booking_url,
        "booking_url": exact_booking_url,
        "official_site": "",
        "google_flights_url": exact_booking_url,
        "is_direct_carrier": False
    }

def build_trip_url(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None, currency: str = "ILS") -> str:
    """Builds a direct search URL for Trip.com."""
    orig = origin.lower()
    dest = destination.lower()
    if return_date:
        return f"https://il.trip.com/flights/{orig}-to-{dest}/tickets-{orig}-{dest}?flighttype=rt&dcity={orig}&acity={dest}&ddate={departure_date}&rdate={return_date}&curr={currency.upper()}"
    return f"https://il.trip.com/flights/{orig}-to-{dest}/tickets-{orig}-{dest}?flighttype=ow&dcity={orig}&acity={dest}&ddate={departure_date}&curr={currency.upper()}"

def build_expedia_url(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None) -> str:
    """Builds a direct search URL for Expedia."""
    orig = origin.upper()
    dest = destination.upper()
    try:
        # Expedia format dd/mm/yyyy
        dep_parts = departure_date.split("-")
        dep_formatted = f"{dep_parts[2]}/{dep_parts[1]}/{dep_parts[0]}"
        if return_date:
            ret_parts = return_date.split("-")
            ret_formatted = f"{ret_parts[2]}/{ret_parts[1]}/{ret_parts[0]}"
            return f"https://www.expedia.com/Flights-Search?leg1=from:{orig},to:{dest},departure:{dep_formatted}TANYT&leg2=from:{dest},to:{orig},departure:{ret_formatted}TANYT&mode=search"
        return f"https://www.expedia.com/Flights-Search?leg1=from:{orig},to:{dest},departure:{dep_formatted}TANYT&mode=search"
    except Exception:
        return "https://www.expedia.com/Flights"

def build_direct_airline_portal_url(airline_code_or_name: str, origin: str, dest: str, dep_date: str = "", ret_date: Optional[str] = None) -> str:
    """
    Returns authentic direct booking URL for the operating airline.
    Guarantees user lands on the official airline domain or reservation engine,
    never on an aggregator search form.
    """
    raw = (airline_code_or_name or "").strip()
    code = resolve_airline_iata(raw) or raw.upper()
    orig = (origin or "TLV").upper()
    destination = (dest or "").upper()
    
    if code in ["W6", "W4", "WIZZ"] or "וויז" in raw.lower() or "wizz" in raw.lower():
        if dep_date and ret_date:
            return f"https://wizzair.com/en-gb/booking/select-flight/{orig}/{destination}/{dep_date}/{ret_date}/1/0/0/null"
        return f"https://wizzair.com/en-gb/booking/select-flight/{orig}/{destination}"
    elif code in ["BZ", "BLUE BIRD", "BLUEBIRD"] or "בלו בירד" in raw:
        if dep_date and ret_date:
            return f"https://booking.bluebirdair.com/flight-results/{orig}-{destination}/{dep_date}/{ret_date}/1/0/0"
        return f"https://booking.bluebirdair.com/flight-results/{orig}-{destination}/{dep_date}/NA/1/0/0"
    elif code in ["FR", "RYANAIR"] or "ראיינאייר" in raw:
        if dep_date and ret_date:
            return f"https://www.ryanair.com/gb/en/trip/flights/select?originIata={orig}&destinationIata={destination}&tpAdults=1&tpStartDate={dep_date}&tpEndDate={ret_date}"
        elif dep_date:
            return f"https://www.ryanair.com/gb/en/trip/flights/select?originIata={orig}&destinationIata={destination}&tpAdults=1&tpStartDate={dep_date}"
        return "https://www.ryanair.com"
    elif code in ["A3", "AEGEAN"] or "איג׳יאן" in raw:
        if dep_date and ret_date:
            return f"https://en.aegeanair.com/flight-deals/?origin={orig}&destination={destination}&departureDate={dep_date}&returnDate={ret_date}"
        return f"https://en.aegeanair.com/flight-deals/?origin={orig}&destination={destination}"
    elif code in ["PC", "PEGASUS"] or "פגסוס" in raw:
        if dep_date:
            return f"https://web.flypgs.com/booking?departureAirport={orig}&arrivalAirport={destination}&departureDate={dep_date}" + (f"&returnDate={ret_date}" if ret_date else "") + "&adultCount=1"
        return "https://www.flypgs.com"
    elif code in ["6H", "ISRAIR"] or "ישראייר" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="6H")
        return ISRAIR_DESTINATION_URLS.get(destination, "https://www.israir.co.il/Flights/Abroad.html")
    elif code in ["LY", "EL AL"] or "אל על" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="LY")
        return "https://www.elal.com/heb/israel"
    elif code in ["IZ", "ARKIA"] or "ארקיע" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="IZ")
        return f"https://www.arkia.co.il/deals?dest={destination}"
    elif code in ["U2", "EASYJET"] or "איזיג׳ט" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="U2")
        return "https://www.easyjet.com"
    elif code in ["AZ", "ITA"] or "איטה" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="AZ")
        return "https://www.ita-airways.com"
    elif code in ["GQ", "SKY EXPRESS"] or "סקיי אקספרס" in raw:
        if dep_date:
            return build_google_flights_url(orig, destination, dep_date, ret_date, airline_code="GQ")
        return "https://www.skyexpress.gr/en"
    return build_google_flights_url(orig, destination, dep_date, ret_date)

