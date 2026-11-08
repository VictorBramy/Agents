import os
import re
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright

from core.config import BASE_DIR, UPLOAD_DIR
from core.db import get_job_by_id, get_profile, update_job_status, get_setting, save_application_kit
from core.form_agent import select_best_cv
from core.linkedin_session import get_linkedin_browser_context, get_linkedin_status

SCREENSHOTS_DIR = BASE_DIR / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _ask_gemini_question(question_text: str, options: List[str], profile: Dict[str, Any], lang: str = "en") -> str:
    """Uses Google AI Pro (Gemini 3.8 Flash) to answer screening questions on LinkedIn."""
    api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    q_lower = question_text.lower()
    # Fast heuristics for standard questions
    if any(k in q_lower for k in ["authorized to work", "legally authorized", "רשאי לעבוד", "אזרחות"]):
        return "Yes" if "yes" in [o.lower() for o in options] else ("כן" if "כן" in options else "Yes")
    if any(k in q_lower for k in ["sponsorship", "visa", "ויזה", "אשרת עבודה"]):
        return "No" if "no" in [o.lower() for o in options] else ("לא" if "לא" in options else "No")
    if any(k in q_lower for k in ["notice period", "start date", "זמינות", "earliest"]):
        return "Immediate" if lang == "en" else "מיידית"
    if any(k in q_lower for k in ["years", "שנים", "ניסיון"]) and not options:
        return "3"

    if api_key and len(api_key.strip()) > 10:
        try:
            from google import genai
            client = genai.Client(api_key=api_key.strip())
            prompt = f"""
You are answering an official job screening question on LinkedIn on behalf of candidate Lior Azulay:
- Background: B.A. in Economics & Management (המכללה האקדמית אשקלון)
- Experience: ~3.5 years in financial operations, budget tracking, cash flow, P&L, pricing and sales analysis at Hai Bamim, plus HR NCO in Israeli Air Force (SAP/ERP).
- Key tools: Excel (Pivot, XLOOKUP, Modeling), ERP, SAP, SQL, Python basics.
- Availability: Immediate
- Work authorization: Israeli Citizen (no visa sponsorship needed)

Question: "{question_text}"
Available Options (if dropdown/radio): {options if options else "Free text/number"}

Return ONLY the single best direct answer to select or type into this field (no extra commentary, no quotes):
"""
            res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
            ans = res.text.strip().replace('"', '').replace("'", "")
            if options:
                for opt in options:
                    if opt.lower() == ans.lower() or ans.lower() in opt.lower():
                        return opt
            return ans
        except Exception as e:
            print(f"[Gemini Screening Question Fallback]: {e}")

    if options:
        return options[0]
    return "Yes" if lang == "en" else "כן"


