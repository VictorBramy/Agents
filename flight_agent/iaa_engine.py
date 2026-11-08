import urllib.request
import urllib.parse
import json
from typing import List, Dict, Any, Optional

IAA_DATASTORE_URL = "https://data.gov.il/api/3/action/datastore_search"
IAA_RESOURCE_ID = "e83f763b-b7d7-479e-b172-ae981ddc6de5"

def get_iaa_flights_for_destination(destination_iata: str, limit: int = 50) -> Dict[str, Any]:
    """
    Queries Israel Airports Authority (רשות שדות התעופה - נתב״ג) live open data
    for direct flights between Ben Gurion Airport (TLV) and the destination.
    """
    dest_clean = destination_iata.strip().upper()
    try:
        params = {
            "resource_id": IAA_RESOURCE_ID,
            "q": dest_clean,
            "limit": limit
        }
        url = f"{IAA_DATASTORE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "FlightHunterAI/1.0"})
        
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            
        if not data.get("success"):
            return {"success": False, "destination": dest_clean, "airlines": [], "flights": []}
            
        records = data.get("result", {}).get("records", [])
        
        # Filter records where CHLOC1 matches our destination
        matched = []
        airlines_map = {}
        
        for r in records:
            loc = r.get("CHLOC1", "").strip().upper()
            if loc == dest_clean or dest_clean in r.get("CHLOC1D", "").upper():
                carrier = r.get("CHOPERD", "").strip()
                code = r.get("CHOPER", "").strip()
                fltn = f"{code} {r.get('CHFLTN', '').strip()}"
                term = r.get("CHTERM", 3)
                direction = "המראה" if r.get("CHAORD") == "D" else "נחיתה"
                sched_time = r.get("CHSTOL", "")
                status = r.get("CHRMINE", "").strip()
                
                flight_info = {
                    "carrier": carrier,
                    "code": code,
                    "flight_number": fltn,
                    "terminal": term,
                    "direction": direction,
                    "scheduled_time": sched_time,
                    "status": status
                }
                matched.append(flight_info)
                
                if carrier not in airlines_map:
                    airlines_map[carrier] = {
                        "name": carrier,
                        "code": code,
                        "flights": set(),
                        "terminals": set(),
                    }
                airlines_map[carrier]["flights"].add(fltn)
                airlines_map[carrier]["terminals"].add(f"טרמינל {term}")

        # Format airlines list
        active_airlines = []
        for a in airlines_map.values():
            active_airlines.append({
                "name": a["name"],
                "code": a["code"],
                "flights": list(a["flights"]),
                "terminals": list(a["terminals"]),
            })
            
        return {
            "success": True,
            "destination": dest_clean,
            "total_iaa_records": len(matched),
            "airlines_count": len(active_airlines),
            "active_airlines": active_airlines,
            "recent_flights": matched[:10]
        }
    except Exception as e:
        print(f"[iaa_engine error for {dest_clean}]: {e}")
        return {
            "success": False,
            "destination": dest_clean,
            "error": str(e),
            "airlines_count": 0,
            "active_airlines": []
        }
