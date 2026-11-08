import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from flight_agent.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_flight_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Search History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flight_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT,
            trip_type TEXT NOT NULL,
            direct_only INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'ILS',
            lowest_price REAL,
            results_count INTEGER,
            ai_recommendation TEXT,
            results_json TEXT,
            user_id INTEGER,
            user_email TEXT,
            prompt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration for existing flight_searches tables
    try:
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(flight_searches)").fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE flight_searches ADD COLUMN user_id INTEGER")
        if "user_email" not in cols:
            cursor.execute("ALTER TABLE flight_searches ADD COLUMN user_email TEXT")
        if "prompt" not in cols:
            cursor.execute("ALTER TABLE flight_searches ADD COLUMN prompt TEXT")
    except Exception as e:
        print(f"[flight_searches migration]: {e}")
    
    # 2. Tracked Price Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT,
            trip_type TEXT NOT NULL,
            max_budget REAL,
            currency TEXT DEFAULT 'ILS',
            last_checked TIMESTAMP,
            lowest_price_seen REAL,
            best_airline TEXT,
            booking_link TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration for tracked_flights table
    try:
        tf_cols = [r[1] for r in cursor.execute("PRAGMA table_info(tracked_flights)").fetchall()]
        if "user_id" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN user_id INTEGER")
        if "user_email" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN user_email TEXT")
        if "user_phone" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN user_phone TEXT")
        if "initial_price" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN initial_price REAL")
        if "target_price" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN target_price REAL")
        if "current_price" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN current_price REAL")
        if "price_drop_amount" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN price_drop_amount REAL DEFAULT 0.0")
        if "price_drop_percent" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN price_drop_percent REAL DEFAULT 0.0")
        if "price_history_json" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN price_history_json TEXT")
        if "direct_only" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN direct_only INTEGER DEFAULT 0")
        if "passengers" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN passengers INTEGER DEFAULT 1")
        if "notification_sent" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN notification_sent INTEGER DEFAULT 0")
        if "last_alert_sent" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN last_alert_sent TIMESTAMP")
        if "alert_status" not in tf_cols:
            cursor.execute("ALTER TABLE tracked_flights ADD COLUMN alert_status TEXT DEFAULT 'tracking'")
    except Exception as e:
        print(f"[tracked_flights migration]: {e}")

    conn.commit()
    conn.close()

    # 3. Auth and user quotas
    from flight_agent.auth import init_auth_db
    init_auth_db()

def save_search_history(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    trip_type: str,
    direct_only: bool,
    currency: str,
    lowest_price: Optional[float],
    results_count: int,
    ai_recommendation: Optional[str],
    results: List[Dict[str, Any]],
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    prompt: Optional[str] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO flight_searches (
            origin, destination, departure_date, return_date, trip_type,
            direct_only, currency, lowest_price, results_count,
            ai_recommendation, results_json, user_id, user_email, prompt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        origin, destination, departure_date, return_date, trip_type,
        1 if direct_only else 0, currency, lowest_price, results_count,
        ai_recommendation, json.dumps(results, ensure_ascii=False),
        user_id, user_email, prompt
    ))
    
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id

