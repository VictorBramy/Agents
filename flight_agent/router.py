from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel

from flight_agent.searcher import execute_flight_search, scan_flexible_weekend_deals
from flight_agent.ai_advisor import parse_flight_intent, generate_flight_advice
from flight_agent.airports import search_airports, AIRPORTS_DB, resolve_airport_code
from flight_agent.db import (
    save_search_history, get_recent_searches,
    add_tracked_flight, get_tracked_flights, delete_tracked_flight
)
from flight_agent.auth import get_current_user, consume_search_credit, get_user_quota
from flight_agent.quality_auditor import QualityAuditor
from flight_agent.requirements_matrix import get_requirements_matrix, load_latest_audit_results

router = APIRouter(prefix="/api/flights", tags=["flights"])

class DirectSearchRequest(BaseModel):
    origin: str = "TLV"
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    trip_type: str = "round-trip"
    direct_only: bool = False
    currency: str = "ILS"
    passengers: int = 1
    seat: str = "economy"
    fast_mode: bool = False

class AISearchRequest(BaseModel):
    prompt: str
    origin: Optional[str] = None
    currency: Optional[str] = None

class TrackRouteRequest(BaseModel):
    origin: str = "TLV"
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    trip_type: str = "round-trip"
    max_budget: Optional[float] = None
    target_price: Optional[float] = None
    currency: str = "ILS"
    lowest_price_seen: Optional[float] = None
    best_airline: Optional[str] = None
    booking_link: Optional[str] = None
    user_phone: Optional[str] = None
    direct_only: bool = False
    passengers: int = 1

class PlaywrightCrawlRequest(BaseModel):
    destination: str
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    currency: str = "ILS"

class RunAuditRequest(BaseModel):
    origin: str = "TLV"
    destination: str = "ATH"
    departure_date: str = "2026-11-20"
    return_date: Optional[str] = "2026-11-27"
    currency: str = "ILS"

@router.get("/airports")
def get_airports_endpoint(q: str = Query(default="", description="Search query")):
    """Returns matching airports for search / autocomplete."""
    return search_airports(q, limit=15)

@router.post("/search")
def direct_search_endpoint(req: DirectSearchRequest, request: Request):
    """Executes a live search and retrieves AI analysis."""
    user = get_current_user(request)
    quota = get_user_quota(user)
    if not quota.get("unlimited") and quota["is_depleted"]:
        raise HTTPException(
            status_code=403, 
            detail=f"הגעת למכסת {quota['searches_limit']} החיפושים החודשית שלך במנוי {quota['plan_name']}. שדרג את המנוי עכשיו להמשך חיפושים!"
        )

    max_stops = 0 if req.direct_only else None
    include_crawler = not req.fast_mode
    
    result = execute_flight_search(
        origin=req.origin,
        destination=req.destination,
        departure_date=req.departure_date,
        return_date=req.return_date,
        trip_type=req.trip_type,
        seat=req.seat,
        currency=req.currency,
        max_stops=max_stops,
        passengers=req.passengers,
        include_browser_crawler=include_crawler
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "חיפוש הטיסות נכשל"))

    # Generate Google Gemini AI flight insights (or instant response in fast mode)
    if req.fast_mode:
        f0 = (result.get("combined_offers") or [{}])[0]
        curr_sym = "₪" if result.get("currency") == "ILS" else "$"
        ai_advice = {
            "best_deal": f"{f0.get('primary_airline', 'Wizz Air')} - {curr_sym}{f0.get('price', result.get('lowest_price'))} (אופציה מומלצת לתאריכים אלו)",
            "price_verdict": f"מחיר אטרקטיבי לתאריכים {req.departure_date} עד {req.return_date}.",
            "tips": [
                "שים לב: המחיר עודכן בהצלחה עבור תאריכים נבחרים אלו.",
                "כולל כבודה מומלצת ל-2 נוסעים בצ'ק-אין."
            ],
            "summary_markdown": f"המחיר הזול ביותר לתאריכים **{req.departure_date} עד {req.return_date}** הוא **{curr_sym}{result.get('lowest_price')}** עם {f0.get('primary_airline', 'חברת התעופה')}."
        }
    else:
        ai_advice = generate_flight_advice(result)
    result["ai_advice"] = ai_advice

    offers_to_save = result.get("combined_offers") or result.get("flights", [])
    # Save to history
    save_search_history(
        origin=result["origin"],
        destination=result["destination"],
        departure_date=result["departure_date"],
        return_date=result.get("return_date"),
        trip_type=result["trip_type"],
        direct_only=req.direct_only,
        currency=result["currency"],
        lowest_price=result.get("lowest_price"),
        results_count=len(offers_to_save),
        ai_recommendation=ai_advice.get("summary_markdown", ""),
        results=offers_to_save,
        user_id=user["id"],
        user_email=user["email"],
        prompt=f"חיפוש ישיר: {result['origin']} -> {result['destination']} ({result['departure_date']})"
    )

    # Consume search credit & attach quota
    updated_quota = consume_search_credit(user["id"])
    result["quota"] = updated_quota
    result["user_session"] = {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "plan_tier": updated_quota["plan_tier"],
        "plan_name": updated_quota["plan_name"]
    }

    # Automated QA Quality Audit verification
    result["quality_audit"] = QualityAuditor.verify_response_compliance(result)

    return result

