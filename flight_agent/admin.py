import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from flight_agent.config import DB_PATH
from flight_agent.auth import get_connection, require_admin, PLANS, upgrade_user_plan, get_user_quota, hash_password

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

class SetPlanPayload(BaseModel):
    plan_tier: str

class ChangePasswordPayload(BaseModel):
    new_password: str

@admin_router.get("/overview")
def get_admin_overview(request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Aggregates comprehensive system statistics, KPIs, financial metrics, and chart data."""
    conn = get_connection()
    c = conn.cursor()

    # 1. Total Users
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0

    # 2. Active Users (last 24 hours & last 7 days)
    c.execute("SELECT COUNT(DISTINCT id) FROM users WHERE last_login >= datetime('now', '-1 day')")
    active_users_24h = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(DISTINCT id) FROM users WHERE last_login >= datetime('now', '-7 days')")
    active_users_7d = c.fetchone()[0] or 0

    # 3. Total Searches & Recent Searches
    c.execute("SELECT COUNT(*) FROM flight_searches")
    total_searches = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM flight_searches WHERE created_at >= datetime('now', '-1 day')")
    searches_24h = c.fetchone()[0] or 0

    # 4. Revenue Calculation (Monthly recurring revenue in ILS)
    c.execute("SELECT COALESCE(SUM(plan_price), 0) FROM users")
    total_revenue_ils = float(c.fetchone()[0] or 0.0)

    # 5. Paying Subscribers vs Free
    c.execute("SELECT COUNT(*) FROM users WHERE plan_price > 0")
    paying_subscribers = c.fetchone()[0] or 0

    conversion_rate = round((paying_subscribers / total_users * 100), 1) if total_users > 0 else 0.0
    avg_searches_per_user = round(total_searches / total_users, 1) if total_users > 0 else 0.0

    # 6. Depleted Users (Reached limit)
    c.execute("SELECT COUNT(*) FROM users WHERE searches_used >= searches_limit AND plan_tier != 'admin'")
    depleted_users_count = c.fetchone()[0] or 0

    # 6b. Pending Bit Payments Count
    c.execute("SELECT COUNT(*) FROM bit_payments WHERE status = 'pending'")
    pending_bit_payments_count = c.fetchone()[0] or 0

    # 7. Plan Distribution
    c.execute("""
        SELECT plan_tier, plan_name, COUNT(*) as user_count
        FROM users
        GROUP BY plan_tier
        ORDER BY user_count DESC
    """)
    plan_rows = c.fetchall()
    plan_distribution = [
        {"plan_tier": r["plan_tier"], "plan_name": r["plan_name"], "count": r["user_count"]}
        for r in plan_rows
    ]

    # 8. Top Searched Destinations
    c.execute("""
        SELECT destination, COUNT(*) as search_count, 
               ROUND(AVG(lowest_price), 0) as avg_price,
               MIN(lowest_price) as min_price
        FROM flight_searches
        WHERE destination IS NOT NULL AND destination != ''
        GROUP BY destination
        ORDER BY search_count DESC
        LIMIT 8
    """)
    dest_rows = c.fetchall()
    top_destinations = [
        {
            "destination": r["destination"],
            "count": r["search_count"],
            "avg_price": r["avg_price"],
            "min_price": r["min_price"]
        }
        for r in dest_rows
    ]

    # 9. Daily Searches Trend (Last 14 days)
    c.execute("""
        SELECT date(created_at) as s_date, COUNT(*) as cnt
        FROM flight_searches
        WHERE created_at >= datetime('now', '-14 days')
        GROUP BY date(created_at)
        ORDER BY s_date ASC
    """)
    trend_rows = c.fetchall()
    daily_trend = [{"date": r["s_date"], "count": r["cnt"]} for r in trend_rows]

    # 10. Recent Searches Global Feed
    c.execute("""
        SELECT id, origin, destination, departure_date, return_date, trip_type,
               direct_only, currency, lowest_price, results_count,
               user_id, user_email, prompt, created_at
        FROM flight_searches
        ORDER BY created_at DESC
        LIMIT 10
    """)
    recent_rows = c.fetchall()
    recent_feed = [dict(r) for r in recent_rows]

    conn.close()

    return {
        "kpis": {
            "total_users": total_users,
            "active_users_24h": active_users_24h,
            "active_users_7d": active_users_7d,
            "total_searches": total_searches,
            "searches_24h": searches_24h,
            "total_revenue_ils": total_revenue_ils,
            "paying_subscribers": paying_subscribers,
            "conversion_rate": conversion_rate,
            "avg_searches_per_user": avg_searches_per_user,
            "depleted_users_count": depleted_users_count,
            "pending_bit_payments": pending_bit_payments_count
        },
        "plan_distribution": plan_distribution,
        "top_destinations": top_destinations,
        "daily_trend": daily_trend,
        "recent_searches": recent_feed,
        "admin_user": {
            "email": current_admin["email"],
            "full_name": current_admin["full_name"],
            "role": "admin"
        }
    }

@admin_router.get("/users")
def get_all_users_endpoint(request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Returns detailed list of all users with search quotas, activity, and search counts."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT 
            u.id, u.email, u.full_name, u.role, u.is_admin, u.is_blocked,
            u.plan_tier, u.plan_name, u.plan_price,
            u.searches_limit, u.searches_used,
            u.created_at, u.last_login, u.current_period_start,
            COUNT(s.id) as logged_searches_count
        FROM users u
        LEFT JOIN flight_searches s ON (s.user_id = u.id OR s.user_email = u.email)
        GROUP BY u.id
        ORDER BY u.id DESC
    """)
    rows = c.fetchall()
    conn.close()

    users_list = []
    for r in rows:
        u = dict(r)
        is_admin_user = bool(u.get("is_admin") == 1 or u.get("role") == "admin" or u.get("email") == "xeinok2@gmail.com")
        is_blocked_user = bool(u.get("is_blocked", 0) == 1)
        limit = u.get("searches_limit", 10)
        used = u.get("searches_used", 0)
        remaining = 999999 if is_admin_user else max(0, limit - used)
        percentage = 0 if is_admin_user else (min(100, int((used / limit) * 100)) if limit > 0 else 100)
        
        users_list.append({
            "id": u["id"],
            "email": u["email"],
            "full_name": u["full_name"],
            "is_admin": is_admin_user,
            "role": "admin" if is_admin_user else "user",
            "is_blocked": is_blocked_user,
            "plan_tier": u["plan_tier"],
            "plan_name": u["plan_name"],
            "plan_price": u["plan_price"],
            "searches_limit": 999999 if is_admin_user else limit,
            "searches_used": used,
            "searches_remaining": remaining,
            "percentage_used": percentage,
            "is_depleted": (remaining <= 0) and not is_admin_user,
            "unlimited": is_admin_user,
            "created_at": u["created_at"],
            "last_login": u["last_login"],
            "logged_searches_count": u["logged_searches_count"]
        })

    return {"users": users_list, "total": len(users_list)}

