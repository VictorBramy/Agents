import re
import hashlib
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from core.scrapers.base import BaseScraper


class AllJobsScraper(BaseScraper):
    name: str = "AllJobs"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """
        Scrapes jobs from AllJobs (alljobs.co.il), Israel's largest employment marketplace.
        Parses full job cards, employer details, cities, and direct application links.
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
            url = f"https://www.alljobs.co.il/SearchResultsGuest.aspx?page=1&freetxt={encoded_term}"

            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                boards = soup.find_all("div", class_="open-board")

                for b in boards[:25]:
                    container_id = b.get("id", "")
                    jid = "".join(filter(str.isdigit, container_id))

                    top = b.find("div", class_="job-content-top")
                    if not top:
                        continue

                    # Title extraction
                    title = ""
                    h2 = top.find("h2")
                    if h2:
                        title = h2.get_text(strip=True)
                    else:
                        title_div = top.find(class_=lambda c: c and "job-content-top-title" in str(c))
                        if title_div:
                            title = title_div.get_text(strip=True)

                    if not title or len(title) < 2:
                        continue

                    # Company extraction
                    company = ""
                    comp_a = top.find("a", href=lambda h: h and ("/Employer/" in h or "/Mador/" in h))
                    if comp_a:
                        company = comp_a.get_text(strip=True)
                    if not company:
                        t14 = top.find(class_="T14")
                        if t14:
                            company = t14.get_text(strip=True)
                    if not company:
                        company = "חברה חסויה / מובילה"

                    # Location extraction
                    loc_div = top.find(class_=lambda c: c and "job-content-top-location" in str(c))
                    job_loc = loc_div.get_text(strip=True).replace("מיקום המשרה:", "").strip() if loc_div else "ישראל"

                    # Description extraction
                    desc_div = top.find("div", id=lambda i: i and i.startswith("job-body-content"))
                    desc = desc_div.get_text(strip=True) if desc_div else f"{title} ב{company}"

                    # Date extraction
                    date_div = top.find(class_=lambda c: c and "job-content-top-date" in str(c))
                    date_str = date_div.get_text(strip=True) if date_div else "Recently"

                    job_url = f"https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID={jid}" if jid else url
                    job_hash = hashlib.md5(f"alljobs_{company}_{title}_{jid or job_url}".encode()).hexdigest()

                    if job_hash in seen_hashes:
                        continue
                    seen_hashes.add(job_hash)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "url": job_url,
                        "source": "AllJobs",
                        "description": desc[:3000],
                        "posted_date": date_str,
                        "job_hash": job_hash,
                        "is_easy_apply": 1,
                        "status": "new",
                        "language": "he"
                    })

            except Exception as e:
                print(f"[AllJobs Scraper Error for '{term}']: {e}")
                continue

        return jobs