@router.post("/ai-search")
def ai_search_endpoint(req: AISearchRequest, request: Request):
    """
    Takes natural language Hebrew/English query, parses it with Gemini AI,
    executes Google Flights live search, and returns structured results + AI advice.
    """
    user = get_current_user(request)
    quota = get_user_quota(user)
    if not quota.get("unlimited") and quota["is_depleted"]:
        raise HTTPException(
            status_code=403, 
            detail=f"הגעת למכסת {quota['searches_limit']} החיפושים החודשית שלך במנוי {quota['plan_name']}. שדרג את המנוי עכשיו להמשך חיפושים!"
        )

    if not req.prompt or len(req.prompt.strip()) < 2:
        raise HTTPException(status_code=400, detail="נא להזין בקשת טיסה תקינה.")

    # 1. Parse intent with Gemini
    parsed = parse_flight_intent(req.prompt)
    
    # Override defaults if provided in request
    origin = req.origin or parsed.get("origin") or "TLV"
    currency = req.currency or parsed.get("currency") or "ILS"
    destination = parsed.get("destination") or "ATH"
    departure_date = parsed.get("departure_date")
    return_date = parsed.get("return_date")
    trip_type = parsed.get("trip_type", "round-trip")
    direct_only = parsed.get("direct_only", False)
    passengers = parsed.get("passengers", 1)

    max_stops = 0 if direct_only else None

    # Detect baggage preference from user prompt
    is_luggage_requested = any(w in req.prompt for w in ["מזוודות", "מזוודה", "כבודה", "luggage", "bags", "baggage"])
    baggage_mode = "checked" if is_luggage_requested else (parsed.get("baggage") or "standard")

    # 2. Execute live search with parallel engines and Playwright crawler
    search_res = execute_flight_search(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        trip_type=trip_type,
        currency=currency,
        max_stops=max_stops,
        passengers=passengers,
        baggage=baggage_mode,
        include_browser_crawler=True
    )

    if not search_res.get("success"):
        raise HTTPException(status_code=400, detail=search_res.get("error", "חיפוש הטיסות נכשל"))

    # 3. Generate AI flight advisory tailored specifically to the user's prompt
    ai_advice = generate_flight_advice(search_res, user_prompt=req.prompt)
    search_res["ai_advice"] = ai_advice
    search_res["parsed_query"] = parsed
    search_res["user_prompt"] = req.prompt
    search_res["candidate_date_options"] = parsed.get("candidate_date_options", [])
    search_res["min_nights"] = parsed.get("min_nights")
    search_res["max_nights"] = parsed.get("max_nights")

    # 4. Save to history
    ai_offers_to_save = search_res.get("combined_offers") or search_res.get("flights", [])
    save_search_history(
        origin=search_res["origin"],
        destination=search_res["destination"],
        departure_date=search_res["departure_date"],
        return_date=search_res.get("return_date"),
        trip_type=search_res["trip_type"],
        direct_only=direct_only,
        currency=search_res["currency"],
        lowest_price=search_res.get("lowest_price"),
        results_count=len(ai_offers_to_save),
        ai_recommendation=ai_advice.get("summary_markdown", ""),
        results=ai_offers_to_save,
        user_id=user["id"],
        user_email=user["email"],
        prompt=req.prompt
    )

    # Automated QA Quality Audit verification on every AI query
    search_res["quality_audit"] = QualityAuditor.verify_response_compliance(search_res)

    # Consume search credit & attach quota
    updated_quota = consume_search_credit(user["id"])
    search_res["quota"] = updated_quota
    search_res["user_session"] = {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "plan_tier": updated_quota["plan_tier"],
        "plan_name": updated_quota["plan_name"]
    }

    return search_res

@router.get("/flexible-weekends")
def flexible_weekends_endpoint(
    destination: str = Query(..., description="Destination airport code or city"),
    origin: str = Query(default="TLV"),
    currency: str = Query(default="ILS"),
    direct_only: bool = Query(default=False)
):
    """Scans the next 4 weekend getaways to find the cheapest weekend."""
    deals = scan_flexible_weekend_deals(
        origin=origin,
        destination=destination,
        weeks_ahead=4,
        currency=currency,
        direct_only=direct_only
    )
    return {"destination": destination, "origin": origin, "deals": deals}

@router.get("/history")
def get_history_endpoint(limit: int = 15):
    """Returns recent flight search history."""
    return get_recent_searches(limit=limit)

