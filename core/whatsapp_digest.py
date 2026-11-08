import urllib.parse
from datetime import datetime
from typing import Dict, Any, List
from core.db import get_jobs, get_profile
from core.salary_estimator import estimate_job_salary

def generate_whatsapp_digest(min_score: int = 70, limit: int = 5) -> Dict[str, Any]:
    """
    Generates a high-conversion, beautifully formatted WhatsApp daily digest
    of top matched job opportunities, complete with 1-click WhatsApp send link.
    """
    profile = get_profile() or {}
    cand_name = profile.get("full_name", "ליאור אזולאי")
    if "|" in cand_name:
        cand_name = cand_name.split("|")[0].strip()

    jobs = get_jobs(status="all")
    # Filter by score and sort descending
    top_jobs = [j for j in jobs if (j.get("match_score") or 0) >= min_score]
    top_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    top_jobs = top_jobs[:limit]

    date_str = datetime.now().strftime("%d/%m/%Y")

    lines = [
        f"🎯 *סיכום משרות יומי חם עבור {cand_name}*",
        f"📅 {date_str} | *Smart Job Hunter AI*",
        f"נמצאו {len(top_jobs)} משרות בהתאמה מעולה עבורך:\n"
    ]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for i, job in enumerate(top_jobs):
        emo = emojis[i] if i < len(emojis) else "🔹"
        title = job.get("title", "")
        company = job.get("company", "")
        loc = job.get("location") or "ישראל"
        score = job.get("match_score", 0)
        url = job.get("url") or ""

        # Estimate salary
        sal = estimate_job_salary(title, job.get("description", ""), company)

        lines.append(f"{emo} *{title}*")
        lines.append(f"🏢 חברה: *{company}* ({loc})")
        lines.append(f"⭐ התאמה אישית: *{score}%* | 💰 שכר משוער: *{sal['short_display']}*")
        if url:
            lines.append(f"🔗 קישור להגשה: {url}")
        lines.append("")

    lines.append("🚀 _הופק אוטומטית ע\"י סוכן מציאת העבודה האישי_")
    text_content = "\n".join(lines)

    # Encode for WhatsApp URL
    encoded_text = urllib.parse.quote(text_content)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"

    return {
        "text": text_content,
        "whatsapp_url": whatsapp_url,
        "jobs_count": len(top_jobs),
        "generated_at": date_str
    }
