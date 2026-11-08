---
name: flight-hunter
description: Autonomous cheap flight finder agent for any destination worldwide departing from Tel Aviv (TLV) or custom origins. Uses Google Gemini AI and parallel multi-engine extraction (Kiwi.com hacker fares, Google Flights, Skyscanner, Kayak, Momondo) to find the absolute lowest price, luggage rules, best travel dates, and direct booking links.
---

# Flight Hunter AI Skill (Multi-Engine)

This skill provides autonomous cheap flight discovery, price comparison, and smart booking links using Google AI (Gemini) and parallel multi-engine extraction.

## Features
- **Parallel Multi-Engine Search**: Concurrently queries **Kiwi.com** (virtual interlining / hacker fares), **Google Flights**, and **Israel Airports Authority (נתב״ג / רש״ת)** in real-time.
- **Playwright Physical Browser Crawler**: Launches headless Chrome to physically enter Israeli airline portals and deal websites (טיסות סודיות, ישראייר, בלו בירד) and extracts live prices and direct booking links.
- **IAA Live Direct Schedule**: Directly queries official Ben Gurion Airport open data (`data.gov.il`) to show all airlines operating direct flights on that route today with terminals (T1 vs T3) and flight numbers.
- **Official Airline Direct Portals**: Generates 1-click official direct booking links for Israeli & direct low-cost carriers (אל על, ארקיע, ישראייר, Wizz Air, Blue Bird Airways, Aegean, Pegasus) with zero OTA commissions.
- **Cross-Engine Comparison**: Generates 1-click comparison links for **Skyscanner**, **Trip.com**, **Kayak**, **Momondo**, **Expedia**, and **Skiplagged**.
- **Natural Language Parsing**: Accepts Hebrew/English queries (e.g. "טיסות הכי זולות לאתונה בסוף נובמבר הלוך ושוב ישיר").
- **Real-Time Price Discovery**: Direct extraction in ILS (₪) or USD ($) with automatic sorting by lowest price across all engines.
- **AI Flight Advisor**: Google Gemini analyzes baggage policies (cabin bag vs personal item), timing, and crowns the best value deal.
- **Weekend Hunter**: Scans the next 4 weekend getaways across all engines.
- **Web Dashboard**: Interactive visual dashboard at `http://127.0.0.1:8080/flights`.

## Execution
Run the local dashboard:
```bash
python main.py
```
Or directly call the API:
```python
from flight_agent.searcher import execute_flight_search
from flight_agent.ai_advisor import generate_flight_advice

res = execute_flight_search(origin="TLV", destination="ATH", departure_date="2026-11-20", return_date="2026-11-25", trip_type="round-trip", currency="ILS")
advice = generate_flight_advice(res)
```
