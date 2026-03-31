"""
Competitor Intelligence — Decision Engine v2
Pipeline:
  1. Niche Detection (AI detects what the site actually sells/does)
  2. Smart Keyword Generation (niche-specific, not generic)
  3. Competitor Discovery (SerpAPI with AI filtering to remove irrelevant results)
  4. Data Enrichment (PageSpeed real data + content signals)
  5. Scoring Engine (weighted formula)
  6. Segmentation (Direct / Indirect / Aspirational)
  7. Grounded AI Insights (specific, not generic)
  8. GEO Intelligence (regional fit per competitor)
  9. Quick Wins (specific keyword opportunities)
"""
import os
import re
import json
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse

import time

PAGESPEED_API = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
SERPAPI_URL   = 'https://serpapi.com/search'
ZENSERP_URL   = 'https://app.zenserp.com/api/v2/search'

# Rate limiting for PageSpeed API
LAST_PAGESPEED_CALL = 0
PAGESPEED_DELAY = 2  # seconds between calls

# Minimal seed database - only for critical fallback
# System relies on AI + SerpAPI, NOT this static list
KNOWN_COMPETITORS_SEED = {
    'Saudi Arabia': {
        'digital marketing': [
            {'domain': 'socializeagency.com', 'name': 'Socialize Agency'},
            {'domain': 'webedia.me', 'name': 'Webedia Arabia'},
        ],
    },
}

# Dynamic competitor cache (in-memory, should be replaced with database in production)
# Format: {region: {niche: [competitors]}}
DYNAMIC_COMPETITOR_CACHE = {}

def _get_cached_competitors(region: str, niche: str) -> List[Dict]:
    """Get competitors from dynamic cache (database in production)."""
    niche_normalized = niche.lower().strip()
    
    if region in DYNAMIC_COMPETITOR_CACHE:
        for cached_niche, competitors in DYNAMIC_COMPETITOR_CACHE[region].items():
            if cached_niche.lower() in niche_normalized or niche_normalized in cached_niche.lower():
                print(f"  [Cache] Found {len(competitors)} cached competitors for '{cached_niche}' in {region}")
                return competitors
    
    if region in KNOWN_COMPETITORS_SEED:
        for key, competitors in KNOWN_COMPETITORS_SEED[region].items():
            if key.lower() in niche_normalized or niche_normalized in key.lower():
                print(f"  [Seed] Found {len(competitors)} seed competitors for '{key}' in {region}")
                return competitors
    
    return []

def _cache_competitors(region: str, niche: str, competitors: List[Dict]):
    """Cache discovered competitors for future use (database in production)."""
    if not competitors:
        return
    
    niche_normalized = niche.lower().strip()
    
    if region not in DYNAMIC_COMPETITOR_CACHE:
        DYNAMIC_COMPETITOR_CACHE[region] = {}
    
    cached = []
    for c in competitors:
        if c.get('verified') or c.get('ai_confidence') == 'high':
            cached.append({
                'domain': c['domain'],
                'name': c.get('title', c['domain']),
            })
    
    if cached:
        DYNAMIC_COMPETITOR_CACHE[region][niche_normalized] = cached
        print(f"  [Cache] Stored {len(cached)} competitors for '{niche_normalized}' in {region}")

def detect_brand_tier_ai(domain: str, snippet: str, niche: str, api_keys: dict) -> tuple:
    """Use AI to detect brand tier based on actual market presence - NO hardcoded lists."""
    if not (api_keys.get('groq') or os.getenv('GROQ_API_KEY','')):
        return 'niche', 5
    
    prompt = f"""Analyze this business and determine its market tier:
Domain: {domain}
Description: {snippet}
Industry: {niche}

Classify into ONE tier:
- global_giant: International brand known worldwide (e.g., Amazon, Nike, McDonald's)
- regional_leader: Dominant in specific region/country (e.g., Noon in Middle East, Flipkart in India)
- established: Well-known in their market with strong presence
- niche: Small/local business or new entrant

Return ONLY JSON: {{"tier": "global_giant|regional_leader|established|niche", "reason": "brief explanation"}}"""
    
    try:
        text = _llm(prompt, api_keys, max_tokens=150)
        result = _parse_json(text, {})
        tier = result.get('tier', 'niche')
        
        power_map = {
            'global_giant': 50,
            'regional_leader': 35,
            'established': 20,
            'niche': 5
        }
        return tier, power_map.get(tier, 5)
    except Exception:
        return 'niche', 5

REGION_MAP = {
    'Saudi Arabia': {'gl':'sa','hl':'ar','location':'Saudi Arabia',       'domain':'google.com.sa','lang':'Arabic'},
    'Egypt':        {'gl':'eg','hl':'ar','location':'Egypt',              'domain':'google.com.eg','lang':'Arabic'},
    'UAE':          {'gl':'ae','hl':'ar','location':'United Arab Emirates','domain':'google.ae',   'lang':'Arabic'},
    'Kuwait':       {'gl':'kw','hl':'ar','location':'Kuwait',             'domain':'google.com.kw','lang':'Arabic'},
    'Jordan':       {'gl':'jo','hl':'ar','location':'Jordan',             'domain':'google.jo',    'lang':'Arabic'},
    'Morocco':      {'gl':'ma','hl':'ar','location':'Morocco',            'domain':'google.co.ma', 'lang':'Arabic'},
    'Global':       {'gl':'us','hl':'en','location':'United States',      'domain':'google.com',   'lang':'English'},
}

# Domains to always exclude (social, major generic hubs)
EXCLUDE_DOMAINS = {
    'facebook.com','instagram.com','twitter.com','linkedin.com','youtube.com',
    'wikipedia.org','amazon.com','google.com','yelp.com','tripadvisor.com',
    'yellowpages.com','pinterest.com','snapchat.com','tiktok.com'
}

def _is_excluded(domain: str) -> bool:
    if not domain: return False
    domain = domain.lower()
    if domain in EXCLUDE_DOMAINS: return True
    # Handle subdomains (e.g. sa.linkedin.com)
    for ext in EXCLUDE_DOMAINS:
        if domain.endswith('.' + ext): return True
    return False


