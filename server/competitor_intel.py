"""
Competitor Intelligence Analyzer
Uses: SerpAPI (find competitors) + Google PageSpeed API (free perf scores) + Groq (AI analysis)
"""
import os
import re
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse


PAGESPEED_API = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
SERPAPI_URL   = 'https://serpapi.com/search'
ZENSERP_URL   = 'https://app.zenserp.com/api/v2/search'

REGION_MAP = {
    'Saudi Arabia':   {'gl': 'sa', 'hl': 'ar', 'location': 'Saudi Arabia', 'domain': 'google.com.sa'},
    'Egypt':          {'gl': 'eg', 'hl': 'ar', 'location': 'Egypt',        'domain': 'google.com.eg'},
    'UAE':            {'gl': 'ae', 'hl': 'ar', 'location': 'United Arab Emirates', 'domain': 'google.ae'},
    'Kuwait':         {'gl': 'kw', 'hl': 'ar', 'location': 'Kuwait',       'domain': 'google.com.kw'},
    'Jordan':         {'gl': 'jo', 'hl': 'ar', 'location': 'Jordan',       'domain': 'google.jo'},
    'Global':         {'gl': 'us', 'hl': 'en', 'location': 'United States','domain': 'google.com'},
}


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace('www.', '')
    except Exception:
        return url


