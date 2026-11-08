import abc
from typing import List, Dict, Any

class BaseScraper(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def search(self, keywords: List[str], location: str = "Israel") -> List[Dict[str, Any]]:
        """
        Searches jobs based on keywords and location.
        Returns a list of dicts with keys:
        - title
        - company
        - location
        - url
        - source
        - description
        - posted_date
        - job_hash
        """
        pass