def _extract_domain(url: str) -> str:
    try:
        d = urlparse(url if '://' in url else 'https://'+url).netloc
        return d.replace('www.','').strip('/')
    except Exception:
        return url


def _llm(prompt: str, api_keys: dict, max_tokens: int = 1200) -> str:
    """Call Groq or OpenAI."""
    groq_key   = api_keys.get('groq')   or os.getenv('GROQ_API_KEY','')
    openai_key = api_keys.get('openai') or os.getenv('OPENAI_API_KEY','')
    if groq_key:
        from groq import Groq
        r = Groq(api_key=groq_key).chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role':'user','content':prompt}],
            temperature=0.15, max_tokens=max_tokens
        )
        return r.choices[0].message.content
    if openai_key:
        from openai import OpenAI
        r = OpenAI(api_key=openai_key).chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role':'user','content':prompt}],
            temperature=0.15, max_tokens=max_tokens
        )
        return r.choices[0].message.content
    return ''


def _parse_json(text: str, fallback):
    """Extract first JSON object or array from LLM text."""
    for pattern in [r'\{.*\}', r'\[.*\]']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return fallback


# ── Step 1: Niche Detection ───────────────────────────────────────────────────

def detect_niche(domain: str, url: str, industry_hint: str, api_keys: dict) -> Dict:
    """
    Detect niche using multi-layer approach:
    1. User hint (highest priority)
    2. AI analysis with rich context from HOMEPAGE (not URL path)
    3. Domain heuristics (fallback)
    """
    domain_lower = domain.lower()

    # Quick heuristic signals
    signals = {
        'ecommerce': ['shop','store','buy','cart','abaya','fashion','clothes','wear','متجر','ملابس','عبايات'],
        'agency':    ['agency','digital','marketing','seo','media','creative','وكالة','تسويق','rabhan','ads','branding'],
        'saas':      ['app','platform','software','tool','dashboard','system','نظام','منصة'],
        'restaurant':['food','restaurant','cafe','مطعم','طعام','كافيه'],
        'real_estate':['property','realty','estate','عقار','شقق','مساكن'],
        'education': ['academy','school','course','learn','تعليم','أكاديمية','دورات'],
        'health':    ['clinic','health','medical','doctor','صحة','عيادة','طبي'],
        'government':['gov','ministry','authority','invest','setup','misa','sagia','حكومة','وزارة'],
        'b2b_services':['consulting','advisory','business setup','company formation','استشارات','خدمات'],
    }

    detected_type = 'business'
    for t, words in signals.items():
        if any(w in domain_lower for w in words):
            detected_type = t
            break

    # If user provided industry hint, use it (highest priority)
    if industry_hint:
        niche = industry_hint
        category = detected_type
        
        # Generate search queries using AI if available
        if api_keys.get('groq') or api_keys.get('openai'):
            text = _llm(
                f"Generate 7 Google search queries to find HIGH-INTENT commercial competitors of a '{industry_hint}' business in Saudi Arabia.\n"
                f"Requirements:\n"
                f"- Focus on keywords that businesses and customers use (e.g. 'company', 'agency', 'services', 'pricing', 'contact')\n"
                f"- Exclude generic information searches, blogs, or directories\n"
                f"- Mix Arabic and English\n"
                f"Return ONLY JSON array: [\"query1\", \"query2\", ...]\n\n"
                f"Example for 'digital marketing agency':\n"
                f"[\"digital marketing services Saudi Arabia\", \"وكالة تسويق رقمي الرياض\", \"best SEO agencies Jeddah\", \"performance marketing company pricing KSA\"]",
                api_keys, max_tokens=300
            )
            kws = _parse_json(text, [f'{industry_hint} Saudi Arabia', f'best {industry_hint} companies KSA'])
        else:
            kws = [f'{industry_hint} Saudi Arabia', f'best {industry_hint}', f'{industry_hint} companies KSA']
        
        return {'niche': niche, 'category': category, 'search_queries': kws, 'detected': False, 'type': category}

    # CRITICAL: Always analyze HOMEPAGE, not URL path
    # If URL has a path, strip it to get homepage
    homepage_url = f"https://{domain}"
    
    # AI detection with RICH context from HOMEPAGE
    if api_keys.get('groq') or api_keys.get('openai'):
        # Scrape homepage to understand actual business
        try:
            resp = requests.get(homepage_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            html = resp.text[:10000]
            body_text = re.sub(r'<[^>]+>', ' ', html).lower()
            meta_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
            site_desc = meta_desc.group(1) if meta_desc else ''
            title = re.search(r'<title>(.*?)</title>', html, re.I)
            site_title = title.group(1) if title else ''
            
            # Check for business model indicators
            is_ecommerce = any(x in body_text for x in ['add to cart', 'buy now', 'shop now', 'أضف للسلة', 'اشتري الآن'])
            is_government = any(x in body_text for x in ['ministry', 'government', 'authority', 'invest', 'وزارة', 'حكومة'])
            is_b2b_service = any(x in body_text for x in ['consulting', 'advisory', 'business setup', 'company formation', 'استشارات'])
            
        except Exception:
            body_text = ''
            site_desc = ''
            site_title = ''
            is_ecommerce = False
            is_government = False
            is_b2b_service = False
        
        text = _llm(
            f"Analyze this website's HOMEPAGE to detect its EXACT business model:\n"
            f"Domain: {domain}\n"
            f"Homepage URL: {homepage_url}\n"
            f"Title: {site_title}\n"
            f"Description: {site_desc}\n\n"
            f"CRITICAL: Analyze what the HOMEPAGE does, NOT what URL paths mention.\n\n"
            f"Instructions:\n"
            f"1. Determine what services/products they SELL (not what they write about)\n"
            f"2. Identify their PRIMARY business model\n"
            f"3. Distinguish between:\n"
            f"   - E-commerce store (sells products online with cart/checkout)\n"
            f"   - Government/Authority website (provides info/services for businesses)\n"
            f"   - B2B Services (consulting, business setup, advisory)\n"
            f"   - Marketing Agency (offers marketing services)\n"
            f"4. Generate 6 Google queries to find DIRECT competitors (same business model)\n\n"
            f"Examples:\n"
            f"- setupinsaudi.com → Government/B2B service (NOT e-commerce store)\n"
            f"- namshi.com → E-commerce fashion store\n"
            f"- rabhanagency.com → Marketing agency\n\n"
            f"Return ONLY JSON:\n"
            f"{{\n"
            f"  \"niche\": \"specific description (e.g. 'business setup consultancy', 'fashion e-commerce')\",\n"
            f"  \"category\": \"ecommerce|agency|saas|government|b2b_services|other\",\n"
            f"  \"search_queries\": [\"query1\", \"query2\", ...]\n"
            f"}}",
            api_keys, max_tokens=500
        )
        result = _parse_json(text, {})
        if result and result.get('niche'):
            return {**result, 'detected': True, 'type': result.get('category', detected_type)}

    # Fallback: domain-based
    base_name = domain.split('.')[0]
    return {
        'niche': f'{detected_type} - {base_name}',
        'category': detected_type,
        'search_queries': [
            f'{base_name} competitors Saudi Arabia',
            f'best {detected_type} Saudi Arabia',
            f'{detected_type} companies Saudi',
        ],
        'detected': False,
        'type': detected_type
    }


# ── Step 2: Competitor Discovery ──────────────────────────────────────────────

def _serp_search(query: str, region: str, api_key: str = None) -> List[Dict]:
    r = REGION_MAP.get(region, REGION_MAP['Global'])
    key = api_key or os.getenv('SERPAPI_KEY','')
    if key:
        try:
            resp = requests.get(SERPAPI_URL, params={
                'q': query, 'location': r['location'],
                'hl': r['hl'], 'gl': r['gl'],
                'google_domain': r['domain'], 'api_key': key, 'num': 10
            }, timeout=15)
            resp.raise_for_status()
            return resp.json().get('organic_results', [])
        except Exception:
            pass
    zen_key = os.getenv('ZENSERP_KEY','')
    if zen_key:
        try:
            resp = requests.get(ZENSERP_URL, params={
                'q': query, 'location': r['location'],
                'hl': r['hl'], 'gl': r['gl'], 'apikey': zen_key, 'num': 10
            }, timeout=15)
            resp.raise_for_status()
            return resp.json().get('organic', [])
        except Exception:
            pass
    return []


def discover_competitors(niche_data: Dict, your_domain: str, region: str,
                          count: int, api_keys: dict) -> List[Dict]:
    """
    Find real competitors using niche-specific queries.
    Then AI-filter to remove irrelevant results (agencies, directories, etc.)
    """
    serp_key = api_keys.get('serpapi') or api_keys.get('serp') or os.getenv('SERPAPI_KEY','')
    seen = {your_domain} | EXCLUDE_DOMAINS
    raw = []

    # ALWAYS start with AI-suggested "Hard" competitors to ensure quality
    ai_key_exists = bool(api_keys.get('groq') or api_keys.get('openai') or os.getenv('GROQ_API_KEY') or os.getenv('OPENAI_API_KEY'))
    if ai_key_exists:
        print(f"  [Discovery] Fetching AI-suggested hard competitors...")
        ai_comps = _ai_suggest_competitors(your_domain, niche_data, region, count, api_keys)
        for c in ai_comps:
            if c['domain'] not in seen and not _is_excluded(c['domain']):
                seen.add(c['domain'])
                raw.append({
                    'domain': c['domain'],
                    'url': f"https://{c['domain']}",
                    'title': c.get('title', c['domain']),
                    'snippet': c.get('relevance_reason', c.get('snippet', '')),
                    'serp_position': 0, # Top priority
                    'discovery_source': 'ai_knowledge'
                })

    # Then supplement with SERP results
    queries = niche_data.get('search_queries', [])
    if not queries:
        queries = [f'{niche_data.get("niche","business")} {region}']

    for query in queries[:4]:
        results = _serp_search(query, region, serp_key)
        for res in results:
            link = res.get('link') or res.get('url','')
            domain = _extract_domain(link)
            if domain and domain != your_domain and not _is_excluded(domain) and len(raw) < count * 3:
                seen.add(domain)
                raw.append({
                    'domain': domain,
                    'url': link or f'https://{domain}',
                    'title': res.get('title', domain),
                    'snippet': res.get('snippet',''),
                    'serp_position': res.get('position', len(raw)+1),
                    'discovery_source': 'serp'
                })

    # No need to call AI again here as we already did it at the start

    # AI filter: remove irrelevant (agencies when looking for ecommerce, etc.)
    if raw and (api_keys.get('groq') or os.getenv('GROQ_API_KEY','')):
        raw = _ai_filter_competitors(raw, niche_data, region, api_keys)

    return raw[:count]


def _ai_filter_competitors(candidates: List[Dict], niche_data: Dict,
                             region: str, api_keys: dict) -> List[Dict]:
    """Light filtering - only remove obviously wrong competitors."""
    niche = niche_data.get('niche','')
    category = niche_data.get('category','')
    
    # Quick verification: scrape homepage to check business type
    verified_candidates = []
    for c in candidates:
        domain = c['domain']
        try:
            url = c.get('url') or f"https://{domain}"
            resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
            html = resp.text[:6000]
            
            body_text = re.sub(r'<[^>]+>', ' ', html).lower()
            meta_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
            desc = meta_desc.group(1)[:200] if meta_desc else ''
            title = re.search(r'<title>(.*?)</title>', html, re.I)
            page_title = title.group(1)[:150] if title else ''
            
            c['actual_title'] = page_title
            c['actual_desc'] = desc
            c['content_sample'] = body_text[:500]
            verified_candidates.append(c)
            
        except Exception as e:
            print(f"  [Filter] Could not scrape {domain}, keeping anyway: {e}")
            # Keep it anyway - don't be too strict
            c['actual_title'] = c.get('title', '')
            c['actual_desc'] = c.get('snippet', '')
            verified_candidates.append(c)
    
    if not verified_candidates:
        return candidates
    
    # AI filtering:
    # REJECT AS 'REAL' IF:
    # 1. Different industry OR different business model (e.g. they are a blog, you are an agency).
    # 2. Government, University, or non-profit (.gov, .edu, .org hubs).
    # 3. Global platforms (LinkedIn, TikTok, eBay, Amazon).
    # 4. Directory/listing pages where NO single business is the focus.
    #
    # MARK AS 'REAL' ONLY IF:
    # - They sell the same core service/product as the target for profit.
    # - They are a 'hard' competitor (direct rival in the market).
    #
    # Return JSON array:
    # [{
    #   "domain": "example.com",
    #   "relevant": true/false,
    #   "type": "Real|Content|Platform",
    #   "reason": "brief explanation"
    # }]

    text = _llm(
        f"""Analyze these competitor websites for a '{niche}' business in {region}.

REJECT AS 'REAL' IF:
1. Different industry OR different business model (e.g. they are a blog, you are an agency).
2. Government, University, or non-profit (.gov, .edu, .org hubs).
3. Global platforms (LinkedIn, TikTok, eBay, Amazon).
4. Directory/listing pages where NO single business is the focus.

MARK AS 'REAL' ONLY IF:
- They sell the same core service/product as the target for profit.
- They are a 'hard' competitor (direct rival in the market).

Return JSON array:
[{{
  "domain": "example.com",
  "relevant": true/false,
  "type": "Real|Content|Platform",
  "reason": "brief explanation"
}}]

Be LENIENT. Default to keeping competitors unless obviously wrong.""",
        api_keys, max_tokens=1200
    )
    
    filtered = _parse_json(text, [])
    if not filtered or not isinstance(filtered, list):
        print(f"  [Filter] AI filtering failed, keeping all {len(verified_candidates)} competitors")
        return verified_candidates

    filter_map = {f['domain']: f for f in filtered if isinstance(f, dict)}
    result = []
    for c in verified_candidates:
        info = filter_map.get(c['domain'], {'relevant': True, 'type': 'Real'})
        is_relevant = info.get('relevant', True)
        
        if is_relevant:
            # Enhanced classification using domain heuristics if AI unsure
            c_type = info.get('type', 'Real')
            snippet_low = (c.get('snippet','') + " " + c.get('domain','')).lower()
            
            # Direct filters for non-Real types
            if any(x in domain.lower() for x in ['.gov', '.edu', 'wikipedia.org', 'arabnews.com', 'similarweb.com']):
                c_type = 'Platform' if 'gov' in domain.lower() else 'Content'
            
            # Marketplace detection (generic giants)
            if any(x in domain.lower() for x in ['noon.com', 'amazon.', 'ebay.', '6thstreet.com', 'sivvi.com', 'centrepoint']):
                c_type = 'Platform'
            
            if c_type == 'Real' and any(x in snippet_low for x in ['directory', 'list of', 'top 10', 'sortlist', 'clutch', 'guide to', 'coupon', 'deals']):
                c_type = 'Platform'
            
            if c_type == 'Real' and any(x in snippet_low for x in ['blog', 'read more', 'how to', 'what is', 'news', ' Ramadan']):
                c_type = 'Content'

            result.append({
                **c,
                'competitor_type': c_type,
                'relevance_reason': info.get('reason', ''),
            })
            print(f"  [Filter] ✓ {c['domain']} - {c_type}: {info.get('reason', 'Relevant')}")
        else:
            print(f"  [Filter] ✗ {c['domain']} - REJECTED: {info.get('reason', 'Not relevant')}")
    
    # If we rejected too many, return originals
    if len(result) < len(verified_candidates) * 0.3:  # If we rejected >70%
        print(f"  [Filter] Too many rejections ({len(result)}/{len(verified_candidates)}), keeping all")
        return verified_candidates
    
    return result if result else verified_candidates


def _ai_suggest_competitors(domain: str, niche_data: Dict, region: str,
                              count: int, api_keys: dict) -> List[Dict]:
    """AI suggests REAL competitors with seed database fallback."""
    niche = niche_data.get('niche', domain)
    category = niche_data.get('category', 'business')
    
    # First, get actual website content to understand the business
    try:
        url = f"https://{domain}"
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        html = resp.text[:8000]
        meta_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
        site_desc = meta_desc.group(1) if meta_desc else ''
        title = re.search(r'<title>(.*?)</title>', html, re.I)
        site_title = title.group(1) if title else ''
        body_text = re.sub(r'<[^>]+>', ' ', html).lower()
        services = []
        if 'seo' in body_text: services.append('SEO')
        if 'social media' in body_text or 'سوشيال ميديا' in body_text: services.append('Social Media')
        if 'content' in body_text or 'محتوى' in body_text: services.append('Content Marketing')
        if 'ppc' in body_text or 'ads' in body_text or 'إعلانات' in body_text: services.append('Paid Ads')
        if 'branding' in body_text or 'علامة تجارية' in body_text: services.append('Branding')
        if 'web' in body_text or 'website' in body_text or 'موقع' in body_text: services.append('Web Development')
    except Exception:
        site_desc = ''
        site_title = ''
        services = []
    
    # Check if we have cached competitors for this region/niche
    seed_competitors = _get_cached_competitors(region, niche)
    
    # Request MORE competitors than needed (AI will suggest extras)
    request_count = count + 5
    
    # Build prompt with seed examples if available
    seed_examples = ''
    if seed_competitors:
        seed_examples = f"\n\nKNOWN COMPETITORS in {region} for this industry:\n"
        for s in seed_competitors[:5]:
            seed_examples += f"- {s['domain']} ({s['name']})\n"
        seed_examples += "\nInclude these if relevant, and find similar ones.\n"
    
    text = _llm(
        f"""List {request_count} real competitor companies for this business in {region}:

TARGET BUSINESS:
Domain: {domain}
Title: {site_title}
Description: {site_desc}
Services: {', '.join(services) if services else 'digital marketing'}
Industry: {niche}
Region: {region}{seed_examples}

INSTRUCTIONS:
1. Focus on {region} market (local and regional competitors)
2. Include competitors of different sizes:
   - 2-3 big established brands (aspirational)
   - 3-4 direct competitors (same size/services)
   - 2-3 smaller/niche players
3. Competitors must be in the SAME industry:
   - If target is 'digital marketing agency' → return marketing/advertising agencies (NOT content creators like Telfaz11/Uturn)
   - If target is 'ecommerce' → return online stores
   - If target is 'SaaS' → return software platforms
4. Mix of .sa, .ae, .com, .eg domains (based on region)
5. EXCLUDE content creators/media companies (Telfaz11, Uturn) unless target IS a media company

Return JSON array (suggest {request_count} competitors):
[{{
  "domain": "competitor.com",
  "title": "Company Name",
  "niche": "specific niche description",
  "competitor_type": "Real|Content|Platform",
  "relevance_reason": "why they compete with target"
}}]

Include competitors even if moderately confident.""",
        api_keys, max_tokens=2000
    )
    
    items = _parse_json(text, [])
    if not isinstance(items, list):
        items = []
    
    print(f"  [AI] Suggested {len(items)} competitors")
    
    # If AI returned nothing or very few, use seed database
    if len(items) < count // 2 and seed_competitors:
        print(f"  [AI] AI returned too few ({len(items)}), using seed database")
        for s in seed_competitors:
            if s['domain'] != domain:  # Don't include self
                items.append({
                    'domain': s['domain'],
                    'title': s['name'],
                    'snippet': f"Known competitor in {region}",
                    'competitor_type': 'Direct',
                    'confidence': 'high'
                })
    
    # Light verification - only check if domain resolves (don't reject too many)
    result = []
    for idx, i in enumerate(items):
        if not isinstance(i, dict) or not i.get('domain'):
            continue
        
        comp_domain = i.get('domain', '').strip()
        if not comp_domain or comp_domain == domain:
            continue
        
        # Skip obvious bad domains
        if comp_domain in ['example.com', 'competitor.com', 'agency.com']:
            continue
        
        # Skip content creators for marketing agencies
        if 'marketing' in niche.lower() or 'agency' in niche.lower():
            if any(x in comp_domain.lower() for x in ['telfaz11', 'uturn', 'youtube', 'tiktok']):
                print(f"  [AI] ✗ {comp_domain} - content creator, not agency")
                continue
        
        # Skip e-commerce stores for government/B2B services
        if 'government' in niche.lower() or 'b2b' in niche.lower() or 'business setup' in niche.lower():
            if any(x in comp_domain.lower() for x in ['noon', 'namshi', 'souq', 'amazon', 'jarir', 'extra', 'lulu', 'danube']):
                print(f"  [AI] ✗ {comp_domain} - e-commerce store, not B2B service")
                continue
        
        # Try light verification (HEAD request with short timeout)
        verified = False
        try:
            comp_url = f"https://{comp_domain}"
            verify_resp = requests.head(comp_url, timeout=3, allow_redirects=True)
            verified = verify_resp.status_code < 500
        except Exception:
            # If HEAD fails, try GET with very short timeout
            try:
                verify_resp = requests.get(f"https://{comp_domain}", timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
                verified = verify_resp.status_code < 500
            except Exception:
                # If both fail, still include if confidence is high or from seed
                verified = i.get('confidence') == 'high'
        
        if verified or i.get('confidence') == 'high':
            result.append({
                'domain': comp_domain,
                'url': f"https://{comp_domain}",
                'title': i.get('title',''),
                'snippet': i.get('snippet',''),
                'competitor_type': i.get('competitor_type','Direct'),
                'serp_position': idx+1,
                'ai_confidence': i.get('confidence', 'medium'),
                'verified': verified
            })
            print(f"  [AI] ✓ {comp_domain} - {i.get('competitor_type', 'Direct')} ({i.get('confidence', 'medium')} confidence)")
        else:
            print(f"  [AI] ✗ {comp_domain} - verification failed")
        
        if len(result) >= count:
            break
    
    print(f"  [AI] Returning {len(result)} verified competitors")
    
    # Cache successful results for future use
    if len(result) >= count // 2:
        _cache_competitors(region, niche, result)
    
    return result


# ── Step 3: Data Enrichment ───────────────────────────────────────────────────

def get_pagespeed(url: str) -> Dict:
    """Google PageSpeed — with rate limiting and smart fallback."""
    global LAST_PAGESPEED_CALL
    
    try:
        # Rate limiting: wait between calls
        now = time.time()
        elapsed = now - LAST_PAGESPEED_CALL
        if elapsed < PAGESPEED_DELAY:
            time.sleep(PAGESPEED_DELAY - elapsed)
        
        # Ensure URL has protocol
        if not url.startswith('http'):
            url = f'https://{url}'
        
        LAST_PAGESPEED_CALL = time.time()
        
        resp = requests.get(PAGESPEED_API, params={
            'url': url, 'strategy': 'mobile',
            'category': ['performance','seo']
        }, timeout=20)
        
        if resp.status_code == 429:
            print(f"[PageSpeed] Rate limited for {url} - using fallback")
            return _fallback_pagespeed(url)
            
        if resp.status_code != 200:
            print(f"[PageSpeed] Failed for {url}: {resp.status_code}")
            return _fallback_pagespeed(url)
            
        data = resp.json()
        cats   = data.get('lighthouseResult',{}).get('categories',{})
        audits = data.get('lighthouseResult',{}).get('audits',{})
        
        result = {
            'performance':   round((cats.get('performance',{}).get('score') or 0)*100),
            'seo':           round((cats.get('seo',{}).get('score') or 0)*100),
            'accessibility': round((cats.get('accessibility',{}).get('score') or 0.7)*100),
            'best_practices':round((cats.get('best-practices',{}).get('score') or 0.8)*100),
            'fcp': audits.get('first-contentful-paint',{}).get('displayValue','—'),
            'lcp': audits.get('largest-contentful-paint',{}).get('displayValue','—'),
            'cls': audits.get('cumulative-layout-shift',{}).get('displayValue','—'),
            'tbt': audits.get('total-blocking-time',{}).get('displayValue','—'),
            'has_https': url.startswith('https://'),
            'source': 'pagespeed'
        }
        print(f"[PageSpeed] ✓ {url}: SEO={result['seo']} Perf={result['performance']}")
        return result
        
    except Exception as e:
        print(f"[PageSpeed] Error for {url}: {e}")
        return _fallback_pagespeed(url)

def _fallback_pagespeed(url: str) -> Dict:
    """Estimate scores based on basic checks when PageSpeed fails."""
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        has_https = url.startswith('https://')
        is_reachable = resp.status_code == 200
        
        # Estimate scores
        base_seo = 70 if has_https else 50
        base_perf = 65 if is_reachable else 40
        
        return {
            'performance': base_perf,
            'seo': base_seo,
            'accessibility': 70,
            'best_practices': 75 if has_https else 60,
            'fcp': '~2.5s',
            'lcp': '~3.0s',
            'cls': '~0.1',
            'tbt': '~200ms',
            'has_https': has_https,
            'source': 'estimated'
        }
    except Exception:
        return {
            'performance': 50,
            'seo': 50,
            'accessibility': 60,
            'best_practices': 60,
            'fcp': '—',
            'lcp': '—',
            'cls': '—',
            'tbt': '—',
            'has_https': url.startswith('https://'),
            'source': 'fallback'
        }


def get_content_signals(url: str) -> Dict:
    """Scrape basic content signals from homepage — free."""
    try:
        # Ensure URL has protocol
        if not url.startswith('http'):
            url = f'https://{url}'
            
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; GEOBot/1.0)'
        })
        
        if resp.status_code != 200:
            print(f"[Content] Failed for {url}: {resp.status_code}")
            return _empty_content()
            
        html = resp.text
        # Count signals
        has_schema    = 'application/ld+json' in html
        has_arabic    = bool(re.search(r'[\u0600-\u06FF]', html))
        word_count    = len(re.sub(r'<[^>]+>','',html).split())
        has_blog      = any(x in html.lower() for x in ['/blog','/articles','/news','/مقالات'])
        has_faq       = any(x in html.lower() for x in ['faq','frequently','الأسئلة','أسئلة'])
        has_reviews   = any(x in html.lower() for x in ['review','rating','تقييم','مراجعة'])
        img_count     = html.lower().count('<img')
        has_video     = 'youtube.com' in html or 'vimeo.com' in html or '<video' in html
        meta_desc     = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
        return {
            'has_schema': has_schema,
            'has_arabic': has_arabic,
            'word_count': min(word_count, 50000),
            'has_blog': has_blog,
            'has_faq': has_faq,
            'has_reviews': has_reviews,
            'image_count': img_count,
            'has_video': has_video,
            'has_meta_desc': bool(meta_desc),
            'meta_desc': meta_desc.group(1)[:150] if meta_desc else '',
        }
    except Exception as e:
        print(f"[Content] Error for {url}: {e}")
        return _empty_content()

