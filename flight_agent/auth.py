import sqlite3
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, HTTPException
from flight_agent.config import DB_PATH

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "מנוי חינמי",
        "price": 0,
        "searches_limit": 10,
        "price_label": "חינם",
        "badge_color": "bg-slate-100 text-slate-700 border-slate-300",
        "button_text": "המסלול הנוכחי שלך",
        "description": "אידיאלי לבדיקה והזמנת חופשה שנתית",
        "features": [
            "10 חיפושי טיסות מבוססי AI בחודש",
            "השוואת מחירים בזמן אמת מול כל המנועים",
            "פירוק מחירי מזוודות וכבודה לכל כיוון",
            "תמיכה בתאריכים גמישים ומסלולים מורכבים"
        ]
    },
    "starter": {
        "id": "starter",
        "name": "מנוי בסיסי (Starter)",
        "price": 10,
        "searches_limit": 20,
        "price_label": "10 ₪ / חודש",
        "badge_color": "bg-sky-100 text-sky-700 border-sky-300",
        "button_text": "שדרג ל-20 חיפושים",
        "description": "למטיילים עצמאיים ולסופי שבוע באירופה",
        "features": [
            "20 חיפושי טיסות בחודש (רק 50 אג' לחיפוש!)",
            "השוואת מחירי אמת מול Kiwi, Google Flights ועוד",
            "התראות מחיר אוטומטיות",
            "חישוב כבודה מדויק ל-2 נוסעים"
        ]
    },
    "pro": {
        "id": "pro",
        "name": "מנוי Pro מומלץ",
        "price": 20,
        "searches_limit": 40,
        "price_label": "20 ₪ / חודש",
        "badge_color": "bg-indigo-100 text-indigo-700 border-indigo-300",
        "popular": True,
        "button_text": "שדרג ל-40 חיפושים",
        "description": "המסלול הנבחר והמשתלם ביותר למשפחות וזוגות",
        "features": [
            "40 חיפושי טיסות בחודש (רק 50 אג' לחיפוש!)",
            "סריקת דפדפן פיזית עמוקה (Playwright Crawler)",
            "ניתוח המלצות מותאם אישית של Gemini AI",
            "חישוב קומבינטורי מלא לטווח לילות וגמישות תאריכים"
        ]
    },
    "vip": {
        "id": "vip",
        "name": "מנוי VIP ללא דאגות",
        "price": 30,
        "searches_limit": 100,
        "price_label": "30 ₪ / חודש",
        "badge_color": "bg-amber-100 text-amber-800 border-amber-300",
        "best_value": True,
        "button_text": "שדרג ל-100 חיפושים",
        "description": "לציידי טיסות, סוכנים ונוסעים תכופים",
        "features": [
            "100 חיפושי טיסות בחודש (30 אגורות בלבד לחיפוש!)",
            "עדיפות סריקה מהירה בשרת",
            "סריקת שילובי תאריכים מרובים במקביל",
            "מעקב אחר שינויי מחירים ודוחות טיסות שבועיים"
        ]
    },
    "admin": {
        "id": "admin",
        "name": "מנהל מערכת (ללא הגבלה) 👑",
        "price": 0,
        "searches_limit": 999999,
        "price_label": "ללא הגבלה (Admin)",
        "badge_color": "bg-purple-100 text-purple-900 border-purple-300",
        "button_text": "מנהל מערכת",
        "description": "גישת מנהל מערכת מלאה ללא הגבלת חיפושים ודאשבורד ניהול",
        "features": [
            "חיפושים ללא הגבלה (Unlimited AI Searches)",
            "גישה מלאה לדאשבורד ניהול וכל היוזרים",
            "צפייה בהיסטוריית חיפושים של כל משתמש",
            "סטטיסטיקות מתקדמות על כלל הפלטפורמה"
        ]
    }
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            plan_tier TEXT NOT NULL DEFAULT 'free',
            plan_name TEXT NOT NULL DEFAULT 'מנוי חינמי',
            searches_limit INTEGER NOT NULL DEFAULT 10,
            searches_used INTEGER NOT NULL DEFAULT 0,
            plan_price REAL NOT NULL DEFAULT 0.0,
            current_period_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS biometric_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            credential_id TEXT UNIQUE NOT NULL,
            device_name TEXT DEFAULT 'סמארטפון (Mobile Device)',
            biometric_type TEXT DEFAULT 'fingerprint_faceid',
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            user_email TEXT NOT NULL,
            user_name TEXT,
            plan_tier TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            amount_ils REAL NOT NULL,
            sender_phone TEXT NOT NULL,
            target_phone TEXT DEFAULT '0524845131',
            status TEXT DEFAULT 'pending',
            approved_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP
        )
    """)

    # Seed default demo user if table is empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        demo_salt = secrets.token_hex(16)
        demo_hash = f"{demo_salt}${hashlib.sha256((demo_salt + 'flight2026').encode('utf-8')).hexdigest()}"
        c.execute("""
            INSERT INTO users (email, password_hash, full_name, plan_tier, plan_name, searches_limit, searches_used, plan_price)
            VALUES ('demo@flighthunter.ai', ?, 'ישראל ישראלי', 'free', 'מנוי חינמי', 10, 0, 0.0)
        """, (demo_hash,))

    # Migration: Ensure is_admin, role, and is_blocked columns exist in users table
    try:
        user_cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        if "is_admin" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        if "role" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        if "is_blocked" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
    except Exception as e:
        print(f"[Users Migration info]: {e}")

    # Set xeinok2@gmail.com as Admin with unlimited search quota
    try:
        c.execute("""
            UPDATE users 
            SET is_admin = 1,
                role = 'admin',
                plan_tier = 'admin',
                plan_name = 'מנהל מערכת (ללא הגבלה) 👑',
                searches_limit = 999999,
                searches_used = 0
            WHERE email = 'xeinok2@gmail.com'
        """)
    except Exception as e:
        print(f"[Admin promotion info]: {e}")

    # Seed biometric credential for xeinok2@gmail.com
    try:
        c.execute("""
            INSERT OR IGNORE INTO biometric_credentials (user_id, credential_id, device_name, biometric_type)
            SELECT id, 'bio_cred_xeinok2_mobile', 'iPhone 14 (Mobile Biometrics)', 'fingerprint_faceid'
            FROM users WHERE email = 'xeinok2@gmail.com'
        """)
    except Exception as e:
        print(f"[Biometric seed info]: {e}")

    conn.commit()
    conn.close()

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hashed = stored_hash.split("$", 1)
        expected = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return hmac.compare_digest(hashed, expected)
    except Exception:
        return False

def check_and_reset_monthly_quota(user: Dict[str, Any]) -> Dict[str, Any]:
    """Resets searches_used to 0 if 30 days have passed since current_period_start."""
    try:
        raw_start = user.get("current_period_start")
        if raw_start:
            if isinstance(raw_start, str):
                p_start = datetime.fromisoformat(raw_start.replace("Z", "").split(".")[0])
            else:
                p_start = raw_start
            if (datetime.now() - p_start).days >= 30:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE users 
                    SET searches_used = 0, current_period_start = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user["id"],))
                conn.commit()
                conn.close()
                user["searches_used"] = 0
                user["current_period_start"] = datetime.now().isoformat()
    except Exception as e:
        print(f"[Quota Reset check error]: {e}")
    return user

def register_user(email: str, password: str, full_name: str, ip: str = "", ua: str = "", remember_me: bool = True) -> Tuple[Dict[str, Any], str, int]:
    clean_email = email.strip().lower()
    clean_name = full_name.strip()
    if not clean_email or "@" not in clean_email:
        raise ValueError("כתובת אימייל לא חוקית")
    if not password or len(password) < 4:
        raise ValueError("הסיסמה חייבת להכיל לפחות 4 תווים")
    if not clean_name:
        clean_name = clean_email.split("@")[0]

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
    if c.fetchone():
        conn.close()
        raise ValueError("משתמש עם אימייל זה כבר קיים במערכת")

    pw_hash = hash_password(password)
    default_plan = PLANS["free"]
    c.execute("""
        INSERT INTO users (email, password_hash, full_name, plan_tier, plan_name, searches_limit, searches_used, plan_price)
        VALUES (?, ?, ?, 'free', ?, ?, 0, 0.0)
    """, (clean_email, pw_hash, clean_name, default_plan["name"], default_plan["searches_limit"]))
    user_id = c.lastrowid
    conn.commit()

    token = secrets.token_urlsafe(32)
    days_valid = 30 if remember_me else 1
    expires = datetime.now() + timedelta(days=days_valid)
    max_age = 2592000 if remember_me else 86400

    c.execute("""
        INSERT INTO sessions (token, user_id, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (token, user_id, ip, ua, expires.isoformat()))
    conn.commit()

    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    user_dict = dict(row)
    conn.close()
    return user_dict, token, max_age

