import os
import requests
from typing import List, Dict

DATAFORSEO_LOGIN = os.getenv('DATAFORSEO_LOGIN', '')
DATAFORSEO_PASSWORD = os.getenv('DATAFORSEO_PASSWORD', '')
BASE_URL = 'https://api.dataforseo.com/v3'

def enrich_keywords(keywords: List[str], location_code: int = 2840) -> List[Dict]:
    """Enrich keywords with volume/CPC data from DataForSEO.
    
    Args:
        keywords: List of keyword strings
        location_code: DataForSEO location code (2840 = USA)
    
    Returns:
        List of dicts with kw, volume, cpc, competition
    """
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD or not keywords:
        return [{'kw': k, 'volume': None, 'cpc': None} for k in keywords]
    
    payload = [{
        "keywords": keywords[:100],  # free tier limit
        "location_code": location_code,
        "language_code": "en"
    }]
    
    try:
        resp = requests.post(
            f'{BASE_URL}/keywords_data/google_ads/search_volume/live',
            json=payload,
            auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        if data.get('tasks') and data['tasks'][0].get('result'):
            for item in data['tasks'][0]['result']:
                results.append({
                    'kw': item.get('keyword', ''),
                    'volume': item.get('search_volume'),
                    'cpc': item.get('cpc'),
                    'competition': item.get('competition')
                })
        return results
    except Exception:
        return [{'kw': k, 'volume': None, 'cpc': None} for k in keywords]
