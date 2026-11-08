import os
import re
import json
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from pypdf import PdfReader
from core.db import save_profile, get_setting, detect_language

# Broad skill set across Tech, Data, Finance, Economics, Product & Operations
COMMON_SKILLS = [
    # Finance, Economics, Business Analysis
    "Excel", "Advanced Excel", "Pivot Tables", "VLOOKUP", "XLOOKUP", "Financial Analysis",
    "Cash Flow", "Cash Flow Management", "Budget Tracking", "P&L", "Financial Modeling",
    "Pricing", "Cost Reduction", "Cost Analysis", "Business Analysis", "Operations",
    "SAP", "ERP", "Sales Analysis", "Accounting", "Forecasting", "MS Project",
    "Power BI", "Tableau",
    
    # Data & Programming
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Python", "Pandas", "NumPy",
    "Matplotlib", "Data Analysis", "Data Visualization", "Machine Learning", "LLM",
    
    # Software Engineering & DevOps
    "JavaScript", "TypeScript", "React", "Node.js", "Vue", "Angular", "Next.js",
    "FastAPI", "Django", "Flask", "Go", "Java", "Spring Boot", "C#", ".NET", "C++",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Git", "CI/CD", "Linux"
]

HEBREW_ROLES_MAP = {
    # Economics & Finance
    "כלכלן": "כלכלן / Junior Economist",
    "כלכלנית": "כלכלנית / Junior Economist",
    "אנליסט פיננסי": "אנליסט פיננסי (Financial Analyst)",
    "אנליסטית פיננסית": "אנליסטית פיננסית (Financial Analyst)",
    "אנליסט עסקי": "אנליסט עסקי (Business Analyst)",
    "אנליסטית עסקית": "אנליסטית עסקית (Business Analyst)",
    "תפעול עסקי": "אנליסט תפעול עסקי (Operations Analyst)",
    "תפעול פיננסי": "אנליסט תפעול פיננסי (Financial Operations)",
    "בקרת תקציב": "אנליסט תקציב ובקרה (Budget Analyst)",
    "תקציב": "אנליסט תקציב (Budget Analyst)",
    
    # Tech & Software
    "פול סטאק": "Full Stack Developer",
    "בקאנד": "Backend Developer",
    "צד שרת": "Backend Developer",
    "פרונטאנד": "Frontend Developer",
    "צד לקוח": "Frontend Developer",
    "מהנדס תוכנה": "Software Engineer",
    "מהנדסת תוכנה": "Software Engineer",
    "מפתח תוכנה": "Software Engineer",
    "מפתחת תוכנה": "Software Engineer",
    "פייתון": "Python Developer",
    "דבאופס": "DevOps Engineer",
    "נתונים": "Data Analyst / Engineer",
    "מדען נתונים": "Data Scientist",
    "מוצר": "Product Manager",
    "בדיקות": "QA Engineer"
}

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts text from PDF, with fallback to Gemini multimodal if fonts are corrupted."""
    text_parts = []
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    except Exception as e:
        print(f"[pypdf extraction error]: {e}")

    raw_text = "\n".join(text_parts).strip()

    # Check if text is corrupted (many replacement characters '\ufffd' or empty)
    corrupted = (raw_text.count('\ufffd') > 15) or len(raw_text.strip()) < 80

    if corrupted:
        print("[Notice] PDF font appears unmapped or corrupted. Attempting Gemini multimodal extraction...")
        api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        if api_key and len(api_key.strip()) > 10:
            try:
                from google import genai
                client = genai.Client(api_key=api_key.strip())
                # Copy to ASCII path for safe HTTP header handling
                temp_ascii = pdf_path.parent / "temp_extract_ascii.pdf"
                shutil.copyfile(pdf_path, temp_ascii)
                uploaded = client.files.upload(file=str(temp_ascii))
                res = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[uploaded, "חלץ את כל הטקסט של קורות החיים ממסמך זה במלואו בעברית ובאנגלית."]
                )
                if temp_ascii.exists():
                    temp_ascii.unlink()
                if res.text and len(res.text.strip()) > 100:
                    return res.text.strip()
            except Exception as e:
                print(f"[Gemini PDF Multimodal Extraction failed]: {e}")

    return raw_text

def rule_based_cv_parser(raw_text: str, filename: str = "", lang: str = "en") -> Dict[str, Any]:
    """Smart heuristic parser recognizing Finance, Economics, Business, and Tech."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    raw_lower = raw_text.lower()
    
    # 1. Contact Info
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
    email = email_match.group(0) if email_match else ""
    
    phone_match = re.search(r'(\+?972[- ]?|0)(5[0-9]|7[0-9]|[2-489])[- ]?[0-9]{3}[- ]?[0-9]{4}', raw_text)
    phone = phone_match.group(0) if phone_match else ""
    
    # Full Name heuristic
    full_name = ""
    for line in lines[:5]:
        if not re.search(r'@|\.com|http|resume|curriculum|cv|phone|tel|\+972|05|b\.a|bachelor|כלכלה|תואר', line, re.IGNORECASE):
            words = line.split()
            if 2 <= len(words) <= 4 and len(line) < 35:
                full_name = line
                break
    if not full_name and lines:
        full_name = lines[0]
        
    # 2. Extract Skills
    found_skills = set()
    for skill in COMMON_SKILLS:
        pattern = r'(?:\b|[^\w])' + re.escape(skill.lower()) + r'(?:\b|[^\w])'
        if re.search(pattern, raw_lower):
            found_skills.add(skill)
            
    # 3. Determine Seniority
    seniority = "Mid-Level"
    if re.search(r'\b(junior|graduate|entry|intern|student|מתחיל|מתחילה|בוגר|בוגרת|סטודנט|ג\'וניור)\b', raw_lower):
        seniority = "Junior / Entry-Level"
    elif re.search(r'\b(senior|lead|principal|head of|vp|בכיר|בכירה|סניור|ראש צוות|מוביל|מובילה)\b', raw_lower):
        seniority = "Senior"
        
    # 4. Estimate Years of Experience (focus on job timelines, NOT high school)
    exp_years = 3.0
    explicit_exp = re.findall(r'(\d+)\+?\s*(?:years|שנים|שנות)\s*(?:of|של)?\s*(?:experience|ניסיון)', raw_lower)
    if explicit_exp:
        try:
            exp_years = float(explicit_exp[0])
        except ValueError:
            pass
    else:
        # Check for job ranges like 2021-Present, 2021-היום
        job_starts = re.findall(r'(201[8-9]|202[0-5])\s*[-–—]\s*(?:present|היום|current)', raw_lower)
        if job_starts:
            start_yr = int(job_starts[0])
            exp_years = float(max(2026 - start_yr, 1))

    # 5. Determine Target Roles accurately based on actual domain
    target_roles = []
    
    # Check for Economics / Finance
    is_finance_econ = any(term in raw_lower for term in [
        "economics", "economist", "financial", "finance", "cash flow", "budget", "כלכלן", "כלכלנית", "פיננס", "תזרים", "תקציב", "רווח והפסד", "p&l"
    ])
    
    if is_finance_econ:
        target_roles.extend([
            "כלכלן / כלכלנית (Junior Economist)",
            "אנליסט/ית פיננסי/ת (Financial Analyst)",
            "אנליסט/ית עסקי/ת ותפעולי/ת (Business Operations Analyst)",
            "אנליסט/ית תקציב ובקרה (Budget Analyst)"
        ])
        
    # Check Hebrew keywords
    for he_kw, role_title in HEBREW_ROLES_MAP.items():
        if he_kw in raw_lower and role_title not in target_roles:
            target_roles.append(role_title)
            
    # Check Tech domains if applicable
    if "full stack" in raw_lower or ("react" in raw_lower and "python" in raw_lower):
        target_roles.append("Full Stack Developer")
    elif "backend" in raw_lower:
        target_roles.append("Backend Developer")
    elif "sql" in raw_lower and ("python" in raw_lower or "pandas" in raw_lower) and not is_finance_econ:
        target_roles.append("Data Analyst")
        
    target_roles = list(dict.fromkeys(target_roles))
    if not target_roles:
        target_roles = ["אנליסט נתונים / עסקי", "Business Analyst"]
        
    skills_preview = ', '.join(list(found_skills)[:6])
    if lang == "he":
        summary = f"מועמד/ת ברמת {seniority} עם כ-{int(exp_years)} שנות ניסיון מעשי ב-{skills_preview}."
    else:
        summary = f"{seniority} professional with ~{int(exp_years)} years of experience in {skills_preview}."
    
    return {
        "full_name": full_name or "Candidate",
        "email": email,
        "phone": phone,
        "cv_filename": filename,
        "raw_text": raw_text,
        "summary": summary,
        "seniority": seniority,
        "target_roles": target_roles,
        "skills": sorted(list(found_skills)),
        "years_of_experience": exp_years,
        "language": lang
    }