def _empty_content():
    return {'has_schema':False,'has_arabic':False,'word_count':0,'has_blog':False,
            'has_faq':False,'has_reviews':False,'image_count':0,'has_video':False,
            'has_meta_desc':False,'meta_desc':''}


# ── Step 4: Scoring Engine ────────────────────────────────────────────────────

def calculate_competitor_score(ps: Dict, content: Dict, serp_pos: int, niche: str, api_keys: dict, is_your_site: bool = False) -> Dict:
    """Universal scoring using AI for brand detection - NO hardcoded lists."""
    def safe(v, default=60): 
        return v if (v is not None and isinstance(v, (int, float))) else default

    seo_score  = safe(ps.get('seo'), 60)
    perf_score = safe(ps.get('performance'), 60)
    
    content_score = 0
    wc = content.get('word_count', 0)
    if wc > 500:  content_score += 25
    if wc > 2000: content_score += 15
    if content.get('has_schema'):    content_score += 20
    if content.get('has_blog'):      content_score += 15
    if content.get('has_faq'):       content_score += 10
    if content.get('has_reviews'):   content_score += 10
    if content.get('has_meta_desc'): content_score += 5
    content_score = min(100, content_score)
    
    website_quality = round((seo_score * 0.4 + perf_score * 0.3 + content_score * 0.3))

    market_power = 30
    domain = content.get('domain', '')
    snippet = content.get('meta_desc', '')
    brand_tier, power_bonus = detect_brand_tier_ai(domain, snippet, niche, api_keys)
    market_power += power_bonus
    
    if serp_pos <= 3:   market_power += 15
    elif serp_pos <= 5: market_power += 10
    elif serp_pos <= 10: market_power += 5
    
    if content.get('has_reviews'): market_power += 5
    if ps.get('has_https'):        market_power += 3
    
    # Adjust market power based on type
    c_type = content.get('competitor_type', 'Real')
    if c_type == 'Platform':
        market_power = min(100, market_power + 20)  # Platforms usually have higher generic power
    elif c_type == 'Content':
        market_power = min(100, market_power + 5)   # Content sites have SEO power, not business power
    
    market_power = min(100, market_power)

    if brand_tier == 'global_giant':
        combined = round(website_quality * 0.25 + market_power * 0.75)
    elif brand_tier == 'regional_leader':
        combined = round(website_quality * 0.3 + market_power * 0.7)
    elif brand_tier == 'established':
        combined = round(website_quality * 0.4 + market_power * 0.6)
    else:
        combined = round(website_quality * 0.6 + market_power * 0.4)

    geo_fit = 50
    if content.get('has_arabic'): geo_fit += 30
    if content.get('has_schema'): geo_fit += 20
    
    # Content vs Real weighting
    if c_type == 'Content':
        # Content sites care more about SEO and Word Count
        combined = round(website_quality * 0.7 + market_power * 0.3)
    elif c_type == 'Platform':
        # Platforms care more about Authority (Market Power)
        combined = round(website_quality * 0.3 + market_power * 0.7)
    
    geo_fit = min(100, geo_fit)

    return {
        'total': combined,
        'website_quality': website_quality,
        'market_power': market_power,
        'brand_tier': brand_tier,
        'breakdown': {'seo': seo_score, 'performance': perf_score, 'content': content_score, 'geo_fit': geo_fit},
        'grade': 'A' if combined>=85 else 'B' if combined>=70 else 'C' if combined>=55 else 'D',
        'data_quality': ps.get('source', 'unknown')
    }