def login_user(email: str, password: str, ip: str = "", ua: str = "", remember_me: bool = True) -> Optional[Tuple[Dict[str, Any], str, int]]:
    clean_email = email.strip().lower()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    user = dict(row)
    if user.get("is_blocked") == 1:
        conn.close()
        raise ValueError("חשבון זה נחסם על ידי מנהל המערכת. לבירורים פנה לתמיכה.")

    if not verify_password(password, user["password_hash"]):
        conn.close()
        return None

    user = check_and_reset_monthly_quota(user)

    token = secrets.token_urlsafe(32)
    days_valid = 30 if remember_me else 1
    expires = datetime.now() + timedelta(days=days_valid)
    max_age = 2592000 if remember_me else 86400

    c.execute("""
        INSERT INTO sessions (token, user_id, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (token, user["id"], ip, ua, expires.isoformat()))
    c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return user, token, max_age

def register_biometric_credential(
    user_id: int, credential_id: str, device_name: str = "סמארטפון (Mobile Device)", biometric_type: str = "fingerprint_faceid"
) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO biometric_credentials (user_id, credential_id, device_name, biometric_type)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(credential_id) DO UPDATE SET
            user_id = excluded.user_id,
            device_name = excluded.device_name,
            biometric_type = excluded.biometric_type,
            last_used = CURRENT_TIMESTAMP
    """, (user_id, credential_id, device_name, biometric_type))
    conn.commit()
    conn.close()
    return {"success": True, "message": "זיהוי ביומטרי (Face ID / טביעת אצבע) הוגדר בהצלחה במכשיר זה!"}

