import requests
import hashlib
import re
from typing import List, Dict, Any
from core.scrapers.base import BaseScraper

COMEET_COMPANIES = [
    {"name": "Lemonade", "token": "lemonade"},
    {"name": "BigPanda", "token": "bigpanda"},
    {"name": "WalkMe", "token": "walkme"},
    {"name": "Verbit", "token": "verbit"},
    {"name": "DriveNets", "token": "drivenets"},
    {"name": "OwnBackup", "token": "ownbackup"},
    {"name": "SimilarWeb", "token": "similarweb"},
]

class ComeetScraper(BaseScraper):
    name: str = "Comeet"

    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        
        keywords_lower = [k.lower() for k in keywords if len(k) > 1]

        for comp in COMEET_COMPANIES:
            company_name = comp["name"]
            company_token = comp["token"]
            
            # Comeet API endpoint
            url = f"https://www.comeet.com/jobs-api/2.0/company/{company_token}/positions?details=true"
            try:
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code != 200:
                    continue
                positions = resp.json()
                if not isinstance(positions, list):
                    continue
                    
                for pos in positions:
                    pos_loc = pos.get("location", {}).get("name", "") if isinstance(pos.get("location"), dict) else str(pos.get("location", ""))
                    loc_match = any(term in pos_loc.lower() for term in ["israel", "tel aviv", "herzliya", "remote", "haifa", "jerusalem"])
                    
                    job_title = pos.get("name", "")
                    job_desc = pos.get("details", "") or pos.get("description", "")
                    job_text = (job_title + " " + job_desc).lower()
                    
                    is_relevant = False
                    if not keywords_lower:
                        is_relevant = True
                    else:
                        for kw in keywords_lower:
                            if kw in job_text or kw in job_title.lower():
                                is_relevant = True
                                break
                                
                    if (loc_match or not pos_loc) and is_relevant:
                        clean_desc = re.sub(r'<[^>]+>', ' ', job_desc)
                        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                        
                        apply_url = pos.get("url_active_page", f"https://www.comeet.com/jobs/{company_token}/{pos.get('uid', '')}")
                        job_hash = hashlib.md5(f"{company_name}_{job_title}_{apply_url}".encode()).hexdigest()
                        
                        jobs.append({
                            "title": job_title,
                            "company": company_name,
                            "location": pos_loc or "Israel / Hybrid",
                            "url": apply_url,
                            "source": "Comeet",
                            "description": clean_desc[:3000],
                            "posted_date": pos.get("time_updated", "")[:10] or pos.get("time_created", "")[:10],
                            "job_hash": job_hash
                        })
            except Exception:
                continue
                
        return jobs
