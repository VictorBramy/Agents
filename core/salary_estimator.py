import re
from typing import Dict, Any, Optional

# Israeli Market Salary Benchmarks (ILS Gross per month)
# Calibrated for Finance, Economics, Business Analysis & High-Tech
BASE_SALARY_TABLE = {
    "junior_economist": {"min": 12000, "max": 15500, "label": "כלכלן / כלכלנית מתחיל/ה"},
    "financial_analyst": {"min": 14500, "max": 18500, "label": "אנליסט פיננסי"},
    "fpa_analyst": {"min": 17000, "max": 23000, "label": "כלכלן / אנליסט FP&A"},
    "business_analyst": {"min": 14000, "max": 19000, "label": "אנליסט עסקי / תפעולי"},
    "pricing_analyst": {"min": 15500, "max": 21000, "label": "אנליסט תמחור והכנסות"},
    "budget_controller": {"min": 16000, "max": 22000, "label": "בקר תקציב ו-P&L"},
    "data_analyst": {"min": 15000, "max": 20000, "label": "אנליסט נתונים (SQL/BI)"},
    "operations_specialist": {"min": 13000, "max": 17000, "label": "תפעול עסקי ופיננסי"},
    "general_finance": {"min": 13500, "max": 17500, "label": "משרה פיננסית / כלכלית"}
}

def estimate_job_salary(title: str, description: str = "", company: str = "") -> Dict[str, Any]:
    """
    Estimates the monthly gross salary range (in ILS) for a given job posting
    based on role semantics, required technology stack, and high-tech market data.
    """
    title_lower = title.lower()
    text_lower = f"{title} {description}".lower()

    # Determine base category
    category_key = "general_finance"
    if any(k in title_lower for k in ["fp&a", "תקציב", "תזרים", "controlling"]):
        category_key = "fpa_analyst"
    elif any(k in title_lower for k in ["pricing", "תמחור", "revops", "revenue"]):
        category_key = "pricing_analyst"
    elif any(k in title_lower for k in ["פיננס", "financial analyst", "כספ"]):
        category_key = "financial_analyst"
    elif any(k in title_lower for k in ["עסק", "business analyst", "bi analyst"]):
        category_key = "business_analyst"
    elif any(k in title_lower for k in ["נתונים", "data analyst", "sql analyst"]):
        category_key = "data_analyst"
    elif any(k in title_lower for k in ["כלכל", "economist"]):
        category_key = "junior_economist"
    elif any(k in title_lower for k in ["תפעול", "operation"]):
        category_key = "operations_specialist"

    base = BASE_SALARY_TABLE[category_key]
    min_sal = base["min"]
    max_sal = base["max"]
    factors = []

    # Premium for tech / multinational companies
    tech_giants = ["taboola", "appsflyer", "riskified", "gong", "similarweb", "pagaya", "forter", "monday", "lemonade"]
    if any(comp in company.lower() for comp in tech_giants) or any(t in text_lower for t in ["saas", "fintech", "high-tech", "הייטק", "היי-טק"]):
        min_sal = int(min_sal * 1.12)
        max_sal = int(max_sal * 1.12)
        factors.append("פרמיית חברת הייטק / גלובלית (+12%)")

    # Premium for advanced technical skills
    if any(s in text_lower for s in ["sql", "python", "power bi", "tableau"]):
        min_sal = int(min_sal * 1.08)
        max_sal = int(max_sal * 1.08)
        factors.append("דרישה לכלים טכנולוגיים מתקדמים (SQL/BI) (+8%)")

    # Premium for complex ERP / SAP systems
    if any(s in text_lower for s in ["sap", "netsuite", "priority", "erp"]):
        min_sal = int(min_sal * 1.05)
        max_sal = int(max_sal * 1.05)
        factors.append("דרישה למערכות ERP / SAP מורכבות (+5%)")

    # Round to hundreds
    min_sal = round(min_sal, -2)
    max_sal = round(max_sal, -2)

    return {
        "min_salary": min_sal,
        "max_salary": max_sal,
        "currency": "₪",
        "period": "חודשי (ברוטו)",
        "display_range": f"{min_sal:,} - {max_sal:,} ₪",
        "short_display": f"{int(min_sal/1000)}K-{int(max_sal/1000)}K ₪",
        "confidence": "גבוהה (מבוסס סקרי שכר הייטק ופיננסים)",
        "role_category": base["label"],
        "factors": factors
    }