def login_with_biometric(
    credential_id: str, email: Optional[str] = None, ip: str = "", ua: str = "", remember_me: bool = True
) -> Optional[Tuple[Dict[str, Any], str, int]]:
    conn = get_connection()
    c = conn.cursor()

    if email:
        c.execute("""
            SELECT u.*, b.credential_id 
            FROM users u
            JOIN biometric_credentials b ON b.user_id = u.id
            WHERE (b.credential_id = ? OR u.email = ?)
            ORDER BY b.last_used DESC LIMIT 1
        """, (credential_id, email.strip().lower()))
    else:
        c.execute("""
            SELECT u.*, b.credential_id 
            FROM users u
            JOIN biometric_credentials b ON b.user_id = u.id
            WHERE b.credential_id = ?
            ORDER BY b.last_used DESC LIMIT 1
        """, (credential_id,))

    row = c.fetchone()
    if not row:
        conn.close()
        return None

    user = dict(row)
    if user.get("is_blocked") == 1:
        conn.close()
        raise ValueError("חשבון זה נחסם על ידי מנהל המערכת. לבירורים פנה לתמיכה.")

    user = check_and_reset_monthly_quota(user)

    token = secrets.token_urlsafe(32)
    days_valid = 30 if remember_me else 1
    expires = datetime.now() + timedelta(days=days_valid)
    max_age = 2592000 if remember_me else 86400

    c.execute("""
        INSERT INTO sessions (token, user_id, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (token, user["id"], ip, ua, expires.isoformat()))
    c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    c.execute("UPDATE biometric_credentials SET last_used = CURRENT_TIMESTAMP WHERE credential_id = ?", (credential_id,))
    conn.commit()
    conn.close()
    return user, token, max_age

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.*, s.token, s.expires_at 
        FROM sessions s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.token = ?
    """, (token,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    user = dict(row)
    # Check if user is blocked by admin
    if user.get("is_blocked") == 1:
        delete_session(token)
        return None

    # Check session expiration
    try:
        exp = datetime.fromisoformat(user["expires_at"])
        if datetime.now() > exp:
            delete_session(token)
            return None
    except Exception:
        pass

    user = check_and_reset_monthly_quota(user)
    return user

def delete_session(token: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def get_user_quota(user_dict: Dict[str, Any]) -> Dict[str, Any]:
    is_admin = bool(
        user_dict.get("is_admin") == 1 or 
        user_dict.get("role") == "admin" or 
        user_dict.get("email") == "xeinok2@gmail.com" or
        user_dict.get("plan_tier") == "admin"
    )
    limit = user_dict.get("searches_limit", 10)
    used = user_dict.get("searches_used", 0)
    
    if is_admin:
        return {
            "user_id": user_dict.get("id"),
            "full_name": user_dict.get("full_name"),
            "email": user_dict.get("email"),
            "plan_tier": "admin",
            "plan_name": "מנהל מערכת (ללא הגבלה) 👑",
            "plan_price": 0.0,
            "searches_limit": 999999,
            "searches_used": used,
            "searches_remaining": 999999,
            "percentage_used": 0,
            "is_depleted": False,
            "unlimited": True,
            "is_admin": True,
            "role": "admin"
        }
    
    remaining = max(0, limit - used)
    percentage = min(100, int((used / limit) * 100)) if limit > 0 else 100
    plan_tier = user_dict.get("plan_tier", "free")
    plan_info = PLANS.get(plan_tier, PLANS["free"])
    
    return {
        "user_id": user_dict.get("id"),
        "full_name": user_dict.get("full_name"),
        "email": user_dict.get("email"),
        "plan_tier": plan_tier,
        "plan_name": user_dict.get("plan_name", plan_info["name"]),
        "plan_price": user_dict.get("plan_price", plan_info["price"]),
        "searches_limit": limit,
        "searches_used": used,
        "searches_remaining": remaining,
        "percentage_used": percentage,
        "is_depleted": (remaining <= 0),
        "unlimited": False,
        "is_admin": False,
        "role": "user"
    }

def consume_search_credit(user_id: int) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET searches_used = searches_used + 1 WHERE id = ?", (user_id,))
    conn.commit()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    user = dict(row)
    return get_user_quota(user)

def upgrade_user_plan(user_id: int, plan_tier: str) -> Dict[str, Any]:
    if plan_tier not in PLANS:
        raise ValueError(f"תוכנית לא מוכרת: {plan_tier}")

    plan = PLANS[plan_tier]
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET plan_tier = ?,
            plan_name = ?,
            searches_limit = ?,
            plan_price = ?
        WHERE id = ?
    """, (plan["id"], plan["name"], plan["searches_limit"], plan["price"], user_id))
    conn.commit()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    user = dict(row)
    return get_user_quota(user)

def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("flight_session_token")
    if not token:
        token = request.headers.get("X-Session-Token")
    if not token:
        return None
    return get_user_by_token(token)

def get_current_user(request: Request) -> Dict[str, Any]:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="נדרשת הרשמה או התחברות לאתר כדי לבצע חיפוש טיסות. כל משתמש חדש מקבל 10 חיפושים חינם בחודש!"
        )
    return user

def require_admin(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    is_admin = bool(
        user.get("is_admin") == 1 or 
        user.get("role") == "admin" or 
        user.get("email") == "xeinok2@gmail.com" or
        user.get("plan_tier") == "admin"
    )
    if not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="גישה חסומה: נדרשות הרשאות מנהל מערכת (Admin) לצפייה בדף זה."
        )
    return user

# --- FastAPI Auth Router ---
from fastapi import APIRouter, Response
from pydantic import BaseModel

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterPayload(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    remember_me: bool = True

class LoginPayload(BaseModel):
    email: str
    password: str
    remember_me: bool = True

class BiometricRegisterPayload(BaseModel):
    credential_id: str
    device_name: Optional[str] = "סמארטפון (Mobile Device)"
    biometric_type: Optional[str] = "fingerprint_faceid"

class BiometricLoginPayload(BaseModel):
    credential_id: str
    email: Optional[str] = None
    remember_me: bool = True

class UpgradePayload(BaseModel):
    plan_tier: str

@auth_router.post("/register")
def register_endpoint(req: RegisterPayload, request: Request, response: Response):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("User-Agent", "")
    try:
        user, token, max_age = register_user(
            email=req.email,
            password=req.password,
            full_name=req.full_name or "",
            ip=ip,
            ua=ua,
            remember_me=req.remember_me
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    response.set_cookie(
        key="flight_session_token",
        value=token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        path="/"
    )
    quota = get_user_quota(user)
    is_admin = quota.get("is_admin", False)
    return {
        "success": True,
        "token": token,
        "remember_me": req.remember_me,
        "session_duration": "חודש ימים" if req.remember_me else "סשן יומי",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "plan_tier": user["plan_tier"],
            "plan_name": user["plan_name"],
            "is_admin": is_admin,
            "role": "admin" if is_admin else "user"
        },
        "quota": quota,
        "message": "נרשמת בהצלחה! קיבלת 10 חיפושים לחודש במתנה במנוי חינמי."
    }

@auth_router.post("/login")
def login_endpoint(req: LoginPayload, request: Request, response: Response):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("User-Agent", "")
    try:
        result = login_user(email=req.email, password=req.password, ip=ip, ua=ua, remember_me=req.remember_me)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not result:
        raise HTTPException(status_code=401, detail="אימייל או סיסמה שגויים. נסה שוב או הירשם.")
    user, token, max_age = result
    response.set_cookie(
        key="flight_session_token",
        value=token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        path="/"
    )
    quota = get_user_quota(user)
    is_admin = quota.get("is_admin", False)
    return {
        "success": True,
        "token": token,
        "remember_me": req.remember_me,
        "session_duration": "חודש ימים" if req.remember_me else "סשן יומי",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "plan_tier": user["plan_tier"],
            "plan_name": user["plan_name"],
            "is_admin": is_admin,
            "role": "admin" if is_admin else "user"
        },
        "quota": quota,
        "message": f"ברוך שובך, {user['full_name']}!"
    }

@auth_router.post("/biometric/register")
def biometric_register_endpoint(req: BiometricRegisterPayload, request: Request):
    user = get_current_user(request)
    result = register_biometric_credential(
        user_id=user["id"],
        credential_id=req.credential_id,
        device_name=req.device_name or "סמארטפון (Mobile Device)",
        biometric_type=req.biometric_type or "fingerprint_faceid"
    )
    return {
        "success": True,
        "message": "זיהוי ביומטרי (Face ID / טביעת אצבע) הופעל בהצלחה במכשיר זה!",
        "credential_id": req.credential_id
    }

@auth_router.post("/biometric/login")
def biometric_login_endpoint(req: BiometricLoginPayload, request: Request, response: Response):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("User-Agent", "")
    try:
        result = login_with_biometric(
            credential_id=req.credential_id,
            email=req.email,
            ip=ip,
            ua=ua,
            remember_me=req.remember_me
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not result:
        raise HTTPException(
            status_code=401, 
            detail="זיהוי ביומטרי לא נמצא עבור מכשיר זה. התחבר עם אימייל וסיסמה תחילה כדי להפעיל זיהוי ביומטרי."
        )
    user, token, max_age = result
    response.set_cookie(
        key="flight_session_token",
        value=token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        path="/"
    )
    quota = get_user_quota(user)
    is_admin = quota.get("is_admin", False)
    return {
        "success": True,
        "token": token,
        "remember_me": req.remember_me,
        "session_duration": "חודש ימים" if req.remember_me else "סשן יומי",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "plan_tier": user["plan_tier"],
            "plan_name": user["plan_name"],
            "is_admin": is_admin,
            "role": "admin" if is_admin else "user"
        },
        "quota": quota,
        "message": f"התחברת בהצלחה באמצעות זיהוי ביומטרי! ברוך שובך, {user['full_name']}."
    }

@auth_router.get("/biometric/status")
def biometric_status_endpoint(request: Request, email: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    user = get_current_user_optional(request)
    if user:
        c.execute("SELECT id, credential_id, device_name, biometric_type, created_at FROM biometric_credentials WHERE user_id = ?", (user["id"],))
        rows = c.fetchall()
        conn.close()
        return {"has_biometric": len(rows) > 0, "credentials": [dict(r) for r in rows]}
    elif email:
        c.execute("""
            SELECT b.id, b.credential_id, b.device_name 
            FROM biometric_credentials b
            JOIN users u ON b.user_id = u.id
            WHERE u.email = ?
        """, (email.strip().lower(),))
        rows = c.fetchall()
        conn.close()
        return {"has_biometric": len(rows) > 0, "credentials": [dict(r) for r in rows]}
    conn.close()
    return {"has_biometric": False, "credentials": []}

@auth_router.post("/logout")
def logout_endpoint(request: Request, response: Response):
    token = request.cookies.get("flight_session_token")
    if not token:
        auth_h = request.headers.get("Authorization")
        if auth_h and auth_h.startswith("Bearer "):
            token = auth_h.split(" ", 1)[1].strip()
    if token:
        delete_session(token)
    response.delete_cookie("flight_session_token", path="/")
    return {"success": True, "message": "התנתקת בהצלחה מהמערכת."}

@auth_router.get("/me")
def me_endpoint(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return {"authenticated": False, "user": None, "quota": None}
    quota = get_user_quota(user)
    is_admin = quota.get("is_admin", False)
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "plan_tier": user["plan_tier"],
            "plan_name": user["plan_name"],
            "is_admin": is_admin,
            "role": "admin" if is_admin else "user"
        },
        "quota": quota
    }

class BitPaymentSubmitPayload(BaseModel):
    plan_tier: str
    sender_phone: str
    notes: Optional[str] = ""

@auth_router.post("/bit/submit-payment")
def submit_bit_payment_endpoint(req: BitPaymentSubmitPayload, request: Request):
    user = get_current_user(request)
    if req.plan_tier not in PLANS:
        raise HTTPException(status_code=400, detail="תוכנית מנוי לא מוכרת")
    
    plan = PLANS[req.plan_tier]
    if plan["price"] <= 0:
        raise HTTPException(status_code=400, detail="תוכנית זו הינה ללא תשלום")

    sender_phone = req.sender_phone.strip()
    if not sender_phone or len(sender_phone) < 4:
        raise HTTPException(status_code=400, detail="נא להזין מספר טלפון תקין ממנו בוצעה העברת הביט")

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO bit_payments (
            user_id, user_email, user_name, plan_tier, plan_name,
            amount_ils, sender_phone, target_phone, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '0524845131', 'pending')
    """, (
        user["id"],
        user["email"],
        user["full_name"],
        plan["id"],
        plan["name"],
        plan["price"],
        sender_phone
    ))
    payment_id = c.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "payment_id": payment_id,
        "amount_ils": plan["price"],
        "plan_name": plan["name"],
        "target_phone": "0524845131",
        "sender_phone": sender_phone,
        "status": "pending",
        "message": f"בקשת התשלום בביט על סך {plan['price']} ₪ עבור {plan['name']} נקלטה בהצלחה! המנוי יופעל מיידית לאחר אימות ההעברה ל-0524845131."
    }

@auth_router.get("/bit/my-payments")
def get_my_bit_payments_endpoint(request: Request):
    user = get_current_user(request)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM bit_payments WHERE user_id = ? ORDER BY created_at DESC
    """, (user["id"],))
    rows = c.fetchall()
    conn.close()
    return {"payments": [dict(r) for r in rows]}

@auth_router.get("/plans")
def get_plans_endpoint():
    return {"plans": list(PLANS.values())}

@auth_router.post("/upgrade")
def upgrade_endpoint(req: UpgradePayload, request: Request):
    user = get_current_user(request)
    is_admin = bool(user.get("is_admin") == 1 or user.get("role") == "admin" or user.get("email") == "xeinok2@gmail.com")
    
    if req.plan_tier != "free" and not is_admin:
        # Check if user has an approved bit payment
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, status FROM bit_payments 
            WHERE user_id = ? AND plan_tier = ? AND status = 'approved'
            ORDER BY id DESC LIMIT 1
        """, (user["id"], req.plan_tier))
        approved = c.fetchone()
        conn.close()
        if not approved:
            raise HTTPException(
                status_code=402, 
                detail="נדרש תשלום בביט (Bit) עבור מנוי זה לטלפון 052-4845131 לפני הפעלתו. נא לבצע העברה בביט."
            )

    try:
        updated_quota = upgrade_user_plan(user["id"], req.plan_tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "success": True,
        "message": f"המנוי עודכן בהצלחה ל-{updated_quota['plan_name']}! מכסת החיפושים שלך עודכנה ל-{updated_quota['searches_limit']} חיפושים בחודש.",
        "quota": updated_quota
    }
