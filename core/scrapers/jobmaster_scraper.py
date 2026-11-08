import re
import hashlib
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from core.scrapers.base import BaseScraper


class JobMasterScraper(BaseScraper):
    name: str = "JobMaster"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """
        Scrapes jobs from JobMaster (jobmaster.co.il), Israel's leading portal for
        economics, finance, accounting, and business operations roles.
        """
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        hebrew_terms = []
        for kw in keywords:
            if any("\u0590" <= c <= "\u05ea" for c in kw):
                for part in re.split(r'[/,]', kw):
                    clean = part.strip()
                    if clean and len(clean) > 2 and clean not in hebrew_terms:
                        hebrew_terms.append(clean)
            elif any(term in kw.lower() for term in ["economist", "analyst", "finance", "budget", "operations"]):
                hebrew_terms.append(kw.strip())

        if not hebrew_terms:
            hebrew_terms = ["כלכלן", "אנליסט פיננסי", "כלכלנית"]

        search_terms = hebrew_terms[:3]
        seen_hashes = set()

        for term in search_terms:
            encoded_term = urllib.parse.quote(term)
            url = f"https://www.jobmaster.co.il/jobs/?q={encoded_term}"

            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                articles = soup.find_all("article")
                if not articles:
                    articles = soup.find_all("div", class_=lambda c: c and "JobItem" in c)

                for a in articles[:25]:
                    header = a.find(class_=lambda c: c and "CardHeader" in str(c)) or a.find(["h2", "h3"])
                    title = header.get_text(strip=True) if header else ""
                    if not title:
                        continue

                    comp_el = a.find(class_=lambda c: c and "ByTitle" in str(c))
                    company = comp_el.get_text(strip=True) if comp_el else "חברה מובילה"

                    loc_el = a.find(class_=lambda c: c and "jobLocation" in str(c))
                    job_loc = loc_el.get_text(strip=True) if loc_el else "ישראל"

                    desc_el = a.find(class_=lambda c: c and "jobShortDescription" in str(c))
                    desc = desc_el.get_text(strip=True) if desc_el else f"{title} ב{company}"

                    link_el = a.find("a", href=lambda h: h and ("/jobs/" in h or "checknum" in h))
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        job_url = "https://www.jobmaster.co.il" + href if href.startswith("/") else href
                    else:
                        job_url = url

                    data_jobnum = a.get("data-jobnum") or ""
                    job_hash = hashlib.md5(f"jobmaster_{company}_{title}_{data_jobnum or job_url}".encode()).hexdigest()

                    if job_hash in seen_hashes:
                        continue
                    seen_hashes.add(job_hash)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "url": job_url,
                        "source": "JobMaster",
                        "description": desc[:3000],
                        "posted_date": "Recently",
                        "job_hash": job_hash,
                        "is_easy_apply": 1,
                        "status": "new",
                        "language": "he"
                    })

            except Exception as e:
                print(f"[JobMaster Scraper Error for '{term}']: {e}")
                continue

        return jobs
