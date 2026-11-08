import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Candidate profile table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        cv_filename TEXT,
        raw_text TEXT,
        summary TEXT,
        seniority TEXT,
        target_roles TEXT, -- JSON array
        skills TEXT,       -- JSON array
        years_of_experience REAL DEFAULT 0,
        cv_he_filename TEXT,
        raw_text_he TEXT,
        summary_he TEXT,
        cv_en_filename TEXT,
        raw_text_en TEXT,
        summary_en TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Ensure all columns exist for existing databases
    cursor.execute("PRAGMA table_info(profile)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    for col in ["cv_he_filename", "raw_text_he", "summary_he", "cv_en_filename", "raw_text_en", "summary_en"]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE profile ADD COLUMN {col} TEXT")
    
    # Jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_hash TEXT UNIQUE,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        url TEXT,
        source TEXT,
        description TEXT,
        posted_date TEXT,
        language TEXT DEFAULT 'en', -- 'he' or 'en'
        match_score INTEGER DEFAULT 0,
        matching_skills TEXT, -- JSON array
        missing_skills TEXT,  -- JSON array
        match_reason TEXT,
        cover_letter TEXT,
        status TEXT DEFAULT 'new', -- new, bookmarked, applied, interviewing, rejected, archived
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("PRAGMA table_info(jobs)")
    existing_job_cols = [r[1] for r in cursor.fetchall()]
    if "language" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN language TEXT DEFAULT 'en'")
    if "application_kit" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN application_kit TEXT")
    if "applied_at" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN applied_at TIMESTAMP")
    if "selected_cv" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN selected_cv TEXT")
    if "is_easy_apply" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN is_easy_apply INTEGER DEFAULT 0")
    if "already_applied_source" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN already_applied_source TEXT")
    if "already_applied_at" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN already_applied_at TIMESTAMP")
    if "already_applied_title" not in existing_job_cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN already_applied_title TEXT")
    
    # System & user settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Meta Agent Audits & Improvements table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meta_agent_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        health_score INTEGER DEFAULT 0,
        scrapers_health TEXT,      -- JSON
        match_quality TEXT,        -- JSON
        recommendations TEXT,      -- JSON
        fixes_applied TEXT,        -- JSON
        summary TEXT
    );
    """)

    # Meta Agent Continuous Thoughts & Action Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meta_agent_thoughts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cycle_number INTEGER DEFAULT 1,
        thought_type TEXT, -- 'analysis', 'discovery', 'optimization', 'verification'
        title TEXT,
        thought_content TEXT,
        action_taken TEXT,
        score_delta INTEGER DEFAULT 0
    );
    """)
    
    conn.commit()
    conn.close()

# Ensure database and columns are initialized on module load
init_db()

def detect_language(text: str) -> str:
    """
    Detects whether text is in Hebrew ('he') or English ('en').
    """
    if not text:
        return "en"
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    if hebrew_chars >= 15 or (hebrew_chars + english_chars > 0 and (hebrew_chars / (hebrew_chars + english_chars)) > 0.15):
        return "he"
    return "en"