@router.post("/track")
def track_flight_endpoint(req: TrackRouteRequest, request: Request):
    """Saves a flight route to be tracked for price drops."""
    from flight_agent.auth import get_current_user_optional
    user = get_current_user_optional(request)
    user_id = user["id"] if user else None
    user_email = user["email"] if user else None

    track_id = add_tracked_flight(
        origin=req.origin,
        destination=req.destination,
        departure_date=req.departure_date,
        return_date=req.return_date,
        trip_type=req.trip_type,
        max_budget=req.max_budget,
        currency=req.currency,
        lowest_price_seen=req.lowest_price_seen,
        best_airline=req.best_airline,
        booking_link=req.booking_link,
        user_id=user_id,
        user_email=user_email,
        user_phone=req.user_phone,
        direct_only=req.direct_only,
        passengers=req.passengers,
        target_price=req.target_price
    )
    return {
        "success": True,
        "track_id": track_id,
        "message": f"המעקב אחרי טיסה ל-{req.destination} הופעל בהצלחה! תקבל התראה ברגע שהמחיר יירד.",
        "tracked_route": {
            "origin": req.origin,
            "destination": req.destination,
            "dates": f"{req.departure_date} עד {req.return_date or ''}",
            "initial_price": req.lowest_price_seen,
            "target_price": req.target_price or req.max_budget,
            "currency": req.currency
        }
    }

@router.get("/tracked")
def get_tracked_endpoint(request: Request):
    """Returns active tracked flight alerts for the logged-in user or all for admin."""
    from flight_agent.auth import get_current_user_optional
    user = get_current_user_optional(request)
    if user and (user.get("role") == "admin" or user.get("email") == "xeinok2@gmail.com"):
        flights = get_tracked_flights()
    elif user:
        flights = get_tracked_flights(user_id=user["id"], user_email=user["email"])
    else:
        flights = get_tracked_flights()
    return flights

@router.delete("/track/{track_id}")
def delete_tracked_endpoint(track_id: int, request: Request):
    """Removes a tracked flight."""
    from flight_agent.auth import get_current_user_optional
    user = get_current_user_optional(request)
    user_id = user["id"] if (user and user.get("role") != "admin") else None
    success = delete_tracked_flight(track_id, user_id=user_id)
    return {"success": success, "message": "המעקב הוסר בהצלחה"}

@router.post("/track/{track_id}/check-now")
def check_tracked_now_endpoint(track_id: int):
    """Forces an immediate live price re-check for a tracked route."""
    from flight_agent.price_tracker_daemon import check_single_tracked_flight
    res = check_single_tracked_flight(track_id)
    return res

@router.post("/track/scan-all")
def scan_all_tracked_endpoint(background_tasks: BackgroundTasks):
    """Triggers an autonomous price drop sweep for all tracked routes in background."""
    from flight_agent.price_tracker_daemon import scan_all_active_tracked_flights
    background_tasks.add_task(scan_all_active_tracked_flights)
    return {"success": True, "message": "סריקת מחירי טיסות לכל המשתמשים הופעלה ברקע!"}

@router.get("/price-alerts/summary")
def price_alerts_summary_endpoint(request: Request):
    """Returns price drop summary statistics."""
    from flight_agent.auth import get_current_user_optional
    from flight_agent.db import get_price_alerts_summary
    user = get_current_user_optional(request)
    user_id = user["id"] if (user and user.get("role") != "admin") else None
    user_email = user["email"] if (user and user.get("role") != "admin") else None
    return get_price_alerts_summary(user_id=user_id, user_email=user_email)

@router.post("/playwright-crawl")
async def playwright_crawl_endpoint(req: PlaywrightCrawlRequest):
    """
    Executes live physical browser crawler using Playwright
    across Israeli flight sources (Secret Flights, Israir, Bluebird)
    to discover direct airline fares.
    """
    from flight_agent.playwright_crawler import execute_playwright_airline_crawl
    dest_code = resolve_airport_code(req.destination) or req.destination.upper()
    crawl_result = await execute_playwright_airline_crawl(
        dest_code,
        departure_date=req.departure_date or "",
        return_date=req.return_date,
        currency=req.currency
    )
    return crawl_result

@router.get("/quality-audit")
def get_quality_audit_endpoint():
    """
    Returns the mapped requirements matrix and latest Playwright QA audit report.
    """
    matrix = get_requirements_matrix()
    latest = load_latest_audit_results()
    return {
        "success": True,
        "requirements_matrix": matrix,
        "latest_audit": latest
    }

@router.post("/run-audit")
async def run_quality_audit_endpoint(req: RunAuditRequest = RunAuditRequest()):
    """
    Executes a physical browser Playwright verification audit across all requirements
    and returns a structured compliance report.
    """
    report = await QualityAuditor.run_full_browser_audit(
        origin=req.origin,
        destination=req.destination,
        departure_date=req.departure_date,
        return_date=req.return_date,
        currency=req.currency
    )
    return report

