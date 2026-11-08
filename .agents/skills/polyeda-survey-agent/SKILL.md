---
name: polyeda-survey-agent
description: Autonomous survey completion agent for Israeli reward panel Polyeda / Project Midgam (panelview@polyeda.com). Connects via IMAP to Gmail, detects new survey invites, navigates via Playwright, and solves questionnaires with Google Gemini AI and demographic consistency.
---

# 📋 Polyeda / Panel View Survey Auto-Agent (Antigravity Skill)

This skill enables Antigravity to autonomously connect to your Gmail, find survey invitation emails from **`panelview@polyeda.com`**, and use **Playwright** + **Google Gemini AI** to fill out and submit the surveys.

## 🎯 Capabilities

1. **Gmail IMAP Connection**:
   - Searches `INBOX` for emails from `panelview@polyeda.com`.
   - Extracts personalized survey URLs, reward points, and subject lines.
   - Saves detected surveys to `data/surveys.db`.

2. **Demographic Screening Consistency**:
   - Maintains an authentic, consistent demographic profile (Lior Azulay, Age 27, Female, Tel Aviv, Economist, Secular, Full-time employee).
   - Automatically answers screening filters (birth year, gender, marital status, income, district).

3. **Autonomous AI Survey Answering**:
   - Detects question types (Radio buttons, Checkboxes, Dropdowns, Likert matrix rating tables, Text inputs).
   - Uses Google Gemini AI to analyze Hebrew survey questions and select natural, consistent responses.

4. **Playwright Navigation & Form Submission**:
   - Locates Next/Submit buttons ("המשך", "הבא", "סיום", "אישור").
   - Simulates human pacing.
   - Detects completion and captures full-page screenshot verification.

## 🛠️ Usage Commands

- **Check emails & solve pending surveys**:
  ```bash
  python -m survey_agent.runner --check-once
  ```

- **Run continuously in background (Daemon mode)**:
  ```bash
  python -m survey_agent.runner --daemon --interval 15
  ```

- **Solve a specific survey link directly**:
  ```bash
  python -m survey_agent.runner --url "https://www.panelview.co.il/..." --no-headless
  ```