# Profile helpers
def save_profile(data: Dict[str, Any], lang: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile LIMIT 1")
    row = cursor.fetchone()

    # Determine CV language if not explicitly provided
    raw_text = data.get("raw_text", "")
    cv_lang = lang or detect_language(raw_text)
    
    # Merge existing skills and roles if available
    existing_skills = []
    existing_roles = []
    existing_d = {}
    if row:
        existing_d = dict(row)
        try:
            existing_skills = json.loads(existing_d.get("skills") or "[]")
            existing_roles = json.loads(existing_d.get("target_roles") or "[]")
        except Exception:
            pass

    new_skills = data.get("skills", [])
    merged_skills = sorted(list(set(existing_skills + new_skills)))
    
    new_roles = data.get("target_roles", [])
    merged_roles = list(dict.fromkeys(new_roles + existing_roles))

    target_roles_json = json.dumps(merged_roles)
    skills_json = json.dumps(merged_skills)
    
    full_name = data.get("full_name") or (existing_d.get("full_name") if row else "")
    email = data.get("email") or (existing_d.get("email") if row else "")
    phone = data.get("phone") or (existing_d.get("phone") if row else "")
    seniority = data.get("seniority") or (existing_d.get("seniority") if row else "Mid-Level")
    years_exp = data.get("years_of_experience") or (existing_d.get("years_of_experience") if row else 3.0)
    summary = data.get("summary") or (existing_d.get("summary") if row else "")

    cv_filename = data.get("cv_filename", "")

    cv_he_file = existing_d.get("cv_he_filename") if row else ""
    raw_he = existing_d.get("raw_text_he") if row else ""
    sum_he = existing_d.get("summary_he") if row else ""

    cv_en_file = existing_d.get("cv_en_filename") if row else ""
    raw_en = existing_d.get("raw_text_en") if row else ""
    sum_en = existing_d.get("summary_en") if row else ""

    if cv_lang == "he":
        cv_he_file = cv_filename or cv_he_file
        raw_he = raw_text or raw_he
        sum_he = summary or sum_he
    else:
        cv_en_file = cv_filename or cv_en_file
        raw_en = raw_text or raw_en
        sum_en = summary or sum_en

    if row:
        cursor.execute("""
        UPDATE profile SET
            full_name = ?,
            email = ?,
            phone = ?,
            cv_filename = ?,
            raw_text = ?,
            summary = ?,
            seniority = ?,
            target_roles = ?,
            skills = ?,
            years_of_experience = ?,
            cv_he_filename = ?,
            raw_text_he = ?,
            summary_he = ?,
            cv_en_filename = ?,
            raw_text_en = ?,
            summary_en = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            full_name,
            email,
            phone,
            cv_filename,
            raw_text,
            summary,
            seniority,
            target_roles_json,
            skills_json,
            years_exp,
            cv_he_file,
            raw_he,
            sum_he,
            cv_en_file,
            raw_en,
            sum_en,
            row["id"]
        ))
    else:
        cursor.execute("""
        INSERT INTO profile (
            full_name, email, phone, cv_filename, raw_text, summary,
            seniority, target_roles, skills, years_of_experience,
            cv_he_filename, raw_text_he, summary_he,
            cv_en_filename, raw_text_en, summary_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name, email, phone, cv_filename, raw_text, summary,
            seniority, target_roles_json, skills_json, years_exp,
            cv_he_file, raw_he, sum_he,
            cv_en_file, raw_en, sum_en
        ))
    conn.commit()
    conn.close()

def get_profile() -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["target_roles"] = json.loads(d.get("target_roles") or "[]")
    d["skills"] = json.loads(d.get("skills") or "[]")
    d["has_hebrew_cv"] = bool(d.get("cv_he_filename") or d.get("raw_text_he"))
    d["has_english_cv"] = bool(d.get("cv_en_filename") or d.get("raw_text_en"))
    return d

# Normalization & Duplicate Prevention Helpers
def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    cleaned = re.sub(r'[\(\)\[\]"\'`]', ' ', name)
    cleaned = re.sub(r'\b(בע"?מ|בעמ|ltd|inc|llc|corp|corporation|group|קבוצת|חברת|משאבי אנוש|השמה|חברה לדלק)\b', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    return cleaned

def is_same_or_similar_role(t1: str, t2: str) -> bool:
    t1_lower = t1.lower()
    t2_lower = t2.lower()
    finance_keywords = ["כלכלנ", "economist", "אנליסט", "analyst", "תקציב", "budget", "p&l", "תפעול", "operations", "fp&a", "כספים", "finance", "חשב"]
    t1_matches = {k for k in finance_keywords if k in t1_lower}
    t2_matches = {k for k in finance_keywords if k in t2_lower}
    if t1_matches and t2_matches and (t1_matches & t2_matches):
        return True
    words1 = set(re.findall(r'\w{3,}', t1_lower))
    words2 = set(re.findall(r'\w{3,}', t2_lower))
    if words1 and words2 and len(words1 & words2) >= 2:
        return True
    return False

def check_duplicate_application(company: str, title: str, url: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    # 1. Check exact URL first
    if url and len(url.strip()) > 10:
        cursor.execute("SELECT id, title, company, source, applied_at, status FROM jobs WHERE status = 'applied' AND url = ?", (url.strip(),))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
            
    # 2. Check company + similar title match
    norm_comp = normalize_company_name(company)
    generic_names = ["חברה חסויה", "חברה מובילה", "חסוי", "השמה", "anonymous", "confidential"]
    if not norm_comp or any(g in norm_comp for g in generic_names) or len(norm_comp) < 3:
        conn.close()
        return None
        
    cursor.execute("SELECT id, title, company, source, applied_at, status FROM jobs WHERE status = 'applied'")
    applied_jobs = cursor.fetchall()
    conn.close()
    
    for row in applied_jobs:
        applied_norm_comp = normalize_company_name(row["company"])
        if applied_norm_comp and (norm_comp in applied_norm_comp or applied_norm_comp in norm_comp):
            if is_same_or_similar_role(title, row["title"]):
                return dict(row)
                
    return None

def propagate_application_status(company: str, title: str, source: str, applied_job_id: Optional[int] = None):
    """
    When an application is submitted on any board, propagates 'applied' status
    and sets already_applied_source to all matching postings across all other boards.
    """
    norm_comp = normalize_company_name(company)
    if not norm_comp or len(norm_comp) < 3:
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company, source FROM jobs WHERE status != 'applied'")
    other_jobs = cursor.fetchall()
    
    for row in other_jobs:
        if applied_job_id and row["id"] == applied_job_id:
            continue
        c_norm = normalize_company_name(row["company"])
        if c_norm and (norm_comp in c_norm or c_norm in norm_comp):
            if is_same_or_similar_role(title, row["title"]):
                cursor.execute("""
                    UPDATE jobs 
                    SET status = 'applied',
                        already_applied_source = ?,
                        already_applied_at = CURRENT_TIMESTAMP,
                        already_applied_title = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (source, title, row["id"]))
    conn.commit()
    conn.close()

# Jobs helpers
def insert_or_update_job(job: Dict[str, Any]) -> int:
    conn = get_db()
    cursor = conn.cursor()
    
    job_hash = job.get("job_hash") or f"{job.get('company')}_{job.get('title')}".lower().strip()
    matching_skills = json.dumps(job.get("matching_skills", []))
    missing_skills = json.dumps(job.get("missing_skills", []))

    # Detect job language automatically if not set
    job_desc = job.get("description", "")
    job_title = job.get("title", "")
    job_lang = job.get("language") or detect_language(job_title + " " + job_desc)
    
    # Cross-Platform Duplicate Prevention Check
    prior_app = None
    if job.get("status") != "applied":
        prior_app = check_duplicate_application(job.get("company", ""), job_title, job.get("url", ""))

    status_to_use = "applied" if (job.get("status") == "applied" or prior_app) else job.get("status", "new")
    already_src = job.get("already_applied_source") or (prior_app["source"] if prior_app else None)
    already_at = job.get("already_applied_at") or (prior_app["applied_at"] if prior_app else None)
    already_ttl = job.get("already_applied_title") or (prior_app["title"] if prior_app else None)

    cursor.execute("SELECT id, status, cover_letter, match_score, language FROM jobs WHERE job_hash = ?", (job_hash,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
        UPDATE jobs SET
            title = ?,
            company = ?,
            location = ?,
            url = ?,
            source = ?,
            description = COALESCE(?, description),
            posted_date = COALESCE(?, posted_date),
            language = ?,
            match_score = COALESCE(?, match_score),
            matching_skills = COALESCE(?, matching_skills),
            missing_skills = COALESCE(?, missing_skills),
            match_reason = COALESCE(?, match_reason),
            is_easy_apply = COALESCE(?, is_easy_apply),
            status = CASE WHEN ? = 'applied' THEN 'applied' ELSE status END,
            applied_at = CASE WHEN ? = 'applied' AND applied_at IS NULL THEN CURRENT_TIMESTAMP ELSE applied_at END,
            already_applied_source = COALESCE(?, already_applied_source),
            already_applied_at = COALESCE(?, already_applied_at),
            already_applied_title = COALESCE(?, already_applied_title),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("url"),
            job.get("source"),
            job.get("description"),
            job.get("posted_date"),
            job_lang,
            job.get("match_score"),
            matching_skills,
            missing_skills,
            job.get("match_reason"),
            job.get("is_easy_apply", 0),
            status_to_use,
            status_to_use,
            already_src,
            already_at,
            already_ttl,
            existing["id"]
        ))
        job_id = existing["id"]
    else:
        cursor.execute("""
        INSERT INTO jobs (
            job_hash, title, company, location, url, source, description,
            posted_date, language, match_score, matching_skills, missing_skills,
            match_reason, is_easy_apply, status, applied_at,
            already_applied_source, already_applied_at, already_applied_title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? = 'applied' THEN CURRENT_TIMESTAMP ELSE NULL END, ?, ?, ?)
        """, (
            job_hash,
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("url"),
            job.get("source"),
            job.get("description"),
            job.get("posted_date"),
            job_lang,
            job.get("match_score", 0),
            matching_skills,
            missing_skills,
            job.get("match_reason", ""),
            job.get("is_easy_apply", 0),
            status_to_use,
            status_to_use,
            already_src,
            already_at,
            already_ttl
        ))
        job_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    return job_id

def get_jobs(status: Optional[str] = None, search: Optional[str] = None, lang: Optional[str] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    
    if status and status != "all":
        query += " AND status = ?"
        params.append(status)
        
    if lang and lang != "all":
        query += " AND language = ?"
        params.append(lang)

    if source and source != "all":
        query += " AND source = ?"
        params.append(source)

    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
        
    query += " ORDER BY match_score DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        d["matching_skills"] = json.loads(d.get("matching_skills") or "[]")
        d["missing_skills"] = json.loads(d.get("missing_skills") or "[]")
        results.append(d)
    return results

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["matching_skills"] = json.loads(d.get("matching_skills") or "[]")
    d["missing_skills"] = json.loads(d.get("missing_skills") or "[]")
    return d

def update_job_status(job_id: int, status: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET status = ?, 
            applied_at = CASE WHEN ? = 'applied' AND applied_at IS NULL THEN CURRENT_TIMESTAMP ELSE applied_at END,
            updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (status, status, job_id))
    cursor.execute("SELECT company, title, source FROM jobs WHERE id = ?", (job_id,))
    job_info = cursor.fetchone()
    conn.commit()
    conn.close()

    if status == "applied" and job_info:
        propagate_application_status(job_info["company"], job_info["title"], job_info["source"] or "Manual", applied_job_id=job_id)

def save_cover_letter(job_id: int, cover_letter: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET cover_letter = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (cover_letter, job_id))
    conn.commit()
    conn.close()

def save_application_kit(job_id: int, kit_data: Dict[str, Any], status: Optional[str] = None):
    """Saves the generated AI application kit (CV selection, form fields, answers, cover letter)."""
    conn = get_db()
    cursor = conn.cursor()
    kit_json = json.dumps(kit_data, ensure_ascii=False)
    
    cv_raw = kit_data.get("selected_cv_name") or kit_data.get("selected_cv") or ""
    if isinstance(cv_raw, dict):
        selected_cv = cv_raw.get("selected_cv_name") or ""
    else:
        selected_cv = str(cv_raw)
        
    cover_letter = kit_data.get("cover_letter") or ""

    if status == "applied":
        cursor.execute("""
            UPDATE jobs 
            SET application_kit = ?,
                selected_cv = ?,
                cover_letter = COALESCE(NULLIF(?, ''), cover_letter),
                status = 'applied',
                applied_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (kit_json, selected_cv, cover_letter, job_id))
    else:
        cursor.execute("""
            UPDATE jobs 
            SET application_kit = ?,
                selected_cv = ?,
                cover_letter = COALESCE(NULLIF(?, ''), cover_letter),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (kit_json, selected_cv, cover_letter, job_id))
        
    cursor.execute("SELECT company, title, source FROM jobs WHERE id = ?", (job_id,))
    job_info = cursor.fetchone()
    conn.commit()
    conn.close()

    if status == "applied" and job_info:
        propagate_application_status(job_info["company"], job_info["title"], job_info["source"] or "AI Form Agent", applied_job_id=job_id)

def get_application_kit(job_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the application kit for a job."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT application_kit, selected_cv, cover_letter, applied_at, status FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row["application_kit"]:
        return None
    try:
        data = json.loads(row["application_kit"])
        data["selected_cv"] = row["selected_cv"] or data.get("selected_cv_name")
        data["applied_at"] = row["applied_at"]
        data["status"] = row["status"]
        return data
    except Exception:
        return None

def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def save_meta_audit(data: Dict[str, Any]) -> int:
    """Saves a meta-agent audit report and recommendations."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meta_agent_audits (health_score, scrapers_health, match_quality, recommendations, fixes_applied, summary)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("health_score", 0),
        json.dumps(data.get("scrapers_health", {}), ensure_ascii=False),
        json.dumps(data.get("match_quality", {}), ensure_ascii=False),
        json.dumps(data.get("recommendations", []), ensure_ascii=False),
        json.dumps(data.get("fixes_applied", []), ensure_ascii=False),
        data.get("summary", "")
    ))
    audit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return audit_id

def get_latest_meta_audit() -> Optional[Dict[str, Any]]:
    """Retrieves the most recent meta-agent audit."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meta_agent_audits ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for field in ["scrapers_health", "match_quality", "recommendations", "fixes_applied"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = {}
        else:
            d[field] = [] if field in ["recommendations", "fixes_applied"] else {}
    return d

def get_all_meta_audits(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves audit history."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meta_agent_audits ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        for field in ["scrapers_health", "match_quality", "recommendations", "fixes_applied"]:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    d[field] = {}
            else:
                d[field] = [] if field in ["recommendations", "fixes_applied"] else {}
        results.append(d)
    return results

def save_meta_thought(thought_type: str, title: str, thought_content: str, action_taken: str = "", score_delta: int = 0, cycle_number: int = 1) -> int:
    """Saves an autonomous thinking and improvement event."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meta_agent_thoughts (cycle_number, thought_type, title, thought_content, action_taken, score_delta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cycle_number, thought_type, title, thought_content, action_taken, score_delta))
    thought_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thought_id

def get_recent_meta_thoughts(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves recent autonomous thoughts and actions."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meta_agent_thoughts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
