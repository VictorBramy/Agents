import re
import json
import hashlib
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from core.scrapers.base import BaseScraper


class DrushimScraper(BaseScraper):
    name: str = "Drushim"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """
        Scrapes jobs from Drushim (drushim.co.il) by extracting pre-rendered
        React TanStack Query dehydratedState from __NEXT_DATA__, with HTML fallback.
        """
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # Filter keywords suitable for Israeli job boards (Hebrew or English)
        hebrew_terms = []
        for kw in keywords:
            # Look for Hebrew terms or common finance keywords
            if any("\u0590" <= c <= "\u05ea" for c in kw):
                # Clean up complex role descriptions into searchable single terms
                for part in re.split(r'[/,]', kw):
                    clean = part.strip()
                    if clean and len(clean) > 2 and clean not in hebrew_terms:
                        hebrew_terms.append(clean)
            elif any(term in kw.lower() for term in ["economist", "analyst", "finance", "budget", "operations"]):
                hebrew_terms.append(kw.strip())

        if not hebrew_terms:
            hebrew_terms = ["כלכלן", "כלכלנית", "אנליסט פיננסי", "אנליסט תקציב"]

        # Limit to top 3 search queries to be respectful of rate limits
        search_terms = hebrew_terms[:3]
        seen_ids = set()

        for term in search_terms:
            encoded_term = urllib.parse.quote(term)
            url = f"https://www.drushim.co.il/jobs/search/{encoded_term}/"

            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    continue

                # 1. Primary Strategy: Extract structured JSON from __NEXT_DATA__
                soup = BeautifulSoup(resp.text, "html.parser")
                script_elem = soup.find("script", id="__NEXT_DATA__")
                extracted_from_next = False

                if script_elem and script_elem.string:
                    try:
                        data = json.loads(script_elem.string)
                        queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
                        for q in queries:
                            state = q.get("state", {})
                            qdata = state.get("data")
                            if isinstance(qdata, dict) and "pages" in qdata:
                                for page in qdata.get("pages", []):
                                    for j in page.get("jobs", []):
                                        jid = str(j.get("id", ""))
                                        if not jid or jid in seen_ids:
                                            continue
                                        seen_ids.add(jid)

                                        title = j.get("title", "").strip()
                                        company = j.get("companyName", "חברה מובילה").strip()
                                        city = j.get("city") or "ישראל"
                                        job_url = "https://www.drushim.co.il" + (j.get("jobUrl") or f"/job/{jid}/")
                                        desc = j.get("description", "")
                                        clean_desc = re.sub(r'<[^>]+>', ' ', desc).strip()
                                        clean_desc = re.sub(r'\s+', ' ', clean_desc)

                                        pub_date = (j.get("publishedAtIso", "")[:10]) or (j.get("publishedAt", "")) or "Recently"
                                        job_hash = hashlib.md5(f"drushim_{company}_{title}_{jid}".encode()).hexdigest()

                                        is_easy = 1 if (j.get("allowNoCv") or j.get("hasSmartFilter") or j.get("isHot")) else 0

                                        jobs.append({
                                            "title": title,
                                            "company": company,
                                            "location": city,
                                            "url": job_url,
                                            "source": "Drushim",
                                            "description": clean_desc[:3000],
                                            "posted_date": pub_date,
                                            "job_hash": job_hash,
                                            "is_easy_apply": is_easy,
                                            "status": "new",
                                            "language": "en" if j.get("isEnglish") else "he"
                                        })
                                        extracted_from_next = True
                    except Exception as err:
                        print(f"[Drushim NEXT_DATA parse error]: {err}")

                # 2. Fallback: Parse HTML cards directly if __NEXT_DATA__ was absent or empty
                if not extracted_from_next:
                    cards = soup.find_all(lambda t: t.name == "div" and any("card" in c.lower() for c in t.get("class", [])))
                    for c in cards[:20]:
                        title_el = c.find(["h2", "h3", "a"])
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        comp_el = c.find(class_=lambda cls: cls and "company" in str(cls).lower())
                        company = comp_el.get_text(strip=True) if comp_el else "חברה מובילה"
                        loc_el = c.find(class_=lambda cls: cls and "city" in str(cls).lower())
                        city = loc_el.get_text(strip=True) if loc_el else "ישראל"
                        link_el = c.find("a", href=lambda h: h and ("/job/" in h or "/jobs/" in h))
                        job_url = "https://www.drushim.co.il" + link_el.get("href") if link_el else url

                        desc_el = c.find(class_=lambda cls: cls and "desc" in str(cls).lower())
                        clean_desc = desc_el.get_text(strip=True) if desc_el else f"{title} ב{company}"

                        job_hash = hashlib.md5(f"drushim_{company}_{title}_{job_url}".encode()).hexdigest()
                        if job_hash not in seen_ids:
                            seen_ids.add(job_hash)
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": city,
                                "url": job_url,
                                "source": "Drushim",
                                "description": clean_desc[:3000],
                                "posted_date": "Recently",
                                "job_hash": job_hash,
                                "is_easy_apply": 1,
                                "status": "new",
                                "language": "he"
                            })

            except Exception as e:
                print(f"[Drushim Scraper Error for '{term}']: {e}")
                continue

        return jobs