def apply_to_linkedin_job(job_id: int, auto_submit: bool = True, headless: bool = False) -> Dict[str, Any]:
    """
    Autonomously applies to a LinkedIn Easy Apply job using Playwright and Google AI Pro.
    Guarantees no duplicate submission if the job was already applied on LinkedIn!
    """
    job = get_job_by_id(job_id)
    if not job:
        return {"success": False, "message": f"משרה ID {job_id} לא נמצאה בבסיס הנתונים"}

    # 1. Immediate local check
    if job.get("status") == "applied":
        return {
            "success": True,
            "already_applied": True,
            "message": f"המשרה '{job.get('title')}' כבר סומנה כהוגשה במערכת בתאריך {job.get('applied_at') or 'מוקדם יותר'}. הסוכן דילג על הגשה כפולה.",
            "logs": ["Job already marked as applied in database. Skipping duplicate submission."]
        }

    job_url = job.get("url", "")
    if not job_url or "linkedin.com" not in job_url:
        return {"success": False, "message": "למשרה זו אין קישור תקין של LinkedIn"}

    profile = get_profile() or {}
    cv_info = select_best_cv(job, profile)
    selected_cv_path = Path(cv_info.get("selected_cv_file", ""))
    lang = cv_info.get("language", "en")

    logs = []
    logs.append(f"מתחיל תהליך הגשה אוטומטית למשרה: '{job.get('title')}' ב-{job.get('company')}")
    logs.append(f"קובץ קו\"ח שנבחר: {cv_info.get('selected_cv_name')} (שפה: {lang.upper()})")

    with sync_playwright() as p:
        browser = None
        try:
            browser, context = get_linkedin_browser_context(p, headless=headless)
            page = context.new_page()

            logs.append(f"פותח את עמוד המשרה בלינקדאין: {job_url}...")
            page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            # 2. Comprehensive check if ALREADY APPLIED on LinkedIn
            already_applied_selectors = [
                "div.jobs-s-apply__applied-date",
                "span.artdeco-inline-feedback__message",
                "//span[contains(., 'Applied') or contains(., 'הגשת מועמדות') or contains(., 'הוגש')]",
                "//div[contains(., 'You applied') or contains(., 'הגשת מועמדות ב-') or contains(., 'מועמדותך הוגשה')]",
                "button[disabled][aria-label*='Applied']",
                "button[disabled][aria-label*='הגשת']"
            ]

            for sel in already_applied_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=1000):
                        applied_text = el.inner_text().strip()
                        if any(w in applied_text.lower() for w in ["applied", "הגשת", "הוגש", "you applied"]):
                            logs.append(f"זוהה באנר הגשה קיים בלינקדאין: '{applied_text}'")
                            logs.append("המשרה כבר הוגשה בעבר בחשבון ה-LinkedIn שלך! הסוכן מסמן כהוגש ומדלג על הגשה חוזרת.")
                            update_job_status(job_id, "applied")
                            context.close()
                            browser.close()
                            return {
                                "success": True,
                                "already_applied": True,
                                "message": f"המשרה '{job.get('title')}' כבר הוגשה בעבר בחשבון ה-LinkedIn שלך! ({applied_text}). המערכת דילגה על הגשה חוזרת.",
                                "logs": logs
                            }
                except Exception:
                    pass

            # 3. Locate Easy Apply button
            apply_btn = None
            selectors = [
                "button.jobs-apply-button",
                "button[aria-label*='Easy Apply']",
                "button[aria-label*='הגשה מהירה']",
                "//button[contains(., 'Easy Apply')]",
                "//button[contains(., 'הגשה מהירה')]"
            ]

            for sel in selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        apply_btn = btn
                        break
                except Exception:
                    continue

            if not apply_btn:
                context.close()
                browser.close()
                return {
                    "success": False,
                    "message": "כפתור Easy Apply לא נמצא בעמוד (ייתכן שהמשרה מפנה לאתר חיצוני או שאינך מחובר לחשבון).",
                    "logs": logs
                }

            logs.append("נמצא כפתור Easy Apply. לוחץ לפתיחת טופס ההגשה...")
            apply_btn.click()
            time.sleep(2)

            # 4. Multi-step form navigation
            step_count = 0
            max_steps = 10
            submitted = False

            while step_count < max_steps:
                step_count += 1
                logs.append(f"מעבד שלב {step_count} בטופס...")
                time.sleep(1.5)

                modal = page.locator("div.jobs-easy-apply-modal, div[role='dialog']").first
                if not modal.is_visible(timeout=3000):
                    logs.append("חלון הטופס נסגר או הושלם.")
                    break

                # A. File Upload (CV)
                file_input = modal.locator("input[type='file']").first
                if file_input.is_visible(timeout=1000):
                    if selected_cv_path.exists():
                        logs.append(f"מעלה את קובץ קורות החיים: {selected_cv_path.name}")
                        file_input.set_input_files(str(selected_cv_path))
                        time.sleep(1)

                # B. Text & Number Inputs
                inputs = modal.locator("input:not([type='hidden']):not([type='file'])").all()
                for inp in inputs:
                    try:
                        val = inp.input_value()
                        if not val:
                            inp_id = inp.get_attribute("id") or ""
                            label_el = modal.locator(f"label[for='{inp_id}']").first
                            label_text = label_el.inner_text() if label_el.is_visible(timeout=500) else ""
                            if not label_text:
                                label_text = inp.get_attribute("aria-label") or ""

                            ans = _ask_gemini_question(label_text, [], profile, lang=lang)
                            inp.fill(ans)
                            logs.append(f"מילוי שדה '{label_text[:30]}': {ans}")
                    except Exception:
                        pass

                # C. Radio Buttons
                fieldsets = modal.locator("fieldset").all()
                for fs in fieldsets:
                    try:
                        legend = fs.locator("legend").inner_text()
                        radios = fs.locator("input[type='radio']").all()
                        if radios:
                            options_labels = [r.locator("..").inner_text().strip() for r in radios]
                            selected_opt = _ask_gemini_question(legend, options_labels, profile, lang=lang)
                            for r in radios:
                                if selected_opt.lower() in r.locator("..").inner_text().strip().lower():
                                    r.check()
                                    logs.append(f"בחירת אפשרות '{legend[:30]}': {selected_opt}")
                                    break
                    except Exception:
                        pass

                # D. Dropdown Selects
                selects = modal.locator("select").all()
                for sel in selects:
                    try:
                        options = [o.inner_text().strip() for o in sel.locator("option").all() if o.inner_text().strip()]
                        sel_id = sel.get_attribute("id") or ""
                        label_el = modal.locator(f"label[for='{sel_id}']").first
                        label_text = label_el.inner_text() if label_el.is_visible(timeout=500) else ""
                        chosen = _ask_gemini_question(label_text, options, profile, lang=lang)
                        sel.select_option(label=chosen)
                        logs.append(f"בחירה מרשימה '{label_text[:30]}': {chosen}")
                    except Exception:
                        pass

                # E. Check for Final Submit
                submit_btn = modal.locator("//button[contains(., 'Submit application') or contains(., 'הגש מועמדות')]").first
                if submit_btn.is_visible(timeout=1000):
                    logs.append("הגענו לשלב הבדיקה הסופי (Review & Submit)!")
                    if auto_submit:
                        logs.append("מגיש את המועמדות כעת...")
                        submit_btn.click()
                        time.sleep(3)
                        submitted = True
                        break
                    else:
                        screenshot_path = SCREENSHOTS_DIR / f"job_{job_id}_review.png"
                        page.screenshot(path=str(screenshot_path))
                        logs.append(f"הטופס מולא ונעצר בשלב ה-Review. צילום מסך נשמר: {screenshot_path.name}")
                        break

                # F. Advance to Next Step
                next_btn = modal.locator("//button[contains(., 'Next') or contains(., 'Review') or contains(., 'הבא') or contains(., 'בדיקה')]").first
                if next_btn.is_visible(timeout=2000):
                    logs.append("עובר לשלב הבא בטופס...")
                    next_btn.click()
                    time.sleep(1.5)
                else:
                    logs.append("לא נמצא כפתור המשך/הגשה נוסף.")
                    break

            # 5. Save final result
            screenshot_final = SCREENSHOTS_DIR / f"job_{job_id}_final.png"
            page.screenshot(path=str(screenshot_final))
            context.close()
            browser.close()

            if submitted:
                update_job_status(job_id, "applied")
                save_application_kit(job_id, {
                    "method": "LinkedIn Auto Easy Apply",
                    "submitted_cv": cv_info.get("selected_cv_name"),
                    "logs": logs
                }, status="applied")
                return {
                    "success": True,
                    "submitted": True,
                    "message": f"המועמדות הוגשה בהצלחה ישירות בלינקדאין עבור '{job.get('title')}' ב-{job.get('company')}!",
                    "logs": logs,
                    "screenshot": f"/static/screenshots/{screenshot_final.name}"
                }
            else:
                return {
                    "success": True,
                    "submitted": False,
                    "message": "טופס ה-Easy Apply מולא בהצלחה על ידי ה-AI ונעצר בשלב הבדיקה הסופית (Review).",
                    "logs": logs
                }

        except Exception as e:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            logs.append(f"שגיאה באוטומציה: {e}")
            return {
                "success": False,
                "message": f"אירעה שגיאה באוטומציה של לינקדאין: {e}",
                "logs": logs
            }
