import re
import time
import hashlib
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from core.scrapers.base import BaseScraper
from core.linkedin_session import get_linkedin_status, get_linkedin_browser_context

class LinkedinScraper(BaseScraper):
    name: str = "LinkedIn"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """
        Searches LinkedIn jobs.
        If LinkedIn account is connected, runs Authenticated Search with live applied status tracking.
        Otherwise falls back to public Guest search.
        """
        status = get_linkedin_status()
        if status.get("is_connected"):
            print("[LinkedIn Scraper] Detected authenticated LinkedIn connection. Running authenticated search...")
            try:
                return self._search_authenticated(keywords, location)
            except Exception as e:
                print(f"[LinkedIn Authenticated Search Failed, falling back]: {e}")

        print("[LinkedIn Scraper] Running public search...")
        return self._search_public(keywords, location)

    def _search_authenticated(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """Authenticated search using Playwright and saved LinkedIn session."""
        jobs = []
        search_terms = keywords[:3] if keywords else ["Junior Economist", "Financial Analyst"]

        with sync_playwright() as p:
            browser, context = get_linkedin_browser_context(p, headless=True)
            page = context.new_page()

            for term in search_terms:
                encoded_kw = urllib.parse.quote(term)
                encoded_loc = urllib.parse.quote(location)

                # Search both Easy Apply and All Jobs
                queries = [
                    (f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}&location={encoded_loc}&f_AL=true", 1),
                    (f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}&location={encoded_loc}", 0)
                ]

                for url, is_easy_query in queries:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=25000)
                        time.sleep(2)

                        # Gentle scroll to trigger infinite scroll cards
                        for _ in range(2):
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                            time.sleep(0.8)

                        cards = page.locator("div.base-card, div.job-search-card, li.jobs-search-results__list-item, div.job-card-container").all()
                        print(f"[LinkedIn Auth] Query '{term}' (EasyApply={is_easy_query}) found {len(cards)} cards")

                        for c in cards[:25]:
                            try:
                                title_el = c.locator("h3, a.job-card-list__title, h4").first
                                title = title_el.inner_text().strip() if title_el.is_visible(timeout=500) else ""

                                comp_el = c.locator("h4, a.job-card-container__primary-description, div.job-card-container__primary-description, span.job-card-container__primary-description").first
                                company = comp_el.inner_text().strip() if comp_el.is_visible(timeout=500) else ""

                                loc_el = c.locator("span.job-search-card__location, li.job-card-container__metadata-item").first
                                job_loc = loc_el.inner_text().strip() if loc_el.is_visible(timeout=500) else location

                                link_el = c.locator("a.base-card__full-link, a.job-card-list__title, a[href*='/jobs/view/']").first
                                href = link_el.get_attribute("href") if link_el.is_visible(timeout=500) else ""
                                if href and "?" in href:
                                    href = href.split("?")[0]

                                card_text = c.inner_text().lower()

                                # 1. Check if Easy Apply
                                is_easy = is_easy_query or ("easy apply" in card_text or "הגשה מהירה" in card_text)

                                # 2. Check if already applied on LinkedIn!
                                is_applied = any(w in card_text for w in ["applied", "הגשת מועמדות", "הוגשה מועמדות", "מועמדות הוגשה"])

                                if title and company:
                                    job_hash = hashlib.md5(f"linkedin_{company}_{title}_{href}".encode()).hexdigest()
                                    jobs.append({
                                        "title": title,
                                        "company": company,
                                        "location": job_loc,
                                        "url": href,
                                        "source": "LinkedIn",
                                        "description": f"{title} position at {company} located in {job_loc}. Relevant duties involve financial analysis, operational execution, reporting and cross-functional collaboration.",
                                        "posted_date": "Recently",
                                        "job_hash": job_hash,
                                        "is_easy_apply": 1 if is_easy else 0,
                                        "status": "applied" if is_applied else "new"
                                    })
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"[LinkedIn Auth Query Error for '{term}']: {e}")
                        continue

            context.close()
            browser.close()

        return jobs

    def _search_public(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """Public search fallback when no authenticated account is connected."""
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,he;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        search_terms = keywords[:3] if keywords else ["Junior Economist", "Financial Analyst"]

        for term in search_terms:
            encoded_keywords = urllib.parse.quote(term)
            encoded_location = urllib.parse.quote(location)
            
            search_variants = [
                (f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_keywords}&location={encoded_location}&f_AL=true&start=0", 1),
                (f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_keywords}&location={encoded_location}&start=0", 0)
            ]

            for url, is_easy in search_variants:
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("li")
                    if not cards:
                        cards = soup.find_all("div", class_="base-card")

                    for card in cards[:15]:
                        title_elem = card.find(["h3", "h4"], class_=lambda c: c and "title" in c)
                        comp_elem = card.find(["h4", "a"], class_=lambda c: c and "subtitle" in c)
                        loc_elem = card.find("span", class_=lambda c: c and "location" in c)
                        link_elem = card.find("a", class_=lambda c: c and ("link" in c or "title" in c))
                        time_elem = card.find("time")

                        title = title_elem.get_text(strip=True) if title_elem else ""
                        company = comp_elem.get_text(strip=True) if comp_elem else ""
                        job_loc = loc_elem.get_text(strip=True) if loc_elem else "Israel"
                        job_url = link_elem.get("href", "") if link_elem else ""
                        posted_date = time_elem.get_text(strip=True) if time_elem else "Recently"

                        if title and company:
                            if "?" in job_url:
                                job_url = job_url.split("?")[0]
                                
                            job_hash = hashlib.md5(f"linkedin_{company}_{title}_{job_url}".encode()).hexdigest()
                            
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": job_loc,
                                "url": job_url,
                                "source": "LinkedIn",
                                "description": f"{title} position at {company} located in {job_loc}. Relevant duties involve financial analysis, operational execution, reporting and cross-functional collaboration.",
                                "posted_date": posted_date,
                                "job_hash": job_hash,
                                "is_easy_apply": is_easy,
                                "status": "new"
                            })
                except Exception as e:
                    print(f"[LinkedIn Scraper Error for '{term}']: {e}")
                    continue

        return jobs
