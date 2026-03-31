import os
import requests
from typing import List, Dict

DATAFORSEO_LOGIN = os.getenv('DATAFORSEO_LOGIN', '')
DATAFORSEO_PASSWORD = os.getenv('DATAFORSEO_PASSWORD', '')
BASE_URL = 'https://api.dataforseo.com/v3'

def enrich_keywords(keywords: List[str], location_code: int = 2682, language_code: str = "ar") -> List[Dict]:
    """Enrich keywords with volume/CPC data from DataForSEO.
    
    DISABLED: DataForSEO quota exceeded. Returning empty results.
    Use SerpAPI/ZenSerp for search data instead.
    
    Args:
        keywords: List of keyword strings
        location_code: DataForSEO location code (2682 = Saudi Arabia, 2840 = USA)
        language_code: Language code (ar, en)
    
    Returns:
        List of dicts with kw, volume, cpc, competition
    """
    # Skip DataForSEO entirely - quota exceeded
    print("DataForSEO: SKIPPED (quota exceeded). Use SerpAPI/ZenSerp instead.")
    return [{'kw': k, 'volume': None, 'cpc': None} for k in keywords]