def llm_cv_parser(raw_text: str, filename: str, api_key: str, lang: str = "en") -> Dict[str, Any]:
    """Uses Gemini API to extract an in-depth structured candidate profile in any discipline."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are an expert HR recruiter and professional CV parser. 
Analyze the candidate's CV below with high precision. Do NOT assume the candidate is a software developer unless stated. Pay close attention to actual degrees, job titles, and duties (e.g. Economics, Finance, Business Analysis, Operations, Engineering).

Return a valid JSON object ONLY (no markdown quotes, no triple backticks):

JSON Structure:
{{
  "full_name": "Full Name",
  "email": "email address",
  "phone": "phone number",
  "summary": "Accurate 2-3 sentence executive profile summary",
  "seniority": "Junior / Entry-Level / Mid-Level / Senior",
  "target_roles": ["List of 3-5 specific matching job titles directly reflecting candidate's experience and degree"],
  "skills": ["List of specific practical skills, tools, systems, and methodologies"],
  "years_of_experience": estimated_actual_years_of_work_experience_float
}}

CV TEXT:
{raw_text[:12000]}
"""
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        resp_text = response.text.strip()
        if resp_text.startswith("```"):
            resp_text = re.sub(r"^```[a-zA-Z]*\n", "", resp_text)
            resp_text = re.sub(r"\n```$", "", resp_text)
            
        data = json.loads(resp_text)
        data["cv_filename"] = filename
        data["raw_text"] = raw_text
        data["language"] = lang
        return data
    except Exception as e:
        print(f"[LLM Parser fallback to rule-based]: {e}")
        return rule_based_cv_parser(raw_text, filename, lang)

def parse_and_save_cv(raw_text: str, filename: str = "", lang: Optional[str] = None) -> Dict[str, Any]:
    """Processes CV text, parses it via Gemini or smart domain engine, and saves to database."""
    detected_lang = lang or detect_language(raw_text)
    api_key = get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    if api_key and len(api_key.strip()) > 10:
        profile_data = llm_cv_parser(raw_text, filename, api_key.strip(), lang=detected_lang)
    else:
        profile_data = rule_based_cv_parser(raw_text, filename, lang=detected_lang)
        
    save_profile(profile_data, lang=detected_lang)
    return profile_data