def _serp_search(query: str, region: str, api_key: str = None) -> List[Dict]:
    """Search Google via SerpAPI or ZenSerp, return organic results."""
    r = REGION_MAP.get(region, REGION_MAP['Global'])
    key = api_key or os.getenv('SERPAPI_KEY', '')

    if key:
        try:
            resp = requests.get(SERPAPI_URL, params={
                'q': query, 'location': r['location'],
                'hl': r['hl'], 'gl': r['gl'],
                'google_domain': r['domain'], 'api_key': key,
                'num': 10
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get('organic_results', [])
        except Exception:
            pass

    # ZenSerp fallback
    zen_key = os.getenv('ZENSERP_KEY', '')
    if zen_key:
        try:
            resp = requests.get(ZENSERP_URL, params={
                'q': query, 'location': r['location'],
                'hl': r['hl'], 'gl': r['gl'], 'apikey': zen_key, 'num': 10
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get('organic', [])
        except Exception:
            pass

    return []


def get_pagespeed(url: str) -> Dict:
    """Get Google PageSpeed score — completely free, no key needed."""
    try:
        resp = requests.get(PAGESPEED_API, params={
            'url': url, 'strategy': 'mobile',
            'category': ['performance', 'seo', 'accessibility']
        }, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        cats = data.get('lighthouseResult', {}).get('categories', {})
        audits = data.get('lighthouseResult', {}).get('audits', {})
        return {
            'performance': round((cats.get('performance', {}).get('score', 0) or 0) * 100),
            'seo':         round((cats.get('seo', {}).get('score', 0) or 0) * 100),
            'accessibility': round((cats.get('accessibility', {}).get('score', 0) or 0) * 100),
            'fcp':  audits.get('first-contentful-paint', {}).get('displayValue', '—'),
            'lcp':  audits.get('largest-contentful-paint', {}).get('displayValue', '—'),
            'cls':  audits.get('cumulative-layout-shift', {}).get('displayValue', '—'),
            'tbt':  audits.get('total-blocking-time', {}).get('displayValue', '—'),
        }
    except Exception:
        return {'performance': None, 'seo': None, 'accessibility': None,
                'fcp': '—', 'lcp': '—', 'cls': '—', 'tbt': '—'}


def _ai_analyze_competitors(your_domain: str, competitors: List[Dict],
                              industry: str, region: str, api_keys: dict = None) -> Dict:
    """Use Groq/OpenAI to generate strategic competitor analysis."""
    api_keys = api_keys or {}
    groq_key = api_keys.get('groq') or os.getenv('GROQ_API_KEY', '')
    openai_key = api_keys.get('openai') or os.getenv('OPENAI_API_KEY', '')

    comp_summary = '\n'.join([
        f"- {c['domain']}: perf={c.get('pagespeed', {}).get('performance', '?')}%, "
        f"seo={c.get('pagespeed', {}).get('seo', '?')}%, "
        f"snippet: {c.get('snippet', '')[:100]}"
        for c in competitors[:6]
    ])

    prompt = f"""You are a competitive intelligence analyst for {region}.

Target site: {your_domain}
Industry: {industry or 'Digital Services'}
Region: {region}

Competitors found:
{comp_summary}

Analyze and return ONLY valid JSON:
{{
  "market_position": "Leader/Challenger/Niche/Newcomer",
  "key_differentiators": ["what makes each competitor stand out"],
  "your_opportunities": ["3-5 specific gaps you can exploit"],
  "threats": ["2-3 main competitive threats"],
  "recommended_keywords": ["5 keywords competitors rank for that you should target"],
  "quick_wins": ["3 immediate actions to outrank competitors"],
  "market_summary": "2-sentence market overview"
}}"""

    try:
        if groq_key:
            from groq import Groq
            client = Groq(api_key=groq_key)
            resp = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.2, max_tokens=1000
            )
            text = resp.choices[0].message.content
        elif openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.2, max_tokens=1000
            )
            text = resp.choices[0].message.content
        else:
            return _demo_analysis(your_domain, competitors, industry, region)

        import json, re
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass

    return _demo_analysis(your_domain, competitors, industry, region)


def _demo_analysis(your_domain: str, competitors: List[Dict], industry: str, region: str) -> Dict:
    return {
        'market_position': 'Challenger',
        'key_differentiators': [f"{c['domain']} يتميز بـ {c.get('snippet','')[:60]}" for c in competitors[:3]],
        'your_opportunities': [
            f'استهداف كلمات {industry or "الخدمة"} في {region} بمحتوى عربي متخصص',
            'بناء صفحات landing محلية لكل مدينة رئيسية',
            'إضافة Schema LocalBusiness لتحسين الظهور المحلي',
        ],
        'threats': [
            f'{competitors[0]["domain"] if competitors else "المنافس الأول"} يحتل المرتبة الأولى',
            'المنافسون يستخدمون محتوى أطول وأكثر تفصيلاً',
        ],
        'recommended_keywords': [f'{industry or "خدمة"} في {region}', f'أفضل {industry or "شركة"} {region}'],
        'quick_wins': [
            'أضف Groq API للحصول على تحليل ذكاء اصطناعي حقيقي',
            'أنشئ صفحة مقارنة مع المنافسين',
            'حسّن سرعة الموقع (PageSpeed < 2s)',
        ],
        'market_summary': f'[وضع تجريبي] أضف Groq API للحصول على تحليل حقيقي لسوق {industry or "الخدمات"} في {region}.'
    }


def analyze_competitors(your_url: str, region: str = 'Saudi Arabia',
                         industry: str = '', count: int = 7,
                         api_keys: dict = None) -> Dict:
    """
    Full competitor intelligence pipeline:
    1. Extract domain + build search queries
    2. Find competitors via SerpAPI (free 100/mo)
    3. Get PageSpeed scores (completely free)
    4. AI strategic analysis via Groq
    """
    api_keys = api_keys or {}
    your_domain = _extract_domain(your_url)
    r = REGION_MAP.get(region, REGION_MAP['Global'])

    # Build search queries to find competitors
    queries = []
    if industry:
        queries.append(f'{industry} agency {region}')
        queries.append(f'best {industry} company {r["location"]}')
    queries.append(f'site similar to {your_domain}')
    queries.append(f'{industry or "digital marketing"} {r["location"]}')

    # Collect unique competitor domains
    seen_domains = {your_domain}
    raw_competitors = []

    for query in queries[:3]:
        results = _serp_search(query, region, api_keys.get('serpapi') or api_keys.get('serp'))
        for res in results:
            link = res.get('link') or res.get('url', '')
            domain = _extract_domain(link)
            if domain and domain not in seen_domains and len(raw_competitors) < count:
                seen_domains.add(domain)
                raw_competitors.append({
                    'domain': domain,
                    'url': link,
                    'title': res.get('title', domain),
                    'snippet': res.get('snippet', ''),
                    'position': res.get('position', len(raw_competitors) + 1),
                })

    # If no SERP key, use AI to suggest competitors
    if not raw_competitors:
        raw_competitors = _suggest_competitors_ai(your_domain, industry, region, count, api_keys)

    # Get PageSpeed for each competitor (free, parallel-ish)
    competitors = []
    for comp in raw_competitors[:count]:
        ps = get_pagespeed(comp['url'] or f"https://{comp['domain']}")
        competitors.append({**comp, 'pagespeed': ps})

    # Get your own PageSpeed
    your_pagespeed = get_pagespeed(your_url)

    # AI strategic analysis
    ai_analysis = _ai_analyze_competitors(your_domain, competitors, industry, region, api_keys)

    return {
        'your_domain': your_domain,
        'your_url': your_url,
        'your_pagespeed': your_pagespeed,
        'region': region,
        'industry': industry,
        'competitors': competitors,
        'competitor_count': len(competitors),
        'ai_analysis': ai_analysis,
        'data_sources': {
            'serp': bool(os.getenv('SERPAPI_KEY') or api_keys.get('serpapi')),
            'pagespeed': True,
            'ai': bool(os.getenv('GROQ_API_KEY') or api_keys.get('groq') or
                       os.getenv('OPENAI_API_KEY') or api_keys.get('openai'))
        }
    }


def _suggest_competitors_ai(domain: str, industry: str, region: str,
                              count: int, api_keys: dict) -> List[Dict]:
    """When no SERP key, use AI to suggest likely competitors."""
    groq_key = api_keys.get('groq') or os.getenv('GROQ_API_KEY', '')
    openai_key = api_keys.get('openai') or os.getenv('OPENAI_API_KEY', '')

    prompt = (f"List {count} real competitor websites for a {industry or 'digital services'} "
              f"company in {region} similar to {domain}. "
              f"Return ONLY a JSON array of objects: "
              f'[{{"domain":"example.com","title":"Company Name","snippet":"brief description"}}]')
    try:
        text = ''
        if groq_key:
            from groq import Groq
            r = Groq(api_key=groq_key).chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3, max_tokens=600
            )
            text = r.choices[0].message.content
        elif openai_key:
            from openai import OpenAI
            r = OpenAI(api_key=openai_key).chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3, max_tokens=600
            )
            text = r.choices[0].message.content

        if text:
            import json, re
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if m:
                items = json.loads(m.group(0))
                return [{'domain': i.get('domain',''), 'url': f"https://{i.get('domain','')}",
                         'title': i.get('title',''), 'snippet': i.get('snippet',''),
                         'position': idx+1} for idx, i in enumerate(items[:count])]
    except Exception:
        pass
    return []
