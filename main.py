import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.config import UPLOAD_DIR, settings
from core.db import (
    init_db, get_profile, save_profile, get_jobs, get_job_by_id,
    update_job_status, save_cover_letter, get_setting, set_setting,
    insert_or_update_job, detect_language, get_application_kit
)
from core.cv_parser import extract_text_from_pdf, parse_and_save_cv
from core.matcher import calculate_match, generate_cover_letter
from core.scrapers.aggregator import run_job_search
from core.form_agent import build_application_kit, execute_job_submission, select_best_cv
from core.linkedin_session import get_linkedin_status, save_li_at_cookie, launch_login_browser
from core.linkedin_easy_apply import apply_to_linkedin_job, SCREENSHOTS_DIR
from core.meta_agent import MetaAgent
from core.autonomous_optimizer import optimizer_instance
from core.salary_estimator import estimate_job_salary
from core.interview_coach import generate_interview_prep
from core.whatsapp_digest import generate_whatsapp_digest
from core.skill_booster import analyze_skill_gaps
from survey_agent.config import SURVEY_SCREENSHOTS_DIR
from survey_agent.db import (
    get_surveys_summary, get_all_surveys, get_survey_profile,
    save_survey_profile, get_setting as get_survey_setting,
    set_setting as set_survey_setting
)
from survey_agent.runner import run_survey_cycle, solve_direct_url
from flight_agent.router import router as flight_router
from flight_agent.auth import auth_router
from flight_agent.admin import admin_router

# Initialize SQLite database
init_db()

app = FastAPI(title="Smart Job Hunter AI Agent")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/static/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")
app.mount("/static/survey_screenshots", StaticFiles(directory=str(SURVEY_SCREENSHOTS_DIR)), name="survey_screenshots")

# Mount Flight Agent Router
app.include_router(flight_router)
app.include_router(auth_router)
app.include_router(admin_router)

# Models for request validation
class SurveySettingsRequest(BaseModel):
    gmail_user: Optional[str] = None
    gmail_app_password: Optional[str] = None
    target_sender: Optional[str] = None
    headless: Optional[bool] = None

