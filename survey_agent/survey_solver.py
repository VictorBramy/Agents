import os
import re
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from survey_agent.config import (
    PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT, SURVEY_SCREENSHOTS_DIR, GEMINI_API_KEY
)
from survey_agent.db import get_survey_profile, update_survey_status, get_setting

class SurveySolver:
    """
    Playwright-based autonomous survey bot tailored for Israeli survey panels
    (Polyeda / Project Midgam / Panel View - panelview@polyeda.com).
    Navigates through survey pages, answers demographic and substantive questions
    consistently using candidate persona and Google Gemini AI, and submits responses.
    """

    def __init__(self, headless: Optional[bool] = None, slow_mo: int = 100):
        if headless is not None:
            self.headless = headless
        else:
            self.headless = PLAYWRIGHT_HEADLESS
        self.slow_mo = slow_mo
        self.profile = get_survey_profile()
        self.logs: List[str] = []

    def _log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        self.logs.append(formatted)
        print(f"[SurveyBot] {formatted}")

    def solve_survey(self, survey_id: int, survey_url: str) -> Dict[str, Any]:
        """
        Main entry point: launches Playwright, solves the survey, takes screenshot,
        and records result in the database.
        """
        self.logs = []
        self._log(f"מתחיל מילוי סקר #{survey_id}: {survey_url}")
        update_survey_status(survey_id, status="running", logs=self.logs)

        pages_count = 0
        final_status = "failed"
        error_msg = ""
        screenshot_path = ""

        with sync_playwright() as p:
            browser = None
            try:
                # Try launching Google Chrome channel first, fallback to standard chromium
                try:
                    browser = p.chromium.launch(channel="chrome", headless=self.headless, slow_mo=self.slow_mo)
                    self._log("דפדפן Google Chrome הופעל בהצלחה.")
                except Exception:
                    browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
                    self._log("דפדפן Chromium הופעל בהצלחה.")

                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="he-IL",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(PLAYWRIGHT_TIMEOUT)

                # 1. Navigate to survey link
                self._log(f"טוען עמוד סקר: {survey_url}")
                page.goto(survey_url, wait_until="domcontentloaded")
                time.sleep(2)

                # Check if survey has initial landing button ("התחל", "כניסה לסקר", "המשך")
                self._handle_landing_screen(page)

                # 2. Main survey interaction loop (up to 40 steps)
                for step in range(1, 41):
                    pages_count = step
                    time.sleep(1.5)

                    page_text = page.inner_text("body").strip() if page.locator("body").count() > 0 else ""

                    # Check completion or screen-out
                    is_complete, comp_msg = self._check_completion(page_text)
                    if is_complete:
                        self._log(f"הסקר הסתיים בהצלחה: {comp_msg}")
                        final_status = "completed"
                        break

                    is_screenout, so_msg = self._check_screenout(page_text)
                    if is_screenout:
                        self._log(f"מכסת המשיבים התמלאה / סקרין-אאוט: {so_msg}")
                        final_status = "screened_out"
                        break

                    self._log(f"--- שלב {step}: מזהה שאלות בעמוד ---")
                    answered = self._answer_current_page(page, page_text)

                    # Click Next button
                    clicked = self._click_next_button(page)
                    if not clicked:
                        # Re-check completion after potential submit
                        time.sleep(2)
                        pt = page.inner_text("body").strip()
                        if self._check_completion(pt)[0]:
                            final_status = "completed"
                            break
                        self._log("לא אותר כפתור 'המשך/הבא'. ייתכן שהסקר הסתיים.")
                        final_status = "completed"
                        break

                    time.sleep(2)

                if final_status == "running":
                    final_status = "completed"

            except Exception as e:
                error_msg = str(e)
                self._log(f"שגיאה במהלך מילוי הסקר: {error_msg}")
                final_status = "failed"

            finally:
                # Save screenshot of final screen
                if page:
                    try:
                        filename = f"survey_{survey_id}_{final_status}_{int(time.time())}.png"
                        out_path = SURVEY_SCREENSHOTS_DIR / filename
                        page.screenshot(path=str(out_path), full_page=True)
                        screenshot_path = f"/static/survey_screenshots/{filename}"
                        self._log(f"צילום מסך נשמר: {screenshot_path}")
                    except Exception as se:
                        self._log(f"לא ניתן לשמור צילום מסך: {se}")

                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

        # Update database
        update_survey_status(
            survey_id=survey_id,
            status=final_status,
            pages_completed=pages_count,
            error_message=error_msg,
            screenshot_path=screenshot_path,
            logs=self.logs
        )

        return {
            "survey_id": survey_id,
            "status": final_status,
            "pages_completed": pages_count,
            "screenshot_path": screenshot_path,
            "logs": self.logs,
            "error_message": error_msg
        }

    def _handle_landing_screen(self, page: Page):
        """Clicks initial start / proceed buttons if present."""
        start_selectors = [
            'button:has-text("התחל")',
            'button:has-text("כניסה לסקר")',
            'button:has-text("המשך")',
            'button:has-text("Start")',
            'input[type="submit"][value*="התחל"]',
            'input[type="submit"][value*="המשך"]',
            'input[type="button"][value*="התחל"]',
            'input[type="button"][value*="המשך"]',
            'a:has-text("התחל")',
            'a:has-text("כניסה לסקר")'
        ]
        for sel in start_selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    self._log(f"נמצא כפתור פתיחת סקר ({sel}), לוחץ...")
                    el.click()
                    time.sleep(1.5)
                    break
            except Exception:
                pass

    def _check_completion(self, page_text: str) -> Tuple[bool, str]:
        """Detects whether survey completed successfully."""
        completion_phrases = [
            "תודה על השתתפותך",
            "תודה שהשתתפת",
            "הסקר הסתיים",
            "סיימת את הסקר",
            "התשובות שלך נקלטו",
            "הנקודות עודכנו",
            "הנקודות נצברו",
            "סיום הסקר",
            "תשובותיך נקלטו בהצלחה",
            "thank you for your participation",
            "survey completed"
        ]
        text_lower = page_text.lower()
        for phrase in completion_phrases:
            if phrase in text_lower:
                return True, phrase
        return False, ""

    def _check_screenout(self, page_text: str) -> Tuple[bool, str]:
        """Detects if candidate was screened out or quota filled."""
        screenout_phrases = [
            "מכסת המשיבים",
            "המכסה התמלאה",
            "אינך מתאים/ה",
            "אינך מתאים לסקר",
            "תודה על נכונותך, אך לצערנו",
            "הסקר כבר נסגר",
            "הסקר אינו פעיל עוד",
            "quota full"
        ]
        text_lower = page_text.lower()
        for phrase in screenout_phrases:
            if phrase in text_lower:
                return True, phrase
        return False, ""

    def _answer_current_page(self, page: Page, page_text: str) -> bool:
        """
        Analyzes the current survey page, determines question types,
        answers demographic fields or substantive questions using Gemini AI / profile,
        and selects the appropriate form controls.
        """
        answered_anything = False

        # 1. Handle Demographic Dropdowns (Cities, Year of birth, Education)
        answered_selects = self._answer_select_dropdowns(page)
        if answered_selects:
            answered_anything = True

        # 2. Handle Matrix / Grid Tables (multiple statements with 1-5 ratings)
        answered_matrix = self._answer_matrix_tables(page, page_text)
        if answered_matrix:
            answered_anything = True

        # 3. Handle Radio Groups (Single-choice questions)
        answered_radios = self._answer_radio_groups(page, page_text)
        if answered_radios:
            answered_anything = True

        # 4. Handle Checkboxes (Multiple-choice questions)
        answered_checkboxes = self._answer_checkboxes(page, page_text)
        if answered_checkboxes:
            answered_anything = True

        # 5. Handle Text Inputs / Open textboxes
        answered_text = self._answer_text_inputs(page, page_text)
        if answered_text:
            answered_anything = True

        return answered_anything

    def _answer_select_dropdowns(self, page: Page) -> bool:
        """Answers select dropdown elements (e.g. birth year, city, education)."""
        selects = page.locator("select")
        count = selects.count()
        if count == 0:
            return False

        acted = False
        prof = self.profile
        for i in range(count):
            try:
                sel = selects.nth(i)
                if not sel.is_visible():
                    continue

                # Inspect select options
                options = sel.locator("option").all_inner_texts()
                opt_values = sel.locator("option").evaluate_all("opts => opts.map(o => o.value)")

                # Demographic: Birth year (1999)
                target_year = str(prof.get("birth_year", 1999))
                for opt_text, opt_val in zip(options, opt_values):
                    if target_year in opt_text:
                        sel.select_option(value=opt_val)
                        self._log(f"נבחרה שנת לידה בדרופדאון: {target_year}")
                        acted = True
                        break

                # Demographic: City (תל אביב)
                target_city = prof.get("city", "תל אביב")
                if not acted:
                    for opt_text, opt_val in zip(options, opt_values):
                        if target_city in opt_text:
                            sel.select_option(value=opt_val)
                            self._log(f"נבחרה עיר בדרופדאון: {target_city}")
                            acted = True
                            break

                # Demographic: Gender
                if not acted:
                    gender = prof.get("gender", "נקבה")
                    for opt_text, opt_val in zip(options, opt_values):
                        if gender in opt_text or ("אישה" in opt_text and gender == "נקבה") or ("גבר" in opt_text and gender == "זכר"):
                            sel.select_option(value=opt_val)
                            self._log(f"נבחר מין בדרופדאון: {gender}")
                            acted = True
                            break

                # Fallback: select second option (first option is usually "בחר...")
                if not acted and len(opt_values) > 1:
                    sel.select_option(index=1)
                    acted = True
            except Exception:
                pass
        return acted

    def _answer_radio_groups(self, page: Page, page_text: str) -> bool:
        """Answers radio button groups (Single Choice)."""
        radios = page.locator('input[type="radio"]')
        total_radios = radios.count()
        if total_radios == 0:
            return False

        # Group radio buttons by 'name' attribute
        radio_names = radios.evaluate_all("els => Array.from(new Set(els.map(e => e.name).filter(n => n)))")
        if not radio_names:
            radio_names = ["_default_group"]

        prof = self.profile
        acted = False

        for name in radio_names:
            group = page.locator(f'input[type="radio"][name="{name}"]') if name != "_default_group" else radios
            group_count = group.count()
            if group_count == 0:
                continue

            # Check if an option in this group is already selected
            is_already_checked = group.evaluate_all("els => els.some(e => e.checked)")
            if is_already_checked:
                continue

            # Get label texts for this group
            options_info = []
            for j in range(group_count):
                r = group.nth(j)
                # Find associated label
                r_id = r.get_attribute("id") or ""
                label_text = ""
                if r_id:
                    lbl = page.locator(f'label[for="{r_id}"]')
                    if lbl.count() > 0:
                        label_text = lbl.inner_text().strip()
                if not label_text:
                    # Check parent label
                    label_text = r.locator("xpath=..").inner_text().strip()
                options_info.append({"index": j, "text": label_text, "element": r})

            # Check for demographic matches first!
            selected_idx = None
            options_text_combined = " ".join([o["text"] for o in options_info])

            # 1. Gender question
            if any(term in options_text_combined for term in ["נקבה", "זכר", "אישה", "גבר"]):
                target_gender = prof.get("gender", "נקבה")
                for o in options_info:
                    if target_gender in o["text"] or ("אישה" in o["text"] and target_gender == "נקבה"):
                        selected_idx = o["index"]
                        self._log(f"נבחר מין: {o['text']}")
                        break

            # 2. Age Range
            elif any(re.search(r'\b\d{2}-\d{2}\b', o["text"]) for o in options_info):
                age = prof.get("age", 27)
                for o in options_info:
                    match = re.search(r'(\d{2})\s*-\s*(\d{2})', o["text"])
                    if match:
                        low, high = int(match.group(1)), int(match.group(2))
                        if low <= age <= high:
                            selected_idx = o["index"]
                            self._log(f"נבחר טווח גיל: {o['text']}")
                            break

            # 3. Marital status
            elif any(term in options_text_combined for term in ["רווק", "רווקה", "נשוי", "נשואה"]):
                status = prof.get("marital_status", "רווקה")
                for o in options_info:
                    if status in o["text"] or ("רווק" in o["text"] and "רווק" in status):
                        selected_idx = o["index"]
                        self._log(f"נבחר מצב משפחתי: {o['text']}")
                        break

            # 4. Education
            elif any(term in options_text_combined for term in ["תואר ראשון", "אקדמית", "תיכונית"]):
                for o in options_info:
                    if any(term in o["text"] for term in ["תואר ראשון", "אקדמית מלאה", "אקדמי"]):
                        selected_idx = o["index"]
                        self._log(f"נבחרה השכלה: {o['text']}")
                        break

            # 5. Religion / Sector
            elif any(term in options_text_combined for term in ["חילוני", "מסורתי", "דתי", "חרדי"]):
                sector = prof.get("religion_sector", "חילונית")
                for o in options_info:
                    if "חילוני" in o["text"]:
                        selected_idx = o["index"]
                        self._log(f"נבחר מגזר: {o['text']}")
                        break

            # 6. Area / District
            elif any(term in options_text_combined for term in ["מרכז", "גוש דן", "תל אביב"]):
                for o in options_info:
                    if any(term in o["text"] for term in ["תל אביב", "גוש דן", "מרכז"]):
                        selected_idx = o["index"]
                        self._log(f"נבחר אזור: {o['text']}")
                        break

            # 7. Employment
            elif any(term in options_text_combined for term in ["שכיר", "שכירה", "עצמאי"]):
                for o in options_info:
                    if "שכיר" in o["text"]:
                        selected_idx = o["index"]
                        self._log(f"נבחר מעמד תעסוקתי: {o['text']}")
                        break

            # If not demographic -> General survey question!
            if selected_idx is None:
                selected_idx = self._decide_choice_with_ai(page_text, [o["text"] for o in options_info])

            # Click chosen radio
            try:
                target_radio = group.nth(selected_idx)
                # Try clicking parent label first for custom styled inputs
                parent = target_radio.locator("xpath=..")
                if parent.count() > 0:
                    parent.click()
                else:
                    target_radio.check(force=True)
                acted = True
            except Exception:
                try:
                    group.nth(selected_idx).check(force=True)
                    acted = True
                except Exception:
                    pass

        return acted

    def _answer_matrix_tables(self, page: Page, page_text: str) -> bool:
        """Answers Matrix / Grid tables where rows contain statements and columns are rating scales."""
        tables = page.locator("table, .matrix, .grid-table")
        if tables.count() == 0:
            return False

        acted = False
        rows = page.locator("tr")
        row_count = rows.count()

        for i in range(row_count):
            try:
                row = rows.nth(i)
                row_radios = row.locator('input[type="radio"]')
                r_count = row_radios.count()
                if r_count < 2:
                    continue

                # Check if already checked in this row
                if row_radios.evaluate_all("els => els.some(e => e.checked)"):
                    continue

                # Choose favorable/positive rating (e.g. 4 out of 5, or 3 out of 5)
                # On 1-5 scale: index 3 or 2
                chosen_idx = min(3, r_count - 1) if r_count >= 5 else int(r_count / 2)
                row_radios.nth(chosen_idx).check(force=True)
                acted = True
            except Exception:
                pass

        if acted:
            self._log("מולאה טבלת דירוגים (Matrix Grid)")
        return acted

    def _answer_checkboxes(self, page: Page, page_text: str) -> bool:
        """Answers multiple-choice checkboxes."""
        checkboxes = page.locator('input[type="checkbox"]')
        cb_count = checkboxes.count()
        if cb_count == 0:
            return False

        # If already some checkboxes checked, skip
        if checkboxes.evaluate_all("els => els.some(e => e.checked)"):
            return False

        # Check 1-2 realistic options (or first available checkbox that isn't "none of the above")
        acted = False
        try:
            for i in range(min(cb_count, 3)):
                cb = checkboxes.nth(i)
                lbl_text = cb.locator("xpath=..").inner_text().lower()
                # Skip "none of the above" unless nothing else
                if any(bad in lbl_text for bad in ["אף אחד", "אף מותג", "אף אחד מהם", "none"]):
                    continue
                cb.check(force=True)
                acted = True
                break
        except Exception:
            pass

        return acted

    def _answer_text_inputs(self, page: Page, page_text: str) -> bool:
        """Fills open-ended text fields and year/age inputs."""
        inputs = page.locator('input[type="text"], input[type="number"], textarea')
        count = inputs.count()
        if count == 0:
            return False

        prof = self.profile
        acted = False

        for i in range(count):
            try:
                inp = inputs.nth(i)
                if not inp.is_visible():
                    continue
                val = inp.input_value()
                if val and val.strip():
                    continue

                # Check placeholder or surrounding text
                placeholder = inp.get_attribute("placeholder") or ""
                surrounding = inp.locator("xpath=..").inner_text() + " " + placeholder

                if any(k in surrounding for k in ["שנת לידה", "שנה"]):
                    inp.fill(str(prof.get("birth_year", 1999)))
                    acted = True
                    self._log("הוזנה שנת לידה בשדה טקסט: 1999")
                elif any(k in surrounding for k in ["גיל", "age"]):
                    inp.fill(str(prof.get("age", 27)))
                    acted = True
                    self._log("הוזן גיל בשדה טקסט: 27")
                elif any(k in surrounding for k in ["עיר", "יישוב", "מגורים"]):
                    inp.fill(prof.get("city", "תל אביב - יפו"))
                    acted = True
                    self._log("הוזנה עיר מגורים בשדה טקסט: תל אביב")
                elif inp.evaluate("el => el.tagName.toLowerCase()") == "textarea" or len(surrounding) > 10:
                    # Open feedback question
                    inp.fill("שירות מקצועי, ברור ואיכותי. חוויית שימוש נוחה וטובה.")
                    acted = True
                    self._log("הוזנה תשובה לשאלה פתוחה")
            except Exception:
                pass
        return acted

    def _decide_choice_with_ai(self, question_text: str, options: List[str]) -> int:
        """
        Calls Google Gemini AI to pick the most natural choice matching the candidate persona.
        Falls back to smart neutral/favorable index (4 on 1-5 scale) if AI is unavailable.
        """
        if not options:
            return 0

        # Fast heuristic fallback calculation
        default_index = min(3, len(options) - 1) if len(options) >= 5 else 0

        api_key = get_setting("GEMINI_API_KEY") or GEMINI_API_KEY
        if not api_key or len(api_key.strip()) < 10:
            return default_index

        try:
            from google import genai
            client = genai.Client(api_key=api_key.strip())

            prompt = f"""
את/ה עונה על סקר צרכני/חברתי ישראלי.
פרופיל המשיבה: אישה, בת 27, גרה בתל אביב, כלכלנית ואנליסטית פיננסית, חילונית, בעלת רכב, צרכנית נבונה וחיובית.

טקסט העמוד / השאלה:
{question_text[:500]}

אפשרויות הבחירה (בחר את האינדקס של האפשרות ההגיונית והעקבית ביותר, מ-0 עד {len(options)-1}):
{chr(10).join([f"{idx}: {opt}" for idx, opt in enumerate(options)])}

ענה במספר בלבד (האינדקס של הבחירה, למשל: 0, 1, 2...). ללא מילים נוספות.
"""
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            raw = resp.text.strip()
            digits = re.findall(r'\d+', raw)
            if digits:
                chosen = int(digits[0])
                if 0 <= chosen < len(options):
                    self._log(f"החלטת AI (אינדקס {chosen}): {options[chosen]}")
                    return chosen
        except Exception:
            pass

        return default_index

    def _click_next_button(self, page: Page) -> bool:
        """Finds and clicks the primary Next / Continue button."""
        next_selectors = [
            'button:has-text("המשך")',
            'button:has-text("הבא")',
            'button:has-text("סיום")',
            'button:has-text("אישור")',
            'input[type="submit"][value*="המשך"]',
            'input[type="submit"][value*="הבא"]',
            'input[type="submit"][value*="סיום"]',
            'input[type="button"][value*="המשך"]',
            'input[type="button"][value*="הבא"]',
            'input[type="button"][value*="סיום"]',
            'button.btn-next',
            'button.next',
            '#btnNext',
            '#ButtonNext',
            'a.next-btn:has-text("המשך")',
            'button:has-text("Next")',
            'input[type="submit"]'
        ]

        for sel in next_selectors:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    self._log(f"לוחץ על כפתור המשך ({sel})")
                    btn.click()
                    return True
            except Exception:
                pass

        return False
