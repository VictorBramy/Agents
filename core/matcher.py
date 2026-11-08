import os
import re
import json
from typing import Dict, Any, List, Tuple, Optional
from core.db import get_profile, get_setting, detect_language

def _extract_skill_tokens(skill_str: str) -> List[str]:
    """Extracts searchable keywords and acronyms from a complex skill string."""
    tokens = [skill_str.lower()]
    # Extract text inside parentheses, e.g. "Excel מתקדם (Pivot, XLOOKUP)" -> "pivot", "xlookup"
    parens = re.findall(r'\((.*?)\)', skill_str)
    for p in parens:
        tokens.extend([item.strip().lower() for item in re.split(r'[,/]', p) if item.strip()])
    # Extract individual words of length >= 3
    words = re.findall(r'[\w\u0590-\u05fe]{3,}', skill_str.lower())
    tokens.extend(words)
    return list(dict.fromkeys(tokens))

def calculate_match(job_title: str, job_description: str, profile: Dict[str, Any]) -> Tuple[int, List[str], List[str], str]:
    """
    Computes a match score (0-100), matching skills, missing skills, and match explanation.
    Tailored for cross-domain matching (Economics, Finance, Business Analysis, Tech).
    """
    if not profile:
        return 50, [], [], "פרופיל קורות חיים טרם הועלה. מומלץ להעלות קו\"ח לקבלת ניתוח מדויק."

    candidate_skills = profile.get("skills", [])
    target_roles = [r.lower() for r in profile.get("target_roles", [])]
    full_text = f"{job_title} {job_description}".lower()

    # 1. Title Similarity Score (up to 45 pts)
    title_score = 15
    job_title_lower = job_title.lower()

    # Domain Negative Keywords: immediate disqualification for unrelated fields
    negative_patterns = [
        r'\b(אסותא|כלניות|מרפאה|רפואי|אחות|רופא|קליניקה|מכבי|כללית)\b',
        r'\b(מחצבה|חומרי בניין|נהג|שינוע|מלגזן|מאבטח|שמירה)\b',
        r'\b(devops engineer|cloud security|hardware engineer|embedded|firmware)\b',
    ]
    is_negative = False
    for neg_pat in negative_patterns:
        if re.search(neg_pat, job_title_lower, re.IGNORECASE):
            is_negative = True
            break
            
    if is_negative:
        return 25, [], [], "המשרה אינה תואמת את היעדים המקצועיים שלך (תחום רפואי/תפעול פיזי/תשתיות טכניות טהורות)."

    # Domain Negative Keywords: immediate disqualification for unrelated fields
    negative_patterns = [
        r'\b(אסותא|כלניות|מרפאה|רפואי|אחות|רופא|קליניקה|מכבי|כללית)\b',
        r'\b(מחצבה|חומרי בניין|נהג|שינוע|מלגזן|מאבטח|שמירה)\b',
        r'\b(devops engineer|cloud security|hardware engineer|embedded|firmware)\b',
    ]
    is_negative = False
    for neg_pat in negative_patterns:
        if re.search(neg_pat, job_title_lower, re.IGNORECASE):
            is_negative = True
            break
            
    if is_negative:
        return 25, [], [], "המשרה אינה תואמת את היעדים המקצועיים שלך (תחום רפואי/תפעול פיזי/תשתיות טכניות טהורות)."

    # Domain Negative Keywords: immediate disqualification for unrelated fields
    negative_patterns = [
        r'\b(אסותא|כלניות|מרפאה|רפואי|אחות|רופא|קליניקה|מכבי|כללית)\b',
        r'\b(מחצבה|חומרי בניין|נהג|שינוע|מלגזן|מאבטח|שמירה)\b',
        r'\b(devops engineer|cloud security|hardware engineer|embedded|firmware)\b',
    ]
    is_negative = False
    for neg_pat in negative_patterns:
        if re.search(neg_pat, job_title_lower, re.IGNORECASE):
            is_negative = True
            break
            
    if is_negative:
        return 25, [], [], "המשרה אינה תואמת את היעדים המקצועיים שלך (תחום רפואי/תפעול פיזי/תשתיות טכניות טהורות)."

    # Domain Negative Keywords: immediate disqualification for unrelated fields
    negative_patterns = [
        r'\b(אסותא|כלניות|מרפאה|רפואי|אחות|רופא|קליניקה|מכבי|כללית)\b',
        r'\b(מחצבה|חומרי בניין|נהג|שינוע|מלגזן|מאבטח|שמירה)\b',
        r'\b(devops engineer|cloud security|hardware engineer|embedded|firmware)\b',
    ]
    is_negative = False
    for neg_pat in negative_patterns:
        if re.search(neg_pat, job_title_lower, re.IGNORECASE):
            is_negative = True
            break
            
    if is_negative:
        return 25, [], [], "המשרה אינה תואמת את היעדים המקצועיים שלך (תחום רפואי/תפעול פיזי/תשתיות טכניות טהורות)."

    # Domain Negative Keywords: immediate disqualification for unrelated fields
    negative_patterns = [
        r'\b(אסותא|כלניות|מרפאה|רפואי|אחות|רופא|קליניקה|מכבי|כללית)\b',
        r'\b(מחצבה|חומרי בניין|נהג|שינוע|מלגזן|מאבטח|שמירה)\b',
        r'\b(devops engineer|cloud security|hardware engineer|embedded|firmware)\b',
    ]
    is_negative = False
    for neg_pat in negative_patterns:
        if re.search(neg_pat, job_title_lower, re.IGNORECASE):
            is_negative = True
            break
            
    if is_negative:
        return 25, [], [], "המשרה אינה תואמת את היעדים המקצועיים שלך (תחום רפואי/תפעול פיזי/תשתיות טכניות טהורות)."

    # Semantic stem groups for Economics, Finance, and Analysis
    domain_roots = {
        "econ": ["כלכל", "כלכלה", "econom", "macro", "micro"],
        "finance": ["פיננס", "כספ", "financ", "fp&a", "treasury", "גזבר", "pricing", "תמחור", "credit", "אשראי", "invest", "השקע"],
        "analyst": ["אנליסט", "analyst", "analytic", "אנליז", "מחקר", "research", "forecast", "תחזית", "controlling"],
        "budget": ["תקציב", "budget", "p&l", "תזרים", "cash flow", "בקרת"],
        "operations": ["תפעול", "operation", "מלאי", "supply", "אספקה", "logistics"],
        "business": ["עסק", "business", "commercial", "trade", "מסחר", "sales", "מכירות"],
        "data": ["נתונים", "data", "sql", "excel", "python", "bi", "דוחות", "reports"]
    }

    # Count matching domain roots with strict word boundaries
    matched_domains = set()
    for domain, stems in domain_roots.items():
        for stem in stems:
            # Require word boundary or prefix match for Hebrew & English
            pattern = r'(?:\b|[^\w\u0590-\u05fe])' + re.escape(stem) + r'(?:\b|[^\w\u0590-\u05fe]|ים|ות|ת|י)'
            if re.search(pattern, job_title_lower):
                matched_domains.add(domain)
                break

    # Check against candidate's target roles
    for role in target_roles:
        role_clean = re.sub(r'[\(\)/\-]', ' ', role.lower())
        role_words = [w for w in role_clean.split() if len(w) >= 3]
        matches_count = sum(1 for w in role_words if w in job_title_lower)
        if matches_count >= 2:
            title_score = 45
            break
        elif matches_count == 1:
            title_score = max(title_score, 35)

    # If domain roots matched strongly
    if ("econ" in matched_domains or "finance" in matched_domains) and "analyst" in matched_domains:
        title_score = max(title_score, 45)
    elif "econ" in matched_domains or "finance" in matched_domains or "analyst" in matched_domains:
        title_score = max(title_score, 38)
    elif "budget" in matched_domains or "business" in matched_domains or "operations" in matched_domains:
        title_score = max(title_score, 32)

    # 2. Skill overlap
    matching = []
    for skill in candidate_skills:
        skill_tokens = _extract_skill_tokens(skill)
        # Check if any token of this skill appears in the job description or title
        for tok in skill_tokens:
            if len(tok) < 3:
                continue
            pattern = r'(?:\b|[^\w\u0590-\u05fe])' + re.escape(tok) + r'(?:\b|[^\w\u0590-\u05fe])'
            if re.search(pattern, full_text):
                matching.append(skill)
                break

    matching = list(dict.fromkeys(matching))

    # Inferred domain skills if job description is brief (e.g. from LinkedIn cards)
    if len(matching) < 2:
        if "econ" in matched_domains:
            for s in candidate_skills:
                if any(k in s.lower() for k in ["excel", "כלכל", "financial", "p&l"]):
                    matching.append(s)
        elif "finance" in matched_domains or "analyst" in matched_domains:
            for s in candidate_skills:
                if any(k in s.lower() for k in ["excel", "פיננס", "financial", "תזרים", "cash flow", "erp", "sap"]):
                    matching.append(s)
    matching = list(dict.fromkeys(matching))

    # 3. Missing skills / potential requirements
    from core.cv_parser import COMMON_SKILLS
    job_required_skills = []
    for skill in COMMON_SKILLS:
        pattern = r'(?:\b|[^\w\u0590-\u05fe])' + re.escape(skill.lower()) + r'(?:\b|[^\w\u0590-\u05fe])'
        if re.search(pattern, full_text):
            job_required_skills.append(skill)

    cand_all_tokens = set()
    for s in candidate_skills:
        cand_all_tokens.update(_extract_skill_tokens(s))

    missing = [s for s in job_required_skills if s.lower() not in cand_all_tokens][:4]

    # 4. Skill match score (up to 45 pts)
    skill_score = min(len(matching) * 12, 45)

    # 5. Seniority bonus (up to 10 pts)
    seniority_score = 10
    cand_sen = profile.get("seniority", "Junior / Entry-Level").lower()
    if any(s in job_title_lower for s in ["senior", "lead", "principal", "head of", "director", "בכיר"]):
        seniority_score = 0
    elif any(s in job_title_lower for s in ["junior", "entry", "מתחיל", "בוגר", "סטודנט"]):
        seniority_score = 10

    total_score = min(max(title_score + skill_score + seniority_score, 30), 96)

    # Match explanation
    top_matches_str = ', '.join([s.split('(')[0].strip() for s in matching[:3]])
    if total_score >= 80:
        reason = f"התאמה גבוהה ביותר! המשרה תואמת את היעד המקצועי שלך וכוללת שימוש בכישורים מרכזיים ({top_matches_str or 'ניתוח נתונים ופיננסים'})."
    elif total_score >= 60:
        reason = f"התאמה טובה. קיימת זיקה ישירה לרקע שלך ({top_matches_str or 'כלכלה ותפעול'}), עם פוטנציאל למינוף הניסיון ב-Excel ו-ERP."
    else:
        reason = f"התאמה בסיסית. המשרה עשויה לדרוש חיזוק בתחומים כגון {', '.join(missing) if missing else 'דרישות ספציפיות של הארגון'}."

    return total_score, matching, missing, reason