def get_recent_searches(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, origin, destination, departure_date, return_date, trip_type,
               direct_only, currency, lowest_price, results_count,
               ai_recommendation, user_id, user_email, prompt, created_at
        FROM flight_searches
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_searches_by_user(user_id: Optional[int] = None, user_email: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_id and user_email:
        cursor.execute("""
            SELECT id, origin, destination, departure_date, return_date, trip_type,
                   direct_only, currency, lowest_price, results_count,
                   ai_recommendation, user_id, user_email, prompt, created_at
            FROM flight_searches
            WHERE user_id = ? OR user_email = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, user_email, limit))
    elif user_id:
        cursor.execute("""
            SELECT id, origin, destination, departure_date, return_date, trip_type,
                   direct_only, currency, lowest_price, results_count,
                   ai_recommendation, user_id, user_email, prompt, created_at
            FROM flight_searches
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
    elif user_email:
        cursor.execute("""
            SELECT id, origin, destination, departure_date, return_date, trip_type,
                   direct_only, currency, lowest_price, results_count,
                   ai_recommendation, user_id, user_email, prompt, created_at
            FROM flight_searches
            WHERE user_email = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_email, limit))
    else:
        cursor.execute("""
            SELECT id, origin, destination, departure_date, return_date, trip_type,
                   direct_only, currency, lowest_price, results_count,
                   ai_recommendation, user_id, user_email, prompt, created_at
            FROM flight_searches
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_tracked_flight(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    trip_type: str,
    max_budget: Optional[float] = None,
    currency: str = "ILS",
    lowest_price_seen: Optional[float] = None,
    best_airline: Optional[str] = None,
    booking_link: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_phone: Optional[str] = None,
    direct_only: bool = False,
    passengers: int = 1,
    target_price: Optional[float] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    initial_p = float(lowest_price_seen) if lowest_price_seen is not None else None
    target_p = float(target_price) if target_price is not None else (float(max_budget) if max_budget is not None else None)
    
    # Initialize price history with first data point
    history_entry = [{
        "timestamp": datetime.now().isoformat(),
        "price": initial_p,
        "airline": best_airline or "חברת תעופה",
        "engine": "Initial Search"
    }] if initial_p else []

    cursor.execute("""
        INSERT INTO tracked_flights (
            origin, destination, departure_date, return_date, trip_type,
            max_budget, currency, last_checked, lowest_price_seen,
            initial_price, target_price, current_price,
            price_drop_amount, price_drop_percent, price_history_json,
            best_airline, booking_link, is_active,
            user_id, user_email, user_phone, direct_only, passengers,
            alert_status
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, CURRENT_TIMESTAMP, ?,
            ?, ?, ?,
            0.0, 0.0, ?,
            ?, ?, 1,
            ?, ?, ?, ?, ?,
            'tracking'
        )
    """, (
        origin, destination, departure_date, return_date, trip_type,
        target_p, currency, initial_p,
        initial_p, target_p, initial_p,
        json.dumps(history_entry, ensure_ascii=False),
        best_airline, booking_link,
        user_id, user_email, user_phone, 1 if direct_only else 0, passengers
    ))
    
    track_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return track_id

def record_price_check(
    track_id: int,
    new_price: float,
    new_airline: Optional[str] = None,
    booking_link: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates a tracked flight with newly discovered live price,
    computes price drop statistics, appends to price history JSON,
    and sets alert status if a drop is detected.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tracked_flights WHERE id = ?", (track_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Flight not found"}

    item = dict(row)
    init_p = float(item.get("initial_price") or item.get("lowest_price_seen") or new_price)
    lowest_seen = float(item.get("lowest_price_seen") or init_p)
    target_p = float(item.get("target_price") or item.get("max_budget") or 0.0)
    
    new_lowest = min(lowest_seen, new_price)
    drop_amt = max(0.0, round(init_p - new_price, 2))
    drop_pct = max(0.0, round((drop_amt / init_p) * 100, 1)) if init_p > 0 else 0.0
    
    # Parse history
    try:
        history = json.loads(item.get("price_history_json") or "[]")
    except Exception:
        history = []
        
    history.append({
        "timestamp": datetime.now().isoformat(),
        "price": round(new_price, 2),
        "airline": new_airline or item.get("best_airline") or "חברת תעופה",
        "drop_percent": drop_pct
    })
    # Keep last 25 checks
    history = history[-25:]

    # Determine alert status
    new_status = "tracking"
    is_alert = False
    if target_p > 0 and new_price <= target_p:
        new_status = "target_reached"
        is_alert = True
    elif drop_pct >= 5.0: # 5% or more price drop
        new_status = "price_dropped"
        is_alert = True

    cursor.execute("""
        UPDATE tracked_flights
        SET current_price = ?,
            lowest_price_seen = ?,
            price_drop_amount = ?,
            price_drop_percent = ?,
            price_history_json = ?,
            best_airline = COALESCE(?, best_airline),
            booking_link = COALESCE(?, booking_link),
            last_checked = CURRENT_TIMESTAMP,
            alert_status = ?,
            last_alert_sent = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE last_alert_sent END
        WHERE id = ?
    """, (
        round(new_price, 2),
        round(new_lowest, 2),
        drop_amt,
        drop_pct,
        json.dumps(history, ensure_ascii=False),
        new_airline,
        booking_link,
        new_status,
        1 if is_alert else 0,
        track_id
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "track_id": track_id,
        "new_price": new_price,
        "initial_price": init_p,
        "price_drop_amount": drop_amt,
        "price_drop_percent": drop_pct,
        "is_alert": is_alert,
        "alert_status": new_status,
        "airline": new_airline or item.get("best_airline")
    }

def get_tracked_flights(
    user_id: Optional[int] = None,
    user_email: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_id and user_email:
        cursor.execute("""
            SELECT * FROM tracked_flights
            WHERE is_active = 1 AND (user_id = ? OR user_email = ?)
            ORDER BY created_at DESC
        """, (user_id, user_email))
    elif user_id:
        cursor.execute("""
            SELECT * FROM tracked_flights
            WHERE is_active = 1 AND user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    elif user_email:
        cursor.execute("""
            SELECT * FROM tracked_flights
            WHERE is_active = 1 AND user_email = ?
            ORDER BY created_at DESC
        """, (user_email,))
    else:
        cursor.execute("""
            SELECT * FROM tracked_flights
            WHERE is_active = 1
            ORDER BY created_at DESC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["price_history"] = json.loads(d.get("price_history_json") or "[]")
        except Exception:
            d["price_history"] = []
        results.append(d)
        
    return results

def delete_tracked_flight(track_id: int, user_id: Optional[int] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("UPDATE tracked_flights SET is_active = 0 WHERE id = ? AND user_id = ?", (track_id, user_id))
    else:
        cursor.execute("UPDATE tracked_flights SET is_active = 0 WHERE id = ?", (track_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def get_price_alerts_summary(user_id: Optional[int] = None, user_email: Optional[str] = None) -> Dict[str, Any]:
    """Returns overview statistics of tracked flights, price drops, and total savings."""
    flights = get_tracked_flights(user_id, user_email)
    total_tracked = len(flights)
    drops = [f for f in flights if (f.get("price_drop_amount") or 0) > 0]
    total_drops_count = len(drops)
    total_saved = sum((f.get("price_drop_amount") or 0) for f in drops)
    
    max_drop = max([f.get("price_drop_percent") or 0 for f in flights], default=0)
    
    return {
        "total_tracked": total_tracked,
        "total_price_drops": total_drops_count,
        "total_savings": round(total_saved, 2),
        "max_drop_percent": round(max_drop, 1),
        "active_alerts": [f for f in flights if f.get("alert_status") in ["price_dropped", "target_reached"]]
    }

# Initialize tables immediately
init_flight_db()