class SurveyProfileRequest(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    age: Optional[int] = None
    city: Optional[str] = None
    district: Optional[str] = None
    marital_status: Optional[str] = None
    children_count: Optional[int] = None
    education: Optional[str] = None
    degree_field: Optional[str] = None
    employment_status: Optional[str] = None
    occupation: Optional[str] = None
    monthly_income: Optional[str] = None
    religion_sector: Optional[str] = None
    car_owner: Optional[str] = None
    smoker: Optional[str] = None

class DirectSurveyRequest(BaseModel):
    url: str
    headless: Optional[bool] = False

class StatusUpdateRequest(BaseModel):
    status: str

class CoverLetterRequest(BaseModel):
    language: Optional[str] = "auto" # 'auto', 'he', or 'en'

class SubmitApplicationRequest(BaseModel):
    answers: Dict[str, Any] = {}

class InspectUrlRequest(BaseModel):
    url: str

class LinkedInCookieRequest(BaseModel):
    li_at: str

class EasyApplyRequest(BaseModel):
    auto_submit: bool = True
    headless: bool = False

class OptimizeRequest(BaseModel):
    fix_ids: Optional[List[str]] = None

class ToggleAutonomousRequest(BaseModel):
    enabled: Optional[bool] = None
    interval_seconds: Optional[int] = None

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    search_location: Optional[str] = None
    linkedin_li_at: Optional[str] = None

class ManualJobRequest(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Israel"
    url: Optional[str] = ""
    description: str

class ProfileUpdateRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    seniority: str
    target_roles: List[str]
    skills: List[str]
    years_of_experience: float
    summary: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard loading... please check templates/index.html</h1>")


@app.get("/flights", response_class=HTMLResponse)
async def serve_flights():
    flights_file = TEMPLATES_DIR / "flights.html"
    if flights_file.exists():
        return HTMLResponse(content=flights_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Flight Agent loading... please check templates/flights.html</h1>")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    admin_file = TEMPLATES_DIR / "admin.html"
    if admin_file.exists():
        return HTMLResponse(content=admin_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Admin Dashboard loading... please check templates/admin.html</h1>")


@app.get("/api/profile")
async def api_get_profile():
    profile = get_profile()
    return profile or {}


@app.post("/api/profile/upload-cv")
async def api_upload_cv(
    file: Optional[UploadFile] = File(None),
    pasted_text: Optional[str] = Form(None),
    lang: Optional[str] = Form("auto")
):
    raw_text = ""
    filename = ""

    if file and file.filename:
        filename = file.filename
        save_path = UPLOAD_DIR / filename
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if filename.lower().endswith(".pdf"):
            raw_text = extract_text_from_pdf(save_path)
        else:
            raw_text = save_path.read_text(encoding="utf-8", errors="ignore")
    elif pasted_text:
        raw_text = pasted_text
        filename = f"pasted_cv_{lang}.txt"
    else:
        raise HTTPException(status_code=400, detail="Please upload a PDF/TXT file or paste CV text.")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the provided CV.")

    target_lang = None if lang == "auto" else lang
    profile = parse_and_save_cv(raw_text, filename, lang=target_lang)

    # Recalculate match scores for all existing jobs with the updated profile
    existing_jobs = get_jobs(status="all")
    for job in existing_jobs:
        score, matching, missing, reason = calculate_match(job["title"], job["description"], profile)
        job["match_score"] = score
        job["matching_skills"] = matching
        job["missing_skills"] = missing
        job["match_reason"] = reason
        insert_or_update_job(job)

    return {"status": "success", "profile": get_profile(), "detected_lang": profile.get("language")}


@app.post("/api/profile/update")
async def api_update_profile(req: ProfileUpdateRequest):
    data = req.dict()
    curr = get_profile() or {}
    data["raw_text"] = curr.get("raw_text", "")
    data["cv_filename"] = curr.get("cv_filename", "")
    save_profile(data)
    return {"status": "success", "profile": get_profile()}


@app.get("/api/jobs")
async def api_get_jobs(
    status: Optional[str] = "all",
    search: Optional[str] = None,
    lang: Optional[str] = "all",
    source: Optional[str] = "all"
):
    jobs = get_jobs(status=status, search=search, lang=lang, source=source)
    for j in jobs:
        j["salary_estimate"] = estimate_job_salary(j.get("title", ""), j.get("description", ""), j.get("company", ""))
    return jobs


@app.post("/api/jobs/scan")
async def api_scan_jobs():
    results = run_job_search()
    return results


@app.post("/api/jobs/{job_id}/status")
async def api_update_status(job_id: int, req: StatusUpdateRequest):
    update_job_status(job_id, req.status)
    return {"status": "success", "job_id": job_id, "new_status": req.status}


@app.post("/api/jobs/{job_id}/cover-letter")
async def api_generate_cover_letter(job_id: int, req: CoverLetterRequest):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = get_profile() or {}
    letter = generate_cover_letter(job, profile, language=req.language)
    save_cover_letter(job_id, letter)
    return {"status": "success", "cover_letter": letter, "applied_language": req.language}


@app.post("/api/jobs/manual-add")
async def api_manual_add_job(req: ManualJobRequest):
    profile = get_profile() or {}
    score, matching, missing, reason = calculate_match(req.title, req.description, profile)
    job_lang = detect_language(req.title + " " + req.description)

    job_dict = {
        "title": req.title,
        "company": req.company,
        "location": req.location or "Israel",
        "url": req.url or "",
        "source": "Manual",
        "description": req.description,
        "posted_date": "Today",
        "language": job_lang,
        "match_score": score,
        "matching_skills": matching,
        "missing_skills": missing,
        "match_reason": reason
    }
    job_id = insert_or_update_job(job_dict)
    return {"status": "success", "job_id": job_id, "match_score": score, "language": job_lang}


@app.get("/api/jobs/{job_id}/application-kit")
async def api_get_application_kit(job_id: int):
    try:
        kit = build_application_kit(job_id)
        return kit
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/submit")
async def api_submit_application(job_id: int, req: SubmitApplicationRequest):
    try:
        res = execute_job_submission(job_id, req.answers)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cv/download/{filename}")
async def api_download_cv(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename, media_type="application/pdf")


@app.post("/api/applications/inspect-url")
async def api_inspect_url(req: InspectUrlRequest):
    import requests
    from bs4 import BeautifulSoup
    from core.db import get_db

    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE url = ? OR url LIKE ? LIMIT 1", (url, f"%{url}%"))
    row = cursor.fetchone()
    conn.close()

    if row:
        job_id = row["id"]
    else:
        title = "Job Opportunity"
        company = "Target Company"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=8)
            soup = BeautifulSoup(r.text, "html.parser")
            t_elem = soup.find(["h1", "title", "h2"], class_=lambda c: c and any(k in str(c).lower() for k in ["title", "job", "position"]))
            if t_elem:
                title = t_elem.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)
        except Exception:
            pass

        profile = get_profile() or {}
        job_lang = detect_language(title)
        score, matching, missing, reason = calculate_match(title, "", profile)

        job_dict = {
            "title": title[:100],
            "company": company,
            "location": "Israel",
            "url": url,
            "source": "Custom URL",
            "description": f"Imported job posting from {url}",
            "posted_date": "Today",
            "language": job_lang,
            "match_score": score,
            "matching_skills": matching,
            "missing_skills": missing,
            "match_reason": reason
        }
        job_id = insert_or_update_job(job_dict)

    kit = build_application_kit(job_id)
    return kit


@app.get("/api/linkedin/status")
async def api_get_linkedin_status():
    return get_linkedin_status()


@app.post("/api/linkedin/login-window")
async def api_open_linkedin_login():
    import threading
    t = threading.Thread(target=launch_login_browser, daemon=True)
    t.start()
    return {"status": "success", "message": "חלון התחברות ל-LinkedIn נפתח בדפדפן Chrome. התחבר לחשבונך והחלון יתעדכן."}


@app.post("/api/linkedin/save-cookie")
async def api_save_linkedin_cookie(req: LinkedInCookieRequest):
    save_li_at_cookie(req.li_at)
    return {"status": "success", "message": "עוגיית li_at נשמרה בהצלחה"}


@app.post("/api/jobs/{job_id}/easy-apply")
async def api_trigger_easy_apply(job_id: int, req: EasyApplyRequest):
    res = apply_to_linkedin_job(job_id, auto_submit=req.auto_submit, headless=req.headless)
    return res


@app.get("/api/settings")
async def api_get_settings():
    key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    masked_key = (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("Configured" if key else "")
    loc = get_setting("SEARCH_LOCATION", "Israel")
    li_cookie = get_setting("LINKEDIN_LI_AT", "")
    masked_li = (li_cookie[:4] + "..." + li_cookie[-4:]) if len(li_cookie) > 8 else ("Configured" if li_cookie else "")
    li_status = get_linkedin_status()
    return {
        "has_gemini_key": bool(key),
        "masked_key": masked_key,
        "search_location": loc,
        "has_linkedin_cookie": bool(li_cookie),
        "masked_linkedin_cookie": masked_li,
        "linkedin_connected": li_status.get("is_connected", False)
    }


@app.post("/api/settings")
async def api_save_settings(req: SettingsUpdateRequest):
    if req.gemini_api_key is not None and req.gemini_api_key.strip():
        set_setting("GEMINI_API_KEY", req.gemini_api_key.strip())
    if req.search_location is not None:
        set_setting("SEARCH_LOCATION", req.search_location.strip())
    if req.linkedin_li_at is not None and req.linkedin_li_at.strip():
        save_li_at_cookie(req.linkedin_li_at.strip())
    return {"status": "success"}


# ==========================================
# Meta-Agent / Agent Optimizer Endpoints
# ==========================================

@app.get("/api/meta-agent/status")
async def api_meta_agent_status():
    from core.db import get_latest_meta_audit
    latest = get_latest_meta_audit()
    if not latest:
        # Run initial audit if none exists
        agent = MetaAgent()
        latest = agent.run_audit()
    return latest


@app.post("/api/meta-agent/audit")
async def api_meta_agent_audit():
    agent = MetaAgent()
    audit_data = agent.run_audit()
    return audit_data


@app.post("/api/meta-agent/optimize")
async def api_meta_agent_optimize(req: OptimizeRequest):
    agent = MetaAgent()
    result = agent.apply_optimization(fix_ids=req.fix_ids)
    return result


@app.get("/api/meta-agent/thoughts")
async def api_meta_agent_thoughts():
    """Returns the continuous autonomous optimizer thoughts, status, and recent actions."""
    return optimizer_instance.get_status()


@app.post("/api/meta-agent/toggle-autonomous")
async def api_meta_agent_toggle_autonomous(req: ToggleAutonomousRequest):
    """Enables or disables continuous autonomous background optimization."""
    if req.enabled is not None:
        set_setting("AUTONOMOUS_OPTIMIZER_ENABLED", "true" if req.enabled else "false")
        if req.enabled:
            optimizer_instance.start()
        else:
            optimizer_instance.stop()

    if req.interval_seconds is not None and req.interval_seconds >= 60:
        optimizer_instance.interval_seconds = req.interval_seconds
        set_setting("AUTONOMOUS_OPTIMIZER_INTERVAL", str(req.interval_seconds))

    return optimizer_instance.get_status()


@app.post("/api/meta-agent/trigger-cycle")
async def api_meta_agent_trigger_cycle(background_tasks: BackgroundTasks):
    """Triggers an autonomous cycle in the background immediately."""
    background_tasks.add_task(optimizer_instance.run_single_autonomous_cycle)
    return {"status": "success", "message": "סבב שיפור וחשיבה אוטונומי הופעל ברקע"}


# ==========================================
# Meta-Agent Conceived & Deployed Features
# ==========================================

@app.get("/api/meta-agent/features")
async def api_get_conceived_features():
    """Returns the catalog of new features conceived and built by the Meta-Agent."""
    from core.autonomous_optimizer import CONCEIVED_FEATURES
    return CONCEIVED_FEATURES


@app.get("/api/jobs/{job_id}/interview-prep")
async def api_get_interview_prep(job_id: int):
    """Feature 1: Personalized AI Interview Prep & Question Predictor."""
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = get_profile() or {}
    prep_kit = generate_interview_prep(job, profile)
    return prep_kit


@app.get("/api/digest/whatsapp")
async def api_get_whatsapp_digest(min_score: int = 70, limit: int = 5):
    """Feature 2: WhatsApp-formatted daily job digest with 1-click share."""
    return generate_whatsapp_digest(min_score=min_score, limit=limit)


@app.get("/api/insights/skill-gaps")
async def api_get_skill_gaps():
    """Feature 3: Market Skill Gap Analysis & Learning Roadmap."""
    return analyze_skill_gaps()


# ==========================================
# Polyeda / Panel View Survey Agent Endpoints
# ==========================================

@app.get("/api/surveys/status")
async def api_get_survey_status():
    """Returns survey agent connection status, summary, and settings."""
    summary = get_surveys_summary()
    user = get_survey_setting("GMAIL_USER", os.getenv("GMAIL_USER", ""))
    pwd = get_survey_setting("GMAIL_APP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD", ""))
    masked_user = (user[:3] + "..." + user[user.find("@"):]) if "@" in user else ("Configured" if user else "")
    has_pwd = bool(pwd and len(pwd.strip()) > 5)
    sender = get_survey_setting("TARGET_SENDER", os.getenv("SURVEY_SENDER", "panelview@polyeda.com"))
    headless = get_survey_setting("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    profile = get_survey_profile()

    return {
        "is_configured": bool(user and has_pwd),
        "gmail_user": masked_user,
        "has_app_password": has_pwd,
        "target_sender": sender,
        "headless": headless,
        "summary": summary,
        "profile": profile
    }


@app.get("/api/surveys/list")
async def api_get_surveys_list():
    """Returns list of all detected & processed surveys."""
    return get_all_surveys(limit=50)


@app.post("/api/surveys/check")
async def api_check_and_solve_surveys(background_tasks: BackgroundTasks):
    """Triggers Gmail check and survey solving cycle in background."""
    headless = get_survey_setting("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    background_tasks.add_task(run_survey_cycle, headless=headless)
    return {"status": "success", "message": "סריקת מיילים מ-panelview@polyeda.com והפעלת סוכן המילוי הופעלה ברקע!"}


@app.post("/api/surveys/solve-url")
async def api_solve_direct_url(req: DirectSurveyRequest, background_tasks: BackgroundTasks):
    """Solves a direct survey URL using Playwright."""
    background_tasks.add_task(solve_direct_url, url=req.url, headless=req.headless)
    return {"status": "success", "message": "סוכן Playwright הופעל למילוי הסקר מקישור ישיר!"}


@app.get("/api/surveys/profile")
async def api_get_survey_profile():
    return get_survey_profile()


@app.post("/api/surveys/profile")
async def api_save_survey_profile(req: SurveyProfileRequest):
    save_survey_profile(req.dict(exclude_unset=True))
    return {"status": "success", "profile": get_survey_profile()}


@app.post("/api/surveys/settings")
async def api_save_survey_settings(req: SurveySettingsRequest):
    if req.gmail_user is not None and req.gmail_user.strip():
        set_survey_setting("GMAIL_USER", req.gmail_user.strip())
    if req.gmail_app_password is not None and req.gmail_app_password.strip():
        set_survey_setting("GMAIL_APP_PASSWORD", req.gmail_app_password.strip())
    if req.target_sender is not None and req.target_sender.strip():
        set_survey_setting("TARGET_SENDER", req.target_sender.strip())
    if req.headless is not None:
        set_survey_setting("PLAYWRIGHT_HEADLESS", "true" if req.headless else "false")

    return {"status": "success", "message": "הגדרות סוכן הסקרים נשמרו בהצלחה!"}


@app.on_event("startup")
async def startup_event():
    """Start autonomous background optimizer on server startup."""
    optimizer_instance.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks gracefully on shutdown."""
    optimizer_instance.stop()


if __name__ == "__main__":
    import uvicorn
    print(f"[*] Starting Smart Job Hunter AI Dashboard on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
