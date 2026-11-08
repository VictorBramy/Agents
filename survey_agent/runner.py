import time
import argparse
import sys
from typing import Dict, Any, List

from survey_agent.config import GMAIL_USER, GMAIL_APP_PASSWORD, TARGET_SENDER
from survey_agent.email_listener import check_polyeda_emails
from survey_agent.survey_solver import SurveySolver
from survey_agent.db import get_all_surveys, get_setting, insert_or_get_survey, get_surveys_summary

def run_survey_cycle(headless: bool = True) -> Dict[str, Any]:
    """
    Executes one full cycle:
    1. Checks Gmail for survey invitations from panelview@polyeda.com
    2. Identifies pending surveys
    3. Solves each survey sequentially with Playwright + Gemini AI
    """
    print("\n=======================================================")
    print("🤖 [Polyeda Survey Agent] מתחיל סבב בדיקת סקרים...")
    print("=======================================================")

    # 1. Check Gmail
    email_res = check_polyeda_emails()
    print(f"[*] תוצאת סריקת דואר: {email_res.get('message')}")

    # 2. Get pending surveys from DB
    all_surveys = get_all_surveys(limit=20)
    pending = [s for s in all_surveys if s.get("status") == "pending"]

    print(f"[*] ממתינים למילוי: {len(pending)} סקרים.")

    solver = SurveySolver(headless=headless)
    results = []

    for survey in pending:
        survey_id = survey["id"]
        survey_url = survey["survey_url"]
        print(f"\n[>>>] מפעיל סוכן Playwright עבור סקר #{survey_id}: {survey.get('subject')}...")

        res = solver.solve_survey(survey_id=survey_id, survey_url=survey_url)
        results.append(res)
        print(f"[✓] סקר #{survey_id} הסתיים בסטטוס: {res.get('status')} (הושלמו {res.get('pages_completed')} עמודים)")
        time.sleep(2)

    summary = get_surveys_summary()
    print("\n=======================================================")
    print(f"📊 סיכום: סה\"כ הושלמו: {summary.get('completed')} סקרים | סקרין-אאוט: {summary.get('screened_out')} | נקודות שנצברו: {summary.get('total_points')}")
    print("=======================================================\n")

    return {
        "status": "success",
        "checked_emails": email_res,
        "solved_count": len(results),
        "results": results,
        "summary": summary
    }

def solve_direct_url(url: str, headless: bool = False) -> Dict[str, Any]:
    """Solves a direct survey link provided by the user."""
    print(f"[*] מפעיל סוכן Playwright עבור קישור ישיר: {url}")
    survey_id = insert_or_get_survey({
        "msg_id": f"manual_{int(time.time())}",
        "sender": "manual_input",
        "subject": "סקר ישיר (הזנה ידנית)",
        "survey_url": url,
        "status": "pending"
    })

    solver = SurveySolver(headless=headless)
    res = solver.solve_survey(survey_id=survey_id, survey_url=url)
    return res

def main():
    parser = argparse.ArgumentParser(description="Polyeda Survey Auto-Agent with Playwright & AI")
    parser.add_argument("--check-once", action="store_true", help="בדוק מייל ומלא סקרים ממתינים פעם אחת")
    parser.add_argument("--daemon", action="store_true", help="הפעל ברקע בלולאה רציפה")
    parser.add_argument("--interval", type=int, default=15, help="תדירות בדיקה בדקות (במצב daemon)")
    parser.add_argument("--url", type=str, help="מלא סקר ישירות מקישור")
    parser.add_argument("--no-headless", action="store_true", help="הצג את חלון הדפדפן בזמן אמת")

    args = parser.parse_args()
    headless = not args.no_headless

    if args.url:
        solve_direct_url(args.url, headless=headless)
        return

    if args.daemon:
        interval_secs = max(args.interval, 2) * 60
        print(f"[*] סוכן הסקרים פועל במצב רציף ברקע (כל {args.interval} דקות). לחץ Ctrl+C לעצירה.")
        while True:
            try:
                run_survey_cycle(headless=headless)
            except Exception as e:
                print(f"[Runner Error]: {e}")
            time.sleep(interval_secs)
    else:
        run_survey_cycle(headless=headless)

if __name__ == "__main__":
    main()