@admin_router.get("/users/{user_id}/history")
def get_user_search_history_endpoint(user_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Fetches complete search queries and flight findings for a specific user."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    u_row = c.fetchone()
    if not u_row:
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא במערכת")
    user = dict(u_row)

    c.execute("""
        SELECT id, origin, destination, departure_date, return_date, trip_type,
               direct_only, currency, lowest_price, results_count,
               ai_recommendation, prompt, created_at
        FROM flight_searches
        WHERE user_id = ? OR user_email = ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (user["id"], user["email"]))
    rows = c.fetchall()
    conn.close()

    history = [dict(r) for r in rows]
    return {
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "plan_tier": user["plan_tier"],
            "plan_name": user["plan_name"]
        },
        "searches": history,
        "total_searches": len(history)
    }

@admin_router.post("/users/{user_id}/reset-quota")
def reset_user_quota_endpoint(user_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Resets searches_used to 0 for a specific user."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET searches_used = 0 WHERE id = ?", (user_id,))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")
    conn.commit()

    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(c.fetchone())
    conn.close()

    quota = get_user_quota(user)
    return {
        "success": True,
        "message": f"מכסת החיפושים עבור {user['full_name']} ({user['email']}) אופסה בהצלחה ל-0 מתוך {quota['searches_limit']}.",
        "quota": quota
    }

@admin_router.post("/users/{user_id}/set-plan")
def set_user_plan_endpoint(user_id: int, req: SetPlanPayload, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Admin endpoint to change any user's plan tier."""
    if req.plan_tier not in PLANS:
        raise HTTPException(status_code=400, detail=f"תוכנית לא קיימת: {req.plan_tier}")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")

    plan = PLANS[req.plan_tier]
    is_admin_plan = (req.plan_tier == "admin")
    
    c.execute("""
        UPDATE users
        SET plan_tier = ?,
            plan_name = ?,
            searches_limit = ?,
            plan_price = ?,
            is_admin = ?,
            role = ?
        WHERE id = ?
    """, (
        plan["id"],
        plan["name"],
        plan["searches_limit"],
        plan["price"],
        1 if is_admin_plan else 0,
        "admin" if is_admin_plan else "user",
        user_id
    ))
    conn.commit()

    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    updated_user = dict(c.fetchone())
    conn.close()

    quota = get_user_quota(updated_user)
    return {
        "success": True,
        "message": f"התוכנית של {updated_user['full_name']} עודכנה בהצלחה ל-{plan['name']}.",
        "user": {
            "id": updated_user["id"],
            "email": updated_user["email"],
            "plan_tier": updated_user["plan_tier"],
            "plan_name": updated_user["plan_name"],
            "searches_limit": quota["searches_limit"],
            "searches_remaining": quota["searches_remaining"]
        }
    }

@admin_router.post("/users/{user_id}/toggle-block")
def toggle_block_user_endpoint(user_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Toggles block status for a user. Invalidates active sessions if blocked."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא במערכת")
    user = dict(row)

    if user["email"] == "xeinok2@gmail.com" or user["id"] == current_admin["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="לא ניתן לחסום את מנהל המערכת הראשי")

    current_blocked = user.get("is_blocked", 0) or 0
    new_blocked = 1 if current_blocked == 0 else 0

    c.execute("UPDATE users SET is_blocked = ? WHERE id = ?", (new_blocked, user_id))
    if new_blocked == 1:
        c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    status_str = "נחסם" if new_blocked == 1 else "שוחרר מחסימה"
    return {
        "success": True,
        "is_blocked": bool(new_blocked == 1),
        "message": f"המשתמש {user['full_name']} ({user['email']}) {status_str} בהצלחה."
    }

@admin_router.post("/users/{user_id}/change-password")
def change_user_password_endpoint(user_id: int, req: ChangePasswordPayload, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Changes password for a user."""
    new_pw = (req.new_password or "").strip()
    if len(new_pw) < 4:
        raise HTTPException(status_code=400, detail="הסיסמה חייבת להכיל לפחות 4 תווים")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא במערכת")
    user = dict(row)

    new_hash = hash_password(new_pw)
    c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    if user["id"] != current_admin["id"]:
        c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"הסיסמה עבור {user['full_name']} ({user['email']}) עודכנה בהצלחה!"
    }

@admin_router.delete("/users/{user_id}")
def delete_user_endpoint(user_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Permanently deletes a user and associated records."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא במערכת")
    user = dict(row)

    if user["email"] == "xeinok2@gmail.com" or user["id"] == current_admin["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="לא ניתן למחוק את מנהל המערכת הראשי")

    try:
        c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM biometric_credentials WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM bit_payments WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM tracked_flights WHERE user_id = ?", (user_id,))
    except Exception as e:
        print(f"[Admin delete user cleanup]: {e}")

    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"המשתמש {user['full_name']} ({user['email']}) נמחק לצמיתות מהמערכת."
    }

@admin_router.get("/searches")
def get_global_searches_endpoint(
    request: Request,
    q: Optional[str] = None,
    user_email: Optional[str] = None,
    destination: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    direct_only: Optional[bool] = None,
    limit: Optional[int] = None,
    current_admin: Dict[str, Any] = Depends(require_admin)
):
    """
    Admin feed of searches with comprehensive filters.
    If limit is None or <= 0, returns the ENTIRE search history.
    """
    conn = get_connection()
    c = conn.cursor()

    # Total searches count
    c.execute("SELECT COUNT(*) FROM flight_searches")
    total_count = c.fetchone()[0] or 0

    # Distinct destinations & users for filter dropdowns
    c.execute("SELECT DISTINCT destination FROM flight_searches WHERE destination IS NOT NULL AND destination != '' ORDER BY destination ASC")
    destinations = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT user_email FROM flight_searches WHERE user_email IS NOT NULL AND user_email != '' ORDER BY user_email ASC")
    user_emails = [r[0] for r in c.fetchall()]

    # Dynamic filter clauses
    where_clauses = []
    params = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(s.destination LIKE ? OR s.origin LIKE ? OR s.prompt LIKE ? OR s.user_email LIKE ? OR u.full_name LIKE ?)")
        params.extend([term, term, term, term, term])

    if user_email and user_email.strip() and user_email.strip() != "all":
        where_clauses.append("s.user_email = ?")
        params.append(user_email.strip())

    if destination and destination.strip() and destination.strip() != "all":
        where_clauses.append("s.destination = ?")
        params.append(destination.strip().upper())

    if from_date and from_date.strip():
        where_clauses.append("date(s.created_at) >= date(?)")
        params.append(from_date.strip())

    if to_date and to_date.strip():
        where_clauses.append("date(s.created_at) <= date(?)")
        params.append(to_date.strip())

    if direct_only is True:
        where_clauses.append("s.direct_only = 1")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    limit_sql = ""
    if limit is not None and limit > 0:
        limit_sql = f"LIMIT {int(limit)}"

    query = f"""
        SELECT s.id, s.origin, s.destination, s.departure_date, s.return_date, s.trip_type,
               s.direct_only, s.currency, s.lowest_price, s.results_count,
               s.ai_recommendation, s.prompt, s.created_at,
               s.user_id, s.user_email, u.full_name as user_name
        FROM flight_searches s
        LEFT JOIN users u ON (s.user_id = u.id OR s.user_email = u.email)
        {where_sql}
        ORDER BY s.created_at DESC
        {limit_sql}
    """

    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()

    searches = [dict(r) for r in rows]

    return {
        "searches": searches,
        "total_count": total_count,
        "filtered_count": len(searches),
        "available_destinations": destinations,
        "available_users": user_emails
    }

@admin_router.get("/bit-payments")
def get_bit_payments_endpoint(request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Lists all Bit payments requested by users."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, u.full_name as current_user_name
        FROM bit_payments p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    payments_list = [dict(r) for r in rows]
    pending_count = sum(1 for p in payments_list if p.get("status") == "pending")
    return {
        "payments": payments_list,
        "total": len(payments_list),
        "pending_count": pending_count
    }

@admin_router.post("/bit-payments/{payment_id}/approve")
def approve_bit_payment_endpoint(payment_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Approves a Bit payment and upgrades the user's plan."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bit_payments WHERE id = ?", (payment_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="בקשת תשלום בביט לא נמצאה")
    
    payment = dict(row)
    c.execute("""
        UPDATE bit_payments
        SET status = 'approved',
            approved_by = ?,
            approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (current_admin["email"], payment_id))
    conn.commit()
    conn.close()

    updated_quota = upgrade_user_plan(payment["user_id"], payment["plan_tier"])
    
    return {
        "success": True,
        "message": f"תשלום הביט בסך {payment['amount_ils']} ₪ אושר בהצלחה! המשתמש {payment['user_email']} שודרג ל-{payment['plan_name']}.",
        "payment": payment,
        "quota": updated_quota
    }

@admin_router.post("/bit-payments/{payment_id}/reject")
def reject_bit_payment_endpoint(payment_id: int, request: Request, current_admin: Dict[str, Any] = Depends(require_admin)):
    """Rejects a Bit payment."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bit_payments WHERE id = ?", (payment_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="בקשת תשלום בביט לא נמצאה")
    
    c.execute("""
        UPDATE bit_payments
        SET status = 'rejected',
            approved_by = ?,
            approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (current_admin["email"], payment_id))
    conn.commit()
    conn.close()

    return {"success": True, "message": "בקשת התשלום נדחתה."}