def generate_cover_letter(job: Dict[str, Any], profile: Dict[str, Any], language: Optional[str] = None) -> str:
    """
    Generates a tailored cover letter in Hebrew or English.
    Automatically matches the language of the job posting if not explicitly specified.
    """
    job_title = job.get("title", "Open Position")
    company = job.get("company", "the company")
    job_desc = job.get("description", "")
    matching_skills = job.get("matching_skills", [])

    # Automatic language selection matching the job
    if not language or language == "auto":
        language = job.get("language") or detect_language(job_title + " " + job_desc)

    cand_name = profile.get("full_name", "ליאור אזולאי")
    # Clean candidate name if it has a pipe like "ליאור אזולאי | Lior Azulay"
    if "|" in cand_name:
        parts = [p.strip() for p in cand_name.split("|")]
        cand_name = parts[0] if language == "he" else (parts[1] if len(parts) > 1 else parts[0])

    cand_exp = profile.get("years_of_experience", 3.5)
    cand_summary = profile.get("summary_he" if language == "he" else "summary_en") or profile.get("summary", "")
    cand_skills_list = [s.split('(')[0].strip() for s in profile.get("skills", [])[:6]]
    cand_skills_str = ", ".join(cand_skills_list)
    matching_str = ", ".join([s.split('(')[0].strip() for s in matching_skills[:4]]) if matching_skills else cand_skills_str

    api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

    if api_key and len(api_key.strip()) > 10:
        try:
            from google import genai
            client = genai.Client(api_key=api_key.strip())
            
            prompt = f"""
You are an expert career consultant, executive recruiter, and professional copywriter.
Write an authentic, highly convincing and personalized cover letter / introductory message from {cand_name} applying for the position of "{job_title}" at "{company}".

Candidate Details:
- Name: {cand_name}
- Candidate Summary: {cand_summary}
- Estimated Experience: ~{cand_exp} years
- Core Skills & Expertise: {cand_skills_str}
- Matching Strengths for this role: {matching_str}

Job Details:
- Title: {job_title}
- Company: {company}
- Job Description:
{job_desc[:2500]}

Requirements:
- Target Language: {"Hebrew (עברית שוטפת ומקצועית)" if language == "he" else "English (Professional and engaging)"}
- Tone: Professional, articulate, results-driven, respectful, highlighting how the candidate's real background and hands-on strengths solve the company's needs.
- Format: 3-4 clean paragraphs with greeting, relevant achievements/skills, interest in company, and polite closing with contact readiness.
- Do NOT use markdown code blocks or triple backticks. Return the letter directly.
"""
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"[Cover Letter LLM Error]: {e}, falling back to template")

    # Smart template fallback tailored to candidate's domain
    if language == "he":
        letter = f"""שלום רב לצוות הגיוס ב-{company},

אני פונה אליכם בהמשך לפרסום משרת **{job_title}**. 
לאחר שעיינתי בדרישות התפקיד ובפעילות של {company}, מצאתי התאמה גבוהה בין הניסיון המעשי שלי לבין יעדי המחלקה.

אני בוגרת תואר ראשון (.B.A) בכלכלה וניהול, ובעלת כ-{cand_exp} שנות ניסיון מעשי בתפעול פיננסי, אנליזה עסקית, ניהול תזרים מזומנים (Cash Flow), בקרת תקציב ודוחות רווח והפסד (P&L). במסגרת עבודתי צברתי שליטה יומיומית באקסל מתקדם, עבודה מול מערכות ERP ו-SAP, וכלים לניתוח נתונים (SQL ו-Python). 

היכולת שלי לשלב ראייה עסקית רחבה עם ירידה לפרטים, ניתוח נתונים מעמיק והנעה לפעולה תאפשר לי להשתלב במהירות בצוות ולתרום תרומה משמעותית מהיום הראשון.

אשמח מאוד לקבוע שיחה כדי להציג את התאמתי ולהכיר אתכם טוב יותר.
קורות החיים שלי מצורפים לעיונכם.

בברכה,
{cand_name}
"""
    else:
        letter = f"""Dear Hiring Team at {company},

I am writing to express my strong interest in the **{job_title}** position at {company}. Having reviewed the role and requirements, I believe my background in Economics, financial operations, and data analysis aligns directly with your team's objectives.

I hold a B.A. in Economics & Management and bring ~{cand_exp} years of practical experience managing financial operations, cash flow, budget tracking, and P&L monitoring. My daily toolkit includes advanced Excel modeling, ERP and SAP systems, alongside an academic foundation in SQL and Python for data analysis.

I am particularly excited about {company} and would welcome the opportunity to bring my analytical rigor, proactive approach, and operational mindset to your team.

Thank you for your time and consideration. I look forward to discussing how my experience can contribute to your goals.

Best regards,
{cand_name}
"""
    return letter
