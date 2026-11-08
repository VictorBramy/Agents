---
name: agent-optimizer
description: Autonomous meta-agent and optimizer for Smart Job Hunter AI. Continuously audits scrapers, detects false-positive substring matches, repairs broken ATS board tokens, enhances bilingual search strategies, and refactors matching algorithms.
---

# 🤖 Agent Optimizer (Meta-Agent Skill)

This skill enables Antigravity to act as the **Meta-Agent** (הסוכן של הסוכן): an autonomous inspector and optimizer designed specifically to diagnose, benchmark, and improve the **Smart Job Hunter AI** system.

## 🎯 Core Capabilities

1. **Continuous Autonomous Thinking & Background Loop (מצב חשיבה ושיפור רציף ברקע)**:
   - Operates as a non-stop daemon thread (`core/autonomous_optimizer.py`).
   - Automatically executes improvement cycles every 10 minutes without requiring manual button clicks.
   - Streams thoughts and actions in real-time to the Web Dashboard and records them in SQLite table `meta_agent_thoughts`.

2. **Scraper Token Health & ATS Discovery (סורקים וטוקנים)**:
   - Probes Greenhouse, LinkedIn, and Israeli job boards (Drushim, JobMaster, AllJobs).
   - Detects dead (404/timeout) company tokens.
   - Discovers and validates active tech company career endpoints (e.g. Taboola, SimilarWeb, Pagaya, Forter, Gong, AppsFlyer, Riskified).

2. **Matching Engine Calibration (כיול מנוע ההתאמה)**:
   - Detects false-positive matches (such as substring collisions like "כלכ" inside "כלניות/אסותא").
   - Implements strict word boundaries (`\b`) and Hebrew prefix rules (`ים`, `ות`, `ת`, `י`).
   - Injects domain-negative keyword penalties (clinics, mining/quarry sales, physical logistics, hardware/cloud infrastructure without financial relevance).

3. **Bilingual Search Strategy (אסטרטגיה דו-לשונית)**:
   - Ensures candidate target roles are dynamically mapped between Hebrew and English.
   - Routes English tech roles to global ATSs (Greenhouse, Comeet) and Hebrew roles to Israeli boards.

4. **Database Hygiene & Rescoring (ניקוי ודירוג מחדש)**:
   - Evaluates stored jobs in `data/jobs.db`.
   - Cleans false positives, suppresses duplicates, and recalculates match scores.

5. **Self-Healing & Auto-Improvement (שדרוג אוטונומי)**:
   - Automatically writes verified improvements to `core/matcher.py`, `core/scrapers/greenhouse_scraper.py`, and `core/scrapers/aggregator.py`.
   - Tracks before/after health score deltas in SQLite `meta_agent_audits`.

## 🛠️ Usage Commands

- **Run Diagnostics via CLI**:
  ```bash
  python -c "from core.meta_agent import MetaAgent; ma = MetaAgent(); print(ma.run_audit())"
  ```

- **Run Full Auto-Optimization via CLI**:
  ```bash
  python -c "from core.meta_agent import MetaAgent; ma = MetaAgent(); print(ma.apply_optimization())"
  ```

- **Web Dashboard Integration**:
  Available under the top bar **"סוכן שיפור מתמיד (Meta AI)"** and interactive health bar on `http://127.0.0.1:8080`.
