---
name: job-hunter
description: Autonomous bilingual (Hebrew & English) AI job hunter agent for the Israeli tech market. Scans Greenhouse, Comeet, and LinkedIn jobs, matches them to candidate CVs, and generates tailored cover letters using Google AI Pro.
---

# 🎯 Smart Job Hunter AI Agent (Antigravity Native Skill)

This skill enables Antigravity to act as your autonomous job hunting agent using your **Google AI Pro** subscription directly.

## Workflow & Commands

Whenever the user asks to:
1. **Analyze or update CVs (בדיקה/עדכון קורות חיים)**:
   - Read candidate CVs from `c:\Users\A\Desktop\AGENTS\data\uploads\` or text provided in chat.
   - Extract skills, experience, and target roles in Hebrew and English.
   - Save or update profile in `c:\Users\A\Desktop\AGENTS\data\jobs.db`.

2. **Scan for tech jobs (סריקת משרות)**:
   - Run the scraper aggregator: `python -c "from core.scrapers.aggregator import run_job_search; print(run_job_search())"`
   - Present the top matched jobs directly in chat with match scores (0-100%) and reasons.

3. **Draft Tailored Cover Letter (ניסוח מכתב פנייה אישי)**:
   - Check the job language:
     - If Hebrew ➜ Draft authentic Hebrew application pitch using the candidate's Hebrew CV.
     - If English ➜ Draft compelling English cover letter using candidate's English CV.
   - Use Google AI Pro frontier reasoning for maximum persuasiveness and tailoring.
   - Save the letter to `jobs.db` so it syncs with the local Web Dashboard (`http://127.0.0.1:8080`).

4. **Automated Daily Scan (סריקה יומית ברקע)**:
   - Use the Antigravity `schedule` tool to scan for new positions every morning or on demand.