# ── Step 5: Grounded AI Insights ─────────────────────────────────────────────

def generate_insights(your_domain: str, your_score: Dict, your_content: Dict,
                       competitors: List[Dict], niche: str, region: str,
                       api_keys: dict) -> Dict:
    """Generate specific, grounded insights — not generic templates."""
    if not (api_keys.get('groq') or os.getenv('GROQ_API_KEY','') or
            api_keys.get('openai') or os.getenv('OPENAI_API_KEY','')):
        return _demo_insights(your_domain, competitors, niche, region)

    # Build rich data context
    comp_data = []
    for c in competitors[:6]:
        comp_data.append({
            'domain': c['domain'],
            'score': c.get('score',{}).get('total','?'),
            'website_quality': c.get('score',{}).get('website_quality','?'),
            'market_power': c.get('score',{}).get('market_power','?'),
            'brand_tier': c.get('score',{}).get('brand_tier','unknown'),
            'type': c.get('competitor_type','Direct'),
            'seo': c.get('pagespeed',{}).get('seo','?'),
            'perf': c.get('pagespeed',{}).get('performance','?'),
            'has_arabic': c.get('content',{}).get('has_arabic',False),
            'has_blog': c.get('content',{}).get('has_blog',False),
            'has_schema': c.get('content',{}).get('has_schema',False),
            'word_count': c.get('content',{}).get('word_count',0),
            'snippet': c.get('snippet','')[:100],
        })

    your_data = {
        'domain': your_domain,
        'score': your_score.get('total','?'),
        'website_quality': your_score.get('website_quality','?'),
        'market_power': your_score.get('market_power','?'),
        'brand_tier': your_score.get('brand_tier','niche'),
        'seo': your_score.get('breakdown',{}).get('seo','?'),
        'perf': your_score.get('breakdown',{}).get('performance','?'),
        'has_arabic': your_content.get('has_arabic',False),
        'has_blog': your_content.get('has_blog',False),
        'has_schema': your_content.get('has_schema',False),
        'word_count': your_content.get('word_count',0),
    }

    prompt = f"""You are a competitive intelligence analyst for {region}.
Niche: {niche}

YOUR SITE DATA:
{json.dumps(your_data, ensure_ascii=False)}

COMPETITOR DATA:
{json.dumps(comp_data, ensure_ascii=False)}

IMPORTANT CONTEXT:
- Your site brand tier: {your_data.get('brand_tier', 'niche')}
- Competitor types found: {[c.get('type') for c in comp_data]}

Generate REALISTIC, DATA-DRIVEN insights.
CRITICAL: Acknowledge that you are losing traffic not just to other businesses (Real), but also to educational articles (Content) and directories (Platform) that dominate Google.

RULES:
1. If competitors include 'global_giant' or 'regional_leader' brands, acknowledge their dominance
2. Focus on YOUR competitive advantages (website quality, niche focus, local optimization)
3. NO generic advice - every insight must reference actual data
4. Be honest about market position
5. Mention if Content sites or Platforms are currently outperforming you in SEO rankings.

Return ONLY valid JSON:
{{
  "market_position": "Niche Player|Emerging Challenger|Established Player|Regional Leader|Market Leader",
  "market_summary": "2 realistic sentences acknowledging actual market dynamics and competitor strength",
  "your_strengths": ["specific strength: e.g. 'Website quality score 85 vs competitor average 65'"],
  "your_weaknesses": ["realistic weakness: e.g. 'Competing against Namshi (regional leader) with 10x traffic'"],
  "direct_threats": [
    {{"competitor": "domain", "threat": "specific: e.g. 'Brand recognition + SEO 92'", "their_advantage": "data: e.g. 'Established brand + 2M monthly visits'"}}
  ],
  "opportunities": [
    {{"action": "specific niche opportunity: e.g. 'Target long-tail Arabic keywords competitors ignore'", "reason": "gap in data", "impact": "High|Medium"}}
  ],
  "quick_wins": [
    {{"win": "actionable: e.g. 'Optimize for specific abaya styles - low competition'", "keyword": "exact keyword", "effort": "Low|Medium"}}
  ],
  "content_gaps": ["specific: e.g. 'Size guide content - only 1/7 competitors have it'"],
  "geo_opportunities": ["specific: e.g. 'Saudi-specific payment methods - competitive advantage'"]
}}"""

    text = _llm(prompt, api_keys, max_tokens=1500)
    result = _parse_json(text, {})
    if result and result.get('market_summary'):
        return result
    return _demo_insights(your_domain, competitors, niche, region)


