import os
import re
import json
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from core.config import UPLOAD_DIR, BASE_DIR
from core.db import get_profile, get_job_by_id, get_setting, save_application_kit, detect_language
from core.matcher import generate_cover_letter


def select_best_cv(job: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Selects whether to submit the Hebrew or English CV based on job language,
    company profile, and post context.
    """
    job_title = job.get("title", "")
    job_desc = job.get("description", "")
    job_lang = job.get("language") or detect_language(job_title + " " + job_desc)

    he_file = profile.get("cv_he_filename") or "קורות חיים - ליאור אזולאי.pdf"
    en_file = profile.get("cv_en_filename") or "Lior_Azulay_CV.pdf"

    he_path = UPLOAD_DIR / he_file
    en_path = UPLOAD_DIR / en_file

    # Fallbacks if files are named slightly differently
    if not he_path.exists():
        for f in UPLOAD_DIR.glob("*.pdf"):
            if "hebrew" in f.name.lower() or "קורות" in f.name:
                he_path = f
                he_file = f.name
                break

    if not en_path.exists():
        for f in UPLOAD_DIR.glob("*.pdf"):
            if "lior" in f.name.lower() and "קורות" not in f.name:
                en_path = f
                en_file = f.name
                break

    if job_lang == "he":
        return {
            "selected_cv_name": he_file,
            "selected_cv_file": str(he_path),
            "language": "he",
            "file_exists": he_path.exists(),
            "file_size_kb": round(he_path.stat().st_size / 1024, 1) if he_path.exists() else 0,
            "rationale": "המשרה פורסמה בעברית בארגון מקומי בישראל. נבחר טופס קורות החיים בעברית כדי להדגיש את תואר ה-.B.A בכלכלה וניהול, השירות בחיל האוויר, והניסיון המעשי בשוק המקומי."
        }
    else:
        return {
            "selected_cv_name": en_file,
            "selected_cv_file": str(en_path),
            "language": "en",
            "file_exists": en_path.exists(),
            "file_size_kb": round(en_path.stat().st_size / 1024, 1) if en_path.exists() else 0,
            "rationale": "The position is listed in English. Selected the English CV (Lior_Azulay_CV.pdf) tailored for international standards, highlighting quantitative financial analysis, cash flow management, Excel modeling, and ERP systems."
        }


def extract_form_schema(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Inspects the job URL / source to extract real or representative form fields.
    Supports Greenhouse API questions, HTML scraping, and comprehensive default fields.
    """
    job_url = job.get("url", "")
    source = job.get("source", "")
    company = job.get("company", "")
    job_title = job.get("title", "")
    job_lang = job.get("language") or "en"

    # 1. Greenhouse Board API inspection
    if "greenhouse.io" in job_url or source == "Greenhouse":
        try:
            # Extract board_token and job_id from URL
            # e.g. https://boards.greenhouse.io/appsflyer/jobs/8816205002
            # or https://boards-api.greenhouse.io/v1/boards/appsflyer/jobs/8816205002
            m = re.search(r'boards(?:\-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)/jobs/(\d+)', job_url)
            if m:
                board_token, jid = m.group(1), m.group(2)
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{jid}?questions=true"
                r = requests.get(api_url, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    questions = data.get("questions", [])
                    if questions:
                        unified_fields = []
                        for q in questions:
                            label = q.get("label", "")
                            req = q.get("required", False)
                            fields_list = q.get("fields", [])
                            name = fields_list[0].get("name") if fields_list else label.lower().replace(" ", "_")
                            f_type = fields_list[0].get("type", "input_text") if fields_list else "input_text"
                            options = []
                            if f_type in ["multi_value_single_select", "multi_value_multi_select"]:
                                options = [opt.get("label") for opt in fields_list[0].get("values", [])]

                            unified_fields.append({
                                "name": name,
                                "label": label,
                                "type": "select" if options else ("textarea" if "cover" in name or "desc" in name else "text"),
                                "required": req,
                                "options": options,
                                "description": q.get("description") or ""
                            })
                        if unified_fields:
                            return unified_fields
        except Exception as e:
            print(f"[Greenhouse Schema Extraction Error]: {e}")

    # 2. Standard smart fields tailored for the role and language
    if job_lang == "he":
        return [
            {"name": "first_name", "label": "שם פרטי", "type": "text", "required": True},
            {"name": "last_name", "label": "שם משפחה", "type": "text", "required": True},
            {"name": "email", "label": "כתובת אימייל", "type": "email", "required": True},
            {"name": "phone", "label": "מספר טלפון", "type": "tel", "required": True},
            {"name": "city", "label": "עיר מגורים", "type": "text", "required": False},
            {"name": "linkedin", "label": "פרופיל LinkedIn", "type": "url", "required": False},
            {"name": "current_company", "label": "מקום עבודה נוכחי / אחרון", "type": "text", "required": True},
            {"name": "current_title", "label": "תפקיד נוכחי / אחרון", "type": "text", "required": True},
            {"name": "salary_expectation", "label": "ציפיות שכר (ברוטו לחודש)", "type": "text", "required": True},
            {"name": "notice_period", "label": "זמינות לתחילת עבודה", "type": "text", "required": True},
            {"name": "work_authorization", "label": "האם הנך בעל/ת אזרחות ישראלית / אישור עבודה חוקי?", "type": "select", "options": ["כן", "לא"], "required": True},
            {"name": "why_us", "label": f"מדוע את/ה מעוניין/ת להצטרף ל-{company}?", "type": "textarea", "required": False},
            {"name": "relevant_experience", "label": "תאר/י בקצרה את הניסיון המעשי שלך בניתוח פיננסי, בקרת תקציב ואקסל מתקדם", "type": "textarea", "required": True}
        ]
    else:
        return [
            {"name": "first_name", "label": "First Name", "type": "text", "required": True},
            {"name": "last_name", "label": "Last Name", "type": "text", "required": True},
            {"name": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "phone", "label": "Phone Number", "type": "tel", "required": True},
            {"name": "location", "label": "Location / City", "type": "text", "required": False},
            {"name": "linkedin", "label": "LinkedIn Profile URL", "type": "url", "required": False},
            {"name": "current_company", "label": "Most Recent Company", "type": "text", "required": True},
            {"name": "current_title", "label": "Most Recent Job Title", "type": "text", "required": True},
            {"name": "salary_expectation", "label": "Salary Expectations (Monthly Gross ILS)", "type": "text", "required": True},
            {"name": "notice_period", "label": "Notice Period / Earliest Start Date", "type": "text", "required": True},
            {"name": "work_authorization", "label": "Are you legally authorized to work in Israel without sponsorship?", "type": "select", "options": ["Yes", "No"], "required": True},
            {"name": "why_company", "label": f"Why are you interested in joining {company}?", "type": "textarea", "required": False},
            {"name": "relevant_experience", "label": "Briefly describe your practical experience with financial analysis, Excel modeling, and ERP systems", "type": "textarea", "required": True}
        ]


def fill_form_fields_with_ai(fields: List[Dict[str, Any]], job: Dict[str, Any], profile: Dict[str, Any], cv_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Uses Google AI Pro (Gemini 3.8 Flash) to inspect each form field, question,
    and option, formulating accurate answers tailored to Lior Azulay's true profile.
    """
    api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    job_lang = cv_info.get("language", "en")
    cand_name = profile.get("full_name", "ליאור אזולאי")
    if "|" in cand_name:
        cand_name = cand_name.split("|")[0].strip() if job_lang == "he" else cand_name.split("|")[1].strip()

    prompt = f"""
You are an expert autonomous job application agent acting on behalf of candidate Lior Azulay.
You need to complete an official job application form for the position of "{job.get('title')}" at "{job.get('company')}".

Candidate Profile:
- Full Name: {cand_name} (Lior Azulay / ליאור אזולאי)
- Email: {profile.get('email', 'liorazulaywork@gmail.com')}
- Phone: {profile.get('phone', '050-345-0447')}
- LinkedIn: https://linkedin.com/in/lior-azulay-bb8242430
- City / Location: Ashkelon, Israel (אשקלון, ישראל)
- Academic Background: B.A. in Economics & Management (בוגרת תואר ראשון בכלכלה וניהול, המכללה האקדמית אשקלון)
- Actual Recent Job: Business Operations & Financial Analyst at "Hai Bamim", Ashkelon (2021-Present)
  * Managed day-to-day accounts, cash flow management, budget tracking, P&L monitoring, pricing analysis, supplier negotiations in Excel.
- Military Service: HR NCO, Israeli Air Force (2018-2020) with daily operational use of SAP & ERP systems.
- Technical Skills: Advanced Excel (Pivot, XLOOKUP, Modeling), ERP & SAP, SQL (Queries, Joins), Python (Pandas).
- Notice Period / Availability: Immediate / מיידית
- Salary Expectation: 13,000 - 15,000 ₪ (גמישה ופתוחה לדיון בהתאם למקובל בארגון / open to discussion)
- Work Authorization: Israeli Citizen, authorized to work with no visa sponsorship needed.
- Selected CV File to submit: {cv_info.get('selected_cv_name')}

Target Language for Answers: {"Hebrew (עברית מקצועית ורהוטה)" if job_lang == "he" else "English (Professional and concise)"}

Form Fields to fill:
{json.dumps(fields, ensure_ascii=False, indent=2)}

Task:
For each form field in the list, provide the exact optimal value to enter into the application, plus a brief 1-sentence rationale.
If a field has predefined "options", pick the EXACT label from the provided options.
For open-ended/essay questions ("why us", "relevant experience"), write authentic, compelling 2-3 sentence responses connecting Lior's background directly to the company.

Return a JSON array of objects with the exact same fields, augmented with "value" and "reason":
[
  {{
    "name": "field_name",
    "label": "field_label",
    "type": "text/select/textarea",
    "required": true/false,
    "options": [...],
    "value": "Exact formulated value to submit",
    "reason": "Rationale for why this answer fits the candidate and role"
  }},
  ...
]
Return valid JSON ONLY (no markdown code blocks, no triple backticks).
"""

    if api_key and len(api_key.strip()) > 10:
        try:
            from google import genai
            client = genai.Client(api_key=api_key.strip())
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            raw = res.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*\n", "", raw)
                raw = re.sub(r"\n```$", "", raw)
            filled = json.loads(raw)
            if isinstance(filled, list) and len(filled) == len(fields):
                return filled
        except Exception as e:
            print(f"[Gemini Form Filling Error]: {e}, fallback to rule-based defaults")

    # Smart rule-based fallback
    filled_fields = []
    for f in fields:
        fname = f.get("name", "").lower()
        flabel = f.get("label", "").lower()
        val = ""
        reason = "ערך מבוסס על נתוני הפרופיל האישי"

        if "first" in fname or "first" in flabel or "פרטי" in flabel:
            val = "ליאור" if job_lang == "he" else "Lior"
            reason = "שם פרטי"
        elif "last" in fname or "last" in flabel or "משפחה" in flabel:
            val = "אזולאי" if job_lang == "he" else "Azulay"
            reason = "שם משפחה"
        elif "email" in fname or "אימייל" in flabel or "דואל" in flabel:
            val = profile.get("email", "liorazulaywork@gmail.com")
            reason = "כתובת דוא\"ל ליצירת קשר"
        elif "phone" in fname or "טלפון" in flabel:
            val = profile.get("phone", "050-345-0447")
            reason = "טלפון ישיר"
        elif "linkedin" in fname or "linkedin" in flabel:
            val = "https://linkedin.com/in/lior-azulay-bb8242430"
            reason = "קישור לפרופיל לינקדאין מאומת"
        elif "city" in fname or "location" in fname or "עיר" in flabel or "מגורים" in flabel:
            val = "אשקלון, ישראל" if job_lang == "he" else "Ashkelon, Israel"
            reason = "עיר מגורים"
        elif "company" in fname or "מעסיק" in flabel or "חברה" in flabel:
            val = "חיי במים (Hai Bamim)"
            reason = "מקום עבודה נוכחי שבו נוהלו פעילויות פיננסיות ותפעוליות"
        elif "title" in fname or "תפקיד" in flabel:
            val = "אחראית תפעול עסקי ואנליסטית פיננסית" if job_lang == "he" else "Business Operations & Financial Analyst"
            reason = "תפקיד נוכחי"
        elif "salary" in fname or "שכר" in flabel:
            val = "13,000 - 15,000 ₪ (גמישה בהתאם למקובל בארגון)" if job_lang == "he" else "13,000 - 15,000 ILS (open to discussion)"
            reason = "ציפיות שכר תחרותיות ומותאמות לשוק הכלכלנים והאנליסטים המתחילים"
        elif "notice" in fname or "start" in fname or "זמינות" in flabel:
            val = "מיידית" if job_lang == "he" else "Immediate"
            reason = "זמינות מלאה להתחלה מיידית"
        elif "authorization" in fname or "work" in fname or "אזרחות" in flabel or "אישור" in flabel:
            val = "כן" if job_lang == "he" else "Yes"
            reason = "אזרחות ישראלית מלאה ללא צורך באשרת עבודה"
        elif "why" in fname or "מדוע" in flabel or "למה" in flabel:
            if job_lang == "he":
                val = f"אני רואה ב-{job.get('company')} סביבה מקצועית אידיאלית שבה אוכל לתרום מהיכולות שלי בניתוח נתונים, בקרת תקציב ותפעול פיננסי, ולהמשיך להתפתח במקצועיות."
            else:
                val = f"I am deeply impressed by {job.get('company')}'s vision and momentum. My practical background in financial operations, budget tracking, and data analysis allows me to add immediate value to your team."
            reason = "חיבור ישיר בין יעדי החברה לרקע המעשי של המועמדת"
        elif "experience" in fname or "ניסיון" in flabel:
            if job_lang == "he":
                val = "כבוגרת תואר בכלכלה וניהול, ניהלתי בשלוש השנים האחרונות תזרים מזומנים, בקרת תקציב ודוחות P&L, לצד ניתוח מכירות ומחירונים באקסל מתקדם, עבודה עם מערכות SAP/ERP, וידע ב-SQL."
            else:
                val = "As an Economics & Management graduate, I have spent the last 3.5 years managing cash flow, tracking budgets, monitoring P&L, and conducting pricing analysis using advanced Excel, ERP/SAP systems, and SQL."
            reason = "פירוט תמציתי ומדויק של הישגים וכלים"
        else:
            val = "כן" if f.get("type") == "select" and "כן" in f.get("options", []) else ("Yes" if f.get("type") == "select" and "Yes" in f.get("options", []) else "")

        f_copy = dict(f)
        f_copy["value"] = val
        f_copy["reason"] = reason
        filled_fields.append(f_copy)

    return filled_fields


def build_application_kit(job_id: int) -> Dict[str, Any]:
    """
    Assembles the complete AI Application Kit for a job:
    1. Selects the appropriate CV (Hebrew vs English) with rationale.
    2. Inspects form fields and questions.
    3. Uses Google AI Pro to formulate exact answers.
    4. Generates a tailored cover letter.
    5. Saves to database and returns complete package.
    """
    job = get_job_by_id(job_id)
    if not job:
        raise ValueError(f"Job with ID {job_id} not found")

    profile = get_profile() or {}
    cv_info = select_best_cv(job, profile)
    raw_fields = extract_form_schema(job)
    ai_filled_fields = fill_form_fields_with_ai(raw_fields, job, profile, cv_info)

    # Generate or reuse tailored cover letter
    cover_letter = job.get("cover_letter")
    if not cover_letter or len(cover_letter.strip()) < 50:
        cover_letter = generate_cover_letter(job, profile, language=cv_info.get("language"))

    kit = {
        "job_id": job_id,
        "job_title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "url": job.get("url"),
        "source": job.get("source"),
        "job_language": cv_info.get("language"),
        "selected_cv": cv_info,
        "form_fields": ai_filled_fields,
        "cover_letter": cover_letter,
        "submission_ready": True,
        "total_fields": len(ai_filled_fields)
    }

    # Save application kit in database
    save_application_kit(job_id, kit)
    return kit


def execute_job_submission(job_id: int, form_answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submits the application:
    - Direct API submission for Greenhouse / Comeet where supported.
    - Updates job status to 'applied', sets applied_at timestamp.
    - Saves updated answers to application_kit.
    """
    job = get_job_by_id(job_id)
    if not job:
        raise ValueError(f"Job with ID {job_id} not found")

    profile = get_profile() or {}
    cv_info = select_best_cv(job, profile)
    cv_path = Path(cv_info.get("selected_cv_file", ""))

    submission_result = {
        "job_id": job_id,
        "company": job.get("company"),
        "title": job.get("title"),
        "submitted_cv": cv_info.get("selected_cv_name"),
        "language": cv_info.get("language"),
        "direct_api_attempted": False,
        "direct_api_success": False,
        "message": ""
    }

    # Attempt direct Greenhouse API post if applicable
    job_url = job.get("url", "")
    if "greenhouse.io" in job_url or job.get("source") == "Greenhouse":
        m = re.search(r'boards(?:\-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)/jobs/(\d+)', job_url)
        if m and cv_path.exists():
            board_token, jid = m.group(1), m.group(2)
            api_post_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{jid}"
            submission_result["direct_api_attempted"] = True
            try:
                # Prepare payload
                payload = {
                    "first_name": form_answers.get("first_name", "Lior"),
                    "last_name": form_answers.get("last_name", "Azulay"),
                    "email": form_answers.get("email", profile.get("email", "liorazulaywork@gmail.com")),
                    "phone": form_answers.get("phone", profile.get("phone", "050-345-0447")),
                    "cover_letter_text": form_answers.get("cover_letter", job.get("cover_letter", ""))
                }
                # Add custom questions
                for k, v in form_answers.items():
                    if k.startswith("question_"):
                        payload[k] = v

                files = {
                    "resume": (cv_info.get("selected_cv_name"), open(str(cv_path), "rb"), "application/pdf")
                }

                resp = requests.post(api_post_url, data=payload, files=files, timeout=12)
                if resp.status_code in [200, 201]:
                    submission_result["direct_api_success"] = True
                    submission_result["message"] = f"הוגש בהצלחה ישירות למערכת Greenhouse של {job.get('company')}!"
                else:
                    submission_result["message"] = f"Greenhouse API הגיב בקוד {resp.status_code}. הנתונים נשמרו להגשה מהירה דרך הפורטל."
            except Exception as e:
                submission_result["message"] = f"ניסיון הגשה ישירה: {e}. הנתונים והטופס נשמרו במלואם."

    if not submission_result["message"]:
        submission_result["message"] = f"הטופס הוכן במלואו והמועמדות סומנה כהוגשה עבור {job.get('company')} עם קורות חיים ב-{cv_info.get('language').upper()}!"

    # Save to DB with status 'applied'
    save_application_kit(job_id, {
        "answers": form_answers,
        "selected_cv_name": cv_info.get("selected_cv_name"),
        "selected_cv_lang": cv_info.get("language"),
        "submission_result": submission_result
    }, status="applied")

    return submission_result
