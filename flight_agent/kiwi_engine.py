import requests
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

KIWI_MCP_ENDPOINT = "https://mcp.kiwi.com"

def _format_iso_time(iso_str: Optional[str]) -> str:
    """Converts '2026-11-24T07:10:00' to '07:10'."""
    if not iso_str:
        return "--:--"
    try:
        if "T" in iso_str:
            t_part = iso_str.split("T")[1]
            return ":".join(t_part.split(":")[:2])
        return iso_str
    except Exception:
        return iso_str

def _format_seconds(seconds: Optional[int]) -> str:
    """Converts seconds into 'X שע׳ ו-Y דק׳'."""
    if not seconds:
        return ""
    mins = seconds // 60
    hours = mins // 60
    rem_mins = mins % 60
    if hours > 0 and rem_mins > 0:
        return f"{hours} שע׳ ו-{rem_mins} דק׳"
    elif hours > 0:
        return f"{hours} שעות"
    return f"{rem_mins} דקות"

def _format_baggage_desc(baggage: Dict[str, Any]) -> str:
    parts = []
    if baggage.get("personalItem", 0) > 0:
        parts.append("תיק אישי")
    if baggage.get("cabinBag", 0) > 0:
        parts.append("טרולי לעלייה למטוס")
    if baggage.get("checkedBag", 0) > 0:
        parts.append("מזוודה לבטן המטוס")
    if not parts:
        return "ללא כבודה נוספת"
    return "כולל " + ", ".join(parts)

def search_kiwi_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    trip_type: str = "round-trip",
    currency: str = "ILS",
    passengers: int = 1,
    max_stops: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Queries Kiwi.com's official flight search engine (via Kiwi MCP).
    Returns a list of structured offers sorted by price.
    """
    args: Dict[str, Any] = {
        "flyFrom": origin.upper(),
        "flyTo": destination.upper(),
        "departureDate": departure_date,
        "adults": max(1, passengers),
        "currency": currency.upper(),
        "sort": "price"
    }

    is_round_trip = (trip_type == "round-trip" and bool(return_date))
    if is_round_trip and return_date:
        args["returnDate"] = return_date

    if max_stops is not None:
        args["max_sector_stopovers"] = max_stops

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search-flight",
            "arguments": args
        },
        "id": 100
    }

    try:
        resp = requests.post(
            KIWI_MCP_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if resp.status_code != 200:
            print(f"[Kiwi MCP error status {resp.status_code}]: {resp.text[:200]}")
            return []

        raw_itineraries = []
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                data_obj = json.loads(line[6:])
                content = data_obj.get("result", {}).get("content", [])
                if content:
                    text_json = json.loads(content[0].get("text", "{}"))
                    raw_itineraries = text_json.get("itineraries", [])
                break

        parsed_offers = []
        for it in raw_itineraries:
            try:
                price = float(it.get("price", 0))
                raw_booking = it.get("bookingUrl", "")
                booking_url = raw_booking if (raw_booking and raw_booking.startswith("http")) else (
                    f"https://www.kiwi.com/deep?from={origin}&to={destination}&departure={departure_date}&return={return_date}&currency={currency}"
                    if return_date else
                    f"https://www.kiwi.com/deep?from={origin}&to={destination}&departure={departure_date}&currency={currency}"
                )
                baggage = it.get("baggage", {}) or {}

                # Outbound
                out = it.get("outbound", {}) or {}
                out_segments = out.get("segments", []) or []
                out_carrier = (out_segments[0].get("carrierName") or out_segments[0].get("carrier") or "חברת תעופה") if out_segments else "חברת תעופה"
                out_flight_no = out_segments[0].get("flightNumber", "") if out_segments else ""
                out_stops = out.get("stops", 0)

                # Inbound (return)
                inb = it.get("inbound") or it.get("return")
                inb_carrier = ""
                inb_flight_no = ""
                inb_stops = 0
                if inb:
                    inb_segments = inb.get("segments", []) or []
                    inb_carrier = (inb_segments[0].get("carrierName") or inb_segments[0].get("carrier") or out_carrier) if inb_segments else out_carrier
                    inb_flight_no = inb_segments[0].get("flightNumber", "") if inb_segments else ""
                    inb_stops = inb.get("stops", 0)

                # Primary airline label
                primary_airline = out_carrier
                if inb and inb_carrier and inb_carrier != out_carrier:
                    primary_airline = f"{out_carrier} / {inb_carrier}"

                parsed_offers.append({
                    "engine": "Kiwi.com",
                    "engine_icon": "🥝",
                    "engine_badge": "Kiwi (האקר פייר)",
                    "price": price,
                    "currency": currency.upper(),
                    "primary_airline": primary_airline,
                    "is_direct": (out_stops == 0 and (inb_stops == 0 if inb else True)),
                    "stops": out_stops + inb_stops,
                    "booking_link": booking_url,
                    "baggage": {
                        "personal_item": baggage.get("personalItem", 0),
                        "cabin_bag": baggage.get("cabinBag", 0),
                        "checked_bag": baggage.get("checkedBag", 0),
                        "summary_he": _format_baggage_desc(baggage)
                    },
                    "outbound": {
                        "origin": out.get("from", origin),
                        "destination": out.get("to", destination),
                        "origin_name": out_segments[0].get("fromName", "") if out_segments else origin,
                        "destination_name": out_segments[-1].get("toName", "") if out_segments else destination,
                        "date": departure_date,
                        "airline": out_carrier,
                        "flight_number": out_flight_no,
                        "departure_time": _format_iso_time(out.get("departureTime")),
                        "arrival_time": _format_iso_time(out.get("arrivalTime")),
                        "duration_text": _format_seconds(out.get("durationSeconds")),
                        "is_direct": (out_stops == 0),
                        "stops": out_stops,
                        "segments": out_segments
                    },
                    "return": {
                        "origin": inb.get("from", destination),
                        "destination": inb.get("to", origin),
                        "origin_name": inb_segments[0].get("fromName", "") if inb_segments else destination,
                        "destination_name": inb_segments[-1].get("toName", "") if inb_segments else origin,
                        "date": return_date,
                        "airline": inb_carrier,
                        "flight_number": inb_flight_no,
                        "departure_time": _format_iso_time(inb.get("departureTime")),
                        "arrival_time": _format_iso_time(inb.get("arrivalTime")),
                        "duration_text": _format_seconds(inb.get("durationSeconds")),
                        "is_direct": (inb_stops == 0),
                        "stops": inb_stops,
                        "segments": inb_segments
                    } if (is_round_trip and inb) else None
                })
            except Exception as e:
                print(f"[Error parsing Kiwi itinerary]: {e}")
                continue

        return parsed_offers
    except Exception as e:
        print(f"[search_kiwi_flights exception]: {e}")
        return []
