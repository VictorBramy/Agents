import requests
import hashlib
from typing import List, Dict, Any
from core.scrapers.base import BaseScraper

# Curated list of prominent tech companies in Israel using Greenhouse
GREENHOUSE_COMPANIES = [
    {"name": "Riskified", "board": "riskified"},
    {"name": "AppsFlyer", "board": "appsflyer"},
    {"name": "Gong", "board": "gongio"},
    {"name": "Taboola", "board": "taboola"},
    {"name": "Pagaya", "board": "pagaya"},
    {"name": "SimilarWeb", "board": "similarweb"},
    {"name": "Forter", "board": "forter"},
]

class GreenhouseScraper(BaseScraper):
    name: str = "Greenhouse"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        jobs = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        keywords_lower = [k.lower() for k in keywords if len(k) > 1]
        
        for comp in GREENHOUSE_COMPANIES:
            company_name = comp["name"]
            board_token = comp["board"]
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
            
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("jobs", [])
                
                for item in items:
                    job_loc = item.get("location", {}).get("name", "")
                    # Filter for Israel or Remote or empty location
                    loc_match = any(term in job_loc.lower() for term in ["israel", "tel aviv", "herzliya", "remote", "haifa", "jerusalem"])
                    
                    job_title = item.get("title", "")
                    job_content = item.get("content", "")
                    job_text = (job_title + " " + job_content).lower()
                    
                    # Match against candidate keywords
                    is_relevant = False
                    if not keywords_lower:
                        is_relevant = True
                    else:
                        for kw in keywords_lower:
                            if kw in job_text or kw in job_title.lower():
                                is_relevant = True
                                break
                                
                    if (loc_match or not job_loc) and is_relevant:
                        clean_content = job_content.replace("&nbsp;", " ").replace("<p>", "\n").replace("</p>", "\n")
                        # Basic html tag stripping
                        import re
                        clean_content = re.sub(r'<[^>]+>', ' ', clean_content)
                        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                        
                        apply_url = item.get("absolute_url", "")
                        job_hash = hashlib.md5(f"{company_name}_{job_title}_{apply_url}".encode()).hexdigest()
                        
                        jobs.append({
                            "title": job_title,
                            "company": company_name,
                            "location": job_loc or "Israel / Hybrid",
                            "url": apply_url,
                            "source": "Greenhouse",
                            "description": clean_content[:3000],
                            "posted_date": item.get("updated_at", "")[:10],
                            "job_hash": job_hash
                        })
            except Exception as e:
                # Silently continue to next company board
                continue
                
        return jobs
