import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from survey_agent.config import SURVEY_DB_PATH

def get_db():
    conn = sqlite3.connect(SURVEY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Table for detected & processed surveys
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS surveys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE,
        sender TEXT,
        subject TEXT,
        received_at TEXT,
        survey_url TEXT NOT NULL,
        reward_points INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending', -- pending, running, completed, screened_out, failed
        pages_completed INTEGER DEFAULT 0,
        error_message TEXT,
        screenshot_path TEXT,
        logs TEXT, -- JSON array of step logs
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Demographic profile table for survey screening & consistency
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT DEFAULT 'ליאור אזולאי',
        gender TEXT DEFAULT 'נקבה', -- זכר / נקבה
        birth_year INTEGER DEFAULT 1999,
        age INTEGER DEFAULT 27,
        city TEXT DEFAULT 'תל אביב - יפו',
        district TEXT DEFAULT 'מרכז / תל אביב',
        marital_status TEXT DEFAULT 'רווקה', -- רווק/ה, נשוי/אה
        children_count INTEGER DEFAULT 0,
        education TEXT DEFAULT 'תואר ראשון (.B.A)',
        degree_field TEXT DEFAULT 'כלכלה וניהול',
        employment_status TEXT DEFAULT 'שכירה במשרה מלאה',
        occupation TEXT DEFAULT 'כלכלנית / אנליסטית פיננסית',
        monthly_income TEXT DEFAULT 'ממוצעת (18,000 - 22,000 ₪)',
        religion_sector TEXT DEFAULT 'חילונית', -- חילוני, מסורתי, דתי, חרדי
        car_owner TEXT DEFAULT 'כן',
        smoker TEXT DEFAULT 'לא',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # App settings table (email credentials, check interval, etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Initialize default profile row if empty
    cursor.execute("SELECT count(*) as count FROM survey_profile")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO survey_profile (
            full_name, gender, birth_year, age, city, district,
            marital_status, children_count, education, degree_field,
            employment_status, occupation, monthly_income, religion_sector
        ) VALUES (
            'ליאור אזולאי', 'נקבה', 1999, 27, 'תל אביב - יפו', 'מרכז / תל אביב',
            'רווקה', 0, 'תואר ראשון (.B.A)', 'כלכלה וניהול',
            'שכירה במשרה מלאה', 'כלכלנית / אנליסטית פיננסית',
            'ממוצעת (18,000 - 22,000 ₪)', 'חילונית'
        )
        """)

    conn.commit()
    conn.close()

# Initialize immediately on import
init_db()

def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM survey_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO survey_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_survey_profile() -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survey_profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def save_survey_profile(data: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE survey_profile SET
        full_name = COALESCE(?, full_name),
        gender = COALESCE(?, gender),
        birth_year = COALESCE(?, birth_year),
        age = COALESCE(?, age),
        city = COALESCE(?, city),
        district = COALESCE(?, district),
        marital_status = COALESCE(?, marital_status),
        children_count = COALESCE(?, children_count),
        education = COALESCE(?, education),
        degree_field = COALESCE(?, degree_field),
        employment_status = COALESCE(?, employment_status),
        occupation = COALESCE(?, occupation),
        monthly_income = COALESCE(?, monthly_income),
        religion_sector = COALESCE(?, religion_sector),
        car_owner = COALESCE(?, car_owner),
        smoker = COALESCE(?, smoker),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = (SELECT id FROM survey_profile ORDER BY id DESC LIMIT 1)
    """, (
        data.get("full_name"), data.get("gender"), data.get("birth_year"),
        data.get("age"), data.get("city"), data.get("district"),
        data.get("marital_status"), data.get("children_count"),
        data.get("education"), data.get("degree_field"),
        data.get("employment_status"), data.get("occupation"),
        data.get("monthly_income"), data.get("religion_sector"),
        data.get("car_owner"), data.get("smoker")
    ))
    conn.commit()
    conn.close()

def insert_or_get_survey(survey_data: Dict[str, Any]) -> int:
    """Inserts a new survey or returns existing survey ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    msg_id = survey_data.get("msg_id") or survey_data.get("survey_url")
    cursor.execute("SELECT id FROM surveys WHERE msg_id = ? OR survey_url = ?", (msg_id, survey_data.get("survey_url")))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    cursor.execute("""
    INSERT INTO surveys (msg_id, sender, subject, received_at, survey_url, reward_points, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        msg_id,
        survey_data.get("sender", "panelview@polyeda.com"),
        survey_data.get("subject", "הזמנה לסקר חדש"),
        survey_data.get("received_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        survey_data.get("survey_url"),
        survey_data.get("reward_points", 0),
        survey_data.get("status", "pending")
    ))
    survey_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return survey_id

def update_survey_status(survey_id: int, status: str, pages_completed: int = 0,
                         error_message: str = "", screenshot_path: str = "",
                         reward_points: Optional[int] = None, logs: Optional[List[str]] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    logs_json = json.dumps(logs or [], ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if status == "completed":
        cursor.execute("""
        UPDATE surveys SET
            status = ?,
            pages_completed = ?,
            error_message = ?,
            screenshot_path = COALESCE(NULLIF(?, ''), screenshot_path),
            reward_points = COALESCE(?, reward_points),
            logs = ?,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, pages_completed, error_message, screenshot_path, reward_points, logs_json, survey_id))
    else:
        cursor.execute("""
        UPDATE surveys SET
            status = ?,
            pages_completed = ?,
            error_message = ?,
            screenshot_path = COALESCE(NULLIF(?, ''), screenshot_path),
            reward_points = COALESCE(?, reward_points),
            logs = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, pages_completed, error_message, screenshot_path, reward_points, logs_json, survey_id))

    conn.commit()
    conn.close()

def get_all_surveys(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM surveys ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("logs"):
            try:
                d["logs"] = json.loads(d["logs"])
            except Exception:
                d["logs"] = []
        else:
            d["logs"] = []
        res.append(d)
    return res

def get_survey_by_id(survey_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("logs"):
        try:
            d["logs"] = json.loads(d["logs"])
        except Exception:
            d["logs"] = []
    else:
        d["logs"] = []
    return d

def get_surveys_summary() -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) as total FROM surveys")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT count(*) as completed FROM surveys WHERE status = 'completed'")
    completed = cursor.fetchone()["completed"]

    cursor.execute("SELECT count(*) as screened_out FROM surveys WHERE status = 'screened_out'")
    screened_out = cursor.fetchone()["screened_out"]

    cursor.execute("SELECT count(*) as pending FROM surveys WHERE status = 'pending'")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COALESCE(SUM(reward_points), 0) as total_points FROM surveys WHERE status = 'completed'")
    total_points = cursor.fetchone()["total_points"]

    conn.close()
    return {
        "total": total,
        "completed": completed,
        "screened_out": screened_out,
        "pending": pending,
        "total_points": total_points
    }