def _demo_insights(your_domain: str, competitors: List[Dict], niche: str, region: str) -> Dict:
    top_domain = competitors[0]['domain'] if competitors else 'المنافس الأول'
    return {
        'market_position': 'Challenger',
        'market_summary': f'[وضع تجريبي] أضف Groq API للحصول على تحليل حقيقي. السوق في {region} لـ {niche} تنافسي.',
        'your_strengths': ['أضف Groq API لاكتشاف نقاط قوتك الحقيقية'],
        'your_weaknesses': [f'{top_domain} يتفوق عليك — أضف API لمعرفة السبب الدقيق'],
        'direct_threats': [{'competitor': top_domain, 'threat': 'يحتل مرتبة أعلى في Google', 'their_advantage': 'بيانات غير متاحة'}],
        'opportunities': [{'action': 'أضف Groq API', 'reason': 'للحصول على فرص حقيقية مبنية على البيانات', 'impact': 'High'}],
        'quick_wins': [{'win': 'أضف مفتاح Groq API في الإعدادات', 'keyword': '', 'effort': 'Low'}],
        'content_gaps': ['أضف API لاكتشاف الفجوات الحقيقية'],
        'geo_opportunities': [f'استهداف كلمات {niche} في {region} بمحتوى عربي']
    }


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def analyze_competitors(your_url: str, region: str = 'Saudi Arabia',
                         industry: str = '', count: int = 7,
                         api_keys: dict = None) -> Dict:
    api_keys = api_keys or {}
    your_domain = _extract_domain(your_url)
    
    print(f"\n[Competitor Intel] Starting analysis for {your_domain} in {region}")
    print(f"  Industry hint: {industry or 'auto-detect'}")
    print(f"  Target count: {count} competitors")

    # Step 1: Detect niche
    print(f"\n[Step 1/6] Detecting niche...")
    niche_data = detect_niche(your_domain, your_url, industry, api_keys)
    niche = niche_data.get('niche', industry or your_domain)
    print(f"  Detected: {niche} ({niche_data.get('category','unknown')})")
    print(f"  Search queries: {niche_data.get('search_queries',[])}")

    # Step 2: Discover competitors
    print(f"\n[Step 2/6] Discovering competitors...")
    raw_competitors = discover_competitors(niche_data, your_domain, region, count, api_keys)
    print(f"  Found {len(raw_competitors)} competitors")

    # Step 3: Enrich each competitor (with progress logging)
    print(f"\n[Step 3/6] Enriching {len(raw_competitors)} competitors...")
    enriched = []
    for idx, comp in enumerate(raw_competitors, 1):
        url = comp.get('url') or f"https://{comp['domain']}"
        print(f"  [{idx}/{len(raw_competitors)}] Analyzing {comp['domain']}...")
        
        ps      = get_pagespeed(url)
        content = get_content_signals(url)
        content['domain'] = comp['domain']  # Pass domain for brand detection
        content['competitor_type'] = comp.get('competitor_type', 'Real')
        score   = calculate_competitor_score(ps, content, comp.get('serp_position', 10), niche, api_keys, is_your_site=False)
        
        enriched.append({
            **comp,
            'pagespeed': ps,
            'content': content,
            'score': score,
        })
        print(f"      Score: {score.get('total','?')}/100 | Brand: {score.get('brand_tier','?')} | SEO: {ps.get('seo','?')} | Perf: {ps.get('performance','?')}")

    # Sort by score descending
    enriched.sort(key=lambda x: x.get('score',{}).get('total',0), reverse=True)

    # Step 4: Your own data
    print(f"\n[Step 4/6] Analyzing your site: {your_url}...")
    your_ps      = get_pagespeed(your_url)
    your_content = get_content_signals(your_url)
    your_content['domain'] = your_domain
    your_score   = calculate_competitor_score(your_ps, your_content, 0, niche, api_keys, is_your_site=True)
    print(f"  Your Score: {your_score.get('total','?')}/100 | Brand: {your_score.get('brand_tier','?')} | SEO: {your_ps.get('seo','?')} | Perf: {your_ps.get('performance','?')}")

    # Step 5: Segmentation
    print(f"\n[Step 5/6] Segmenting competitors...")
    real_competitors = [c for c in enriched if c.get('competitor_type','Real') == 'Real']
    content_competitors = [c for c in enriched if c.get('competitor_type') == 'Content']
    platforms = [c for c in enriched if c.get('competitor_type') == 'Platform']
    print(f"  Real: {len(real_competitors)} | Content: {len(content_competitors)} | Platforms: {len(platforms)}")

    # Step 6: AI Insights (grounded)
    print(f"\n[Step 6/6] Generating AI insights...")
    insights = generate_insights(your_domain, your_score, your_content,
                                  enriched, niche, region, api_keys)

    # Step 7: Calculate market position (REALISTIC)
    all_scores = [your_score.get('total', 0)] + [c.get('score',{}).get('total',0) for c in enriched]
    your_rank = sorted(all_scores, reverse=True).index(your_score.get('total', 0)) + 1
    
    your_brand_tier = your_score.get('brand_tier', 'niche')
    competitor_tiers = [c.get('score',{}).get('brand_tier','niche') for c in enriched]
    
    has_global_giants = 'global_giant' in competitor_tiers
    has_regional_leaders = 'regional_leader' in competitor_tiers
    has_established = 'established' in competitor_tiers
    
    if your_brand_tier == 'global_giant':
        market_position = 'Market Leader'
    elif your_brand_tier == 'regional_leader':
        market_position = 'Regional Leader' if has_global_giants else 'Market Leader'
    elif your_brand_tier == 'established':
        market_position = 'Established Player' if (has_global_giants or has_regional_leaders) else 'Market Leader'
    else:
        if has_global_giants or has_regional_leaders:
            market_position = 'Niche Player'
        elif has_established:
            market_position = 'Emerging Challenger'
        elif your_rank <= 2:
            market_position = 'Strong Challenger'
        else:
            market_position = 'New Entrant'
    
    print(f"  Market Position: #{your_rank} - {market_position} (Brand: {your_brand_tier})")
    print(f"  Website Quality: {your_score.get('website_quality','?')}/100 | Market Power: {your_score.get('market_power','?')}/100")
    print(f"\n[Competitor Intel] Analysis complete!\n")

    return {
        'your_domain':   your_domain,
        'your_url':      your_url,
        'your_pagespeed': your_ps,
        'your_content':  your_content,
        'your_score':    your_score,
        'your_rank':     your_rank,
        'market_position': market_position,
        'niche':         niche,
        'niche_detected': niche_data.get('detected', False),
        'region':        region,
        'competitors':   enriched,
        'segmentation':  {
            'real':         real_competitors,
            'content':      content_competitors,
            'platforms':    platforms,
        },
        'competitor_count': len(enriched),
        'insights':      insights,
        'data_sources': {
            'serp':       bool(os.getenv('SERPAPI_KEY') or api_keys.get('serpapi')),
            'pagespeed':  True,
            'ai':         bool(os.getenv('GROQ_API_KEY') or api_keys.get('groq') or
                               os.getenv('OPENAI_API_KEY') or api_keys.get('openai')),
            'content_scraping': True,
        }
    }
