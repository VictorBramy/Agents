"""
Autonomous Price Drop Tracker Daemon for Smart Flight Hunter AI.
Periodically scans active tracked flight routes, compares prices in real-time,
detects price drops, and alerts users via in-app notifications and WhatsApp format.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from flight_agent.db import (
    get_connection,
    get_tracked_flights,
    record_price_check,
    get_price_alerts_summary
)
from flight_agent.searcher import execute_flight_search
from flight_agent.airports import get_airport_display_name

logger = logging.getLogger("PriceTrackerDaemon")


def check_single_tracked_flight(track_id: int) -> Dict[str, Any]:
    """
    Executes a fresh live search for a specific tracked flight,
    updates price history, and flags price drops.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tracked_flights WHERE id = ? AND is_active = 1", (track_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": f"Tracked flight #{track_id} not found or inactive"}

    item = dict(row)
    orig = item["origin"]
    dest = item["destination"]
    dep = item["departure_date"]
    ret = item.get("return_date")
    curr = item.get("currency", "ILS")
    direct = bool(item.get("direct_only", 0))
    pax = int(item.get("passengers", 1) or 1)
    prev_price = float(item.get("current_price") or item.get("initial_price") or 0.0)

    try:
        res = execute_flight_search(
            origin=orig,
            destination=dest,
            departure_date=dep,
            return_date=ret,
            trip_type=item.get("trip_type", "round-trip"),
            currency=curr,
            max_stops=0 if direct else None,
            passengers=pax,
            include_browser_crawler=True
        )

        if not res.get("success") or not res.get("lowest_price"):
            return {
                "success": False,
                "track_id": track_id,
                "error": "No flights found during live recheck",
                "current_price": prev_price
            }

        new_lowest = float(res["lowest_price"])
        best_airline = res.get("combined_offers", [{}])[0].get("primary_airline") if res.get("combined_offers") else res.get("best_deal_engine")
        booking_link = res.get("combined_offers", [{}])[0].get("booking_link") or res.get("booking_link")

        # Record check in database
        check_res = record_price_check(
            track_id=track_id,
            new_price=new_lowest,
            new_airline=best_airline,
            booking_link=booking_link
        )

        orig_name = get_airport_display_name(orig)
        dest_name = get_airport_display_name(dest)
        dates_desc = f"{dep} עד {ret}" if ret else dep

        # WhatsApp alert message format
        whatsapp_msg = (
            f"🔥 *התראת ירידת מחיר מסוכן הטיסות!* 🔥\n\n"
            f"✈️ מסלול: *{orig_name} ({orig}) ⇄ {dest_name} ({dest})*\n"
            f"📅 תאריכים: {dates_desc}\n"
            f"📉 מחיר קודם: {prev_price} {curr}\n"
            f"🎉 *מחיר חדש עכשיו: {new_lowest} {curr}* (חיסכון של {check_res.get('price_drop_amount')} {curr}!)\n"
            f"🏢 חברת תעופה: {best_airline}\n\n"
            f"👉 להזמנה מיידית לפני שיעלה:\n{booking_link}"
        ) if check_res.get("is_alert") else None

        check_res["whatsapp_alert_text"] = whatsapp_msg
        check_res["route_display"] = f"{orig} -> {dest}"
        check_res["dates_display"] = dates_desc
        return check_res

    except Exception as e:
        logger.error(f"Error checking tracked flight #{track_id}: {e}")
        return {"success": False, "track_id": track_id, "error": str(e)}


def scan_all_active_tracked_flights() -> Dict[str, Any]:
    """
    Scans all active tracked flights across the system,
    identifies price drops, and aggregates telemetry.
    """
    t0 = time.time()
    active_flights = get_tracked_flights()
    results = []
    alerts_triggered = []

    for f in active_flights:
        res = check_single_tracked_flight(f["id"])
        results.append(res)
        if res.get("is_alert"):
            alerts_triggered.append(res)

    duration = round(time.time() - t0, 2)
    return {
        "success": True,
        "total_scanned": len(active_flights),
        "alerts_triggered_count": len(alerts_triggered),
        "alerts_triggered": alerts_triggered,
        "scan_duration_seconds": duration,
        "summary": get_price_alerts_summary()
    }


class PriceTrackerDaemon:
    """Background daemon for automated periodic price drop checking."""
    def __init__(self, interval_seconds: int = 1800):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None
        self.last_run_time = None
        self.last_results = None

    def start(self):
        if not self._running:
            self._running = True
            logger.info(f"PriceTrackerDaemon started with interval={self.interval_seconds}s")

    def stop(self):
        self._running = False
        logger.info("PriceTrackerDaemon stopped.")

    async def run_single_cycle(self) -> Dict[str, Any]:
        """Runs a single background scan cycle asynchronously."""
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, scan_all_active_tracked_flights)
        self.last_run_time = datetime.now().isoformat()
        self.last_results = res
        return res

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "interval_seconds": self.interval_seconds,
            "last_run_time": self.last_run_time,
            "last_scan_results": self.last_results,
            "alerts_summary": get_price_alerts_summary()
        }


# Singleton daemon instance
price_tracker_instance = PriceTrackerDaemon(interval_seconds=3600)
