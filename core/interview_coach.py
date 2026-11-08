import os
import json
from typing import Dict, Any, List, Optional
from core.db import get_setting

def generate_interview_prep(job: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a comprehensive, tailored Interview Preparation Kit for a specific job,
    combining predictive technical/behavioral questions, STAR-method sample answers,
    and strategic questions to ask the interviewer.
    """
    job_title = job.get("title", "משרה פיננסית")
    company = job.get("company", "החברה")
    job_desc = job.get("description", "")
    matching_skills = job.get("matching_skills", [])
    if isinstance(matching_skills, str):
        try:
            matching_skills = json.loads(matching_skills)
        except Exception:
            matching_skills = []

    cand_name = profile.get("full_name", "ליאור אזולאי")
    if "|" in cand_name:
        cand_name = cand_name.split("|")[0].strip()
    cand_exp = profile.get("years_of_experience", 3.5)
    skills_list = [s.split('(')[0].strip() for s in profile.get("skills", [])[:6]]

    api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

    llm_result = None
    if api_key and len(api_key.strip()) > 10:
        def call_gemini():
            nonlocal llm_result
            try:
                from google import genai
                client = genai.Client(api_key=api_key.strip())
                prompt = f"""
You are an elite executive recruiter and interview coach.
Generate a structured Interview Preparation Kit in Hebrew for candidate {cand_name} interviewing for "{job_title}" at "{company}".

Candidate Background:
- Degree: B.A. in Economics & Management (בוגרת תואר ראשון בכלכלה וניהול)
- Practical Experience: ~{cand_exp} years in financial operations, business analysis, cash flow management, P&L tracking, and budget control.
- Core Skills: {', '.join(skills_list)} (Advanced Excel, ERP/SAP, SQL, Python).

Job Title: {job_title}
Company: {company}
Job Description:
{job_desc[:1500]}

Please return a valid JSON object (without markdown code blocks) with:
{{
  "job_title": "{job_title}",
  "company": "{company}",
  "executive_summary": "...",
  "top_questions": [
    {{
      "question": "...",
      "category": "...",
      "why_asked": "...",
      "star_answer": "..."
    }}
  ],
  "questions_to_ask_interviewer": ["...", "..."],
  "insider_tips": ["...", "..."]
}}
"""
                resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )
                raw = resp.text.strip()
                if raw.startswith("```json"):
                    raw = raw[7:]
                if raw.startswith("```"):
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                llm_result = json.loads(raw.strip())
            except Exception as e:
                print(f"[InterviewCoach LLM error]: {e}")

        import threading
        t = threading.Thread(target=call_gemini, daemon=True)
        t.start()
        t.join(timeout=3.5) # Max wait 3.5s

        if llm_result and isinstance(llm_result, dict) and llm_result.get("top_questions"):
            return llm_result

    # High-quality smart domain template fallback
    return {
        "job_title": job_title,
        "company": company,
        "executive_summary": f"בראיון למשרת {job_title} ב-{company}, הדגש המרכזי הוא היכולת שלך לשלב ידע מעמיק בכלכלה ובדוחות כספיים (P&L ותזרים מזומנים) יחד עם שליטה טכנית מהירה ב-Excel מתקדם ומערכות ERP. הפגיני גישה יוזמת, חשיבה אנליטית ויכולת לתרגם נתונים להמלצות עסקיות ברורות.",
        "top_questions": [
            {
                "question": f"ספרי לי על עצמך ועל הניסיון שלך הרלוונטי למשרת {job_title}?",
                "category": "פתיחה והיכרות",
                "why_asked": "בדיקת בהירות, ביטחון מקצועי והתאמה לתפקיד.",
                "star_answer": f"אני בוגרת תואר ראשון בכלכלה וניהול ובעלת כ-{cand_exp} שנות ניסיון מעשי בתפעול פיננסי, בקרת תקציב וניתוח נתונים עסקיים. במסגרת העבודה שלי ניהלתי תזרימי מזומנים, ניתחתי דוחות רווח והפסד (P&L) ועבדתי באופן יומיומי עם Excel מתקדם ומערכות ERP ו-SAP. אני מחפשת את האתגר הבא ב-{company} שבו אוכל לתרום לדיוק הנתונים ולשיפור תהליכי קבלת ההחלטות."
            },
            {
                "question": "איך את מתמודדת עם פערים או אי-התאמות בדוחות כספיים או בתקציב?",
                "category": "מקצועי / מתודולוגי",
                "why_asked": "בדיקת ירידה לפרטים, אחריות ופתרון בעיות.",
                "star_answer": "בכל אי-התאמה אני פועלת בצורה שיטתית: ראשית מאמתת את מקורות הנתונים בין ה-ERP לדוחות האקסל, מבצעת הצלבות עם פונקציות מתקדמות, ומזהה את מקור הסטייה – בין אם מדובר בטעות רישום או שינוי תפעולי בלתי צפוי. לאחר התיקון, אני תמיד מוודאת בניית מנגנון בקרה כדי למנוע הישנות של הטעות."
            },
            {
                "question": "מהי הרמה שלך ב-Excel ועם אילו פונקציות וכלים את עובדת ביומיום?",
                "category": "טכני",
                "why_asked": "בדיקת עצמאות טכנולוגית בעבודה אנליטית יומיומית.",
                "star_answer": "אני עובדת ברמה מתקדמת ביותר: שולטת ב-XLOOKUP, INDEX/MATCH, טבלאות ציר (Pivot Tables) מורכבות, נוסחאות תנאי מתקדמות (SUMIFS, COUNTIFS) ועיצוב מודלים פיננסיים דינמיים. בנוסף, יש לי רקע אקדמי ב-SQL ו-Python המאפשר לי להבין שליפות מסדי נתונים בצורה מעמיקה."
            },
            {
                "question": "ספרי על מקרה שבו היית צריכה להעביר ממצאים פיננסיים מורכבים לגורם לא כלכלי (כגון מנהל מוצר או שיווק)?",
                "category": "התנהגותי / תקשורת",
                "why_asked": "בדיקת יכולת תקשורת בינאישית וראייה עסקית רחבה.",
                "star_answer": "זיהיתי סטייה תקציבית באחד מסעיפי ההוצאה התפעוליים. במקום להציג גליון נתונים עמוס, זיקקתי את המסקנות לתרשים ברור שהציג את ההשפעה בשורה התחתונה ואת 2 החלופות המרכזיות לפעולה. זה אפשר לקבל החלטה מהירה ומדויקת תוך 15 דקות."
            },
            {
                "question": f"למה את מעוניינת להצטרף ספציפית ל-{company}?",
                "category": "מוטיבציה והתאמה",
                "why_asked": "בדיקת בדיקה מקדימה על החברה ומוטיבציה אישית.",
                "star_answer": f"קראתי על הפעילות והצמיחה של {company}. אני רואה כאן הזדמנות לשלב את הרקע שלי בכלכלה וניתוח תפעולי בחברה דינמית, לעבוד עם צוות מקצועי ולהביא ערך מוסף אמיתי מהיום הראשון."
            }
        ],
        "questions_to_ask_interviewer": [
            f"מהם האתגרים הפיננסיים/תפעוליים המרכזיים שמחלקת הכלכלה ב-{company} מתמודדת איתם ברבעון הקרוב?",
            "איך נראה יום טיפוסי בתפקיד ואיך מוגדרת הצלחה ב-6 החודשים הראשונים?",
            "אילו מערכות וטכנולוגיות נמצאות כרגע בשימוש עיקרי במחלקה (ERP, BI, כלי אוטומציה)?"
        ],
        "insider_tips": [
            "הפגיני התלהבות מנתונים: מראיינים פיננסיים אוהבים לראות מועמדים שאוהבים סדר, לוגיקה ודיוק.",
            "הביאי דוגמאות מוחשיות עם מספרים: כל פעם שאת מציינת הישג, צייני את סדר הגודל (למשל 'מעקב אחר תזרים חודשי בהיקף של מיליוני שקלים').",
            "שדרי תקשורת בינאישית חיובית: לצד הניתוח הטכני, מחפשים מישהי שנעים לעבוד איתה בצוות."
        ]
    }
