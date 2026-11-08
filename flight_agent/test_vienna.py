import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from flight_agent.searcher import execute_flight_search

res = execute_flight_search('TLV', 'VIE', '2026-11-26', '2026-11-30', trip_type='round-trip', currency='ILS', include_browser_crawler=True)
print('Success:', res.get('success'))
print('Total combined offers:', len(res.get('combined_offers', [])))
print('Google URL in res:', res.get('booking_link'))
for i, o in enumerate(res.get('combined_offers', [])[:8]):
    print(f"[{i}] engine={o.get('engine')} airline={o.get('primary_airline')} price={o.get('price')}")
    print(f"     booking_link={o.get('booking_link')}")
    portal = o.get('airline_portal')
    if portal:
        print(f"     official_site={portal.get('official_site')}")
