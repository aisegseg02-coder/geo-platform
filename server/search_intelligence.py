"""Complete Search Intelligence Analysis - Clean Professional Output."""
from typing import Dict, List
from server.keyword_engine import extract_keywords_from_audit
from server.keyword_analytics import analyze_keywords, clean_keyword, is_valid_keyword, cluster_by_topic
from server.competitor_analysis import detect_competitors, get_competitor_summary
from server.dataforseo_client import enrich_keywords
from server.geo_services import _serp_api_search, _zenserp_search, _llm
import os
try:
    from . import ai_analysis
except ImportError:
    import ai_analysis

    
def cluster_topics_ai(analytics: Dict, api_keys: dict = None) -> Dict:
    """Group keywords into semantic clusters using LLM if available."""
    if ai_analysis and (api_keys or {}):
        kws = [k['kw'] for k in analytics.get('top_keywords', [])[:20]]
        prompt = (
            f"Group these SEO keywords into 3-5 semantic topic clusters with descriptive names. "
            f"Return ONLY JSON object where keys are cluster names and values are lists of keywords: {', '.join(kws)}"
        )
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception: res = None
            
        if res and res.get('result') and isinstance(res['result'], dict):
            # Transform to expected format: {topic: {'count': N, 'keywords': [...]}}
            final_clusters = {}
            raw_clusters = res['result']
            all_kws_map = {k['kw']: k for k in analytics.get('top_keywords', [])}
            
            for topic, kw_list in raw_clusters.items():
                if isinstance(kw_list, list):
                    cluster_kws = []
                    for k in kw_list:
                        if k in all_kws_map:
                            cluster_kws.append(all_kws_map[k])
                        else:
                            cluster_kws.append({'kw': k, 'count': 1})
                    
                    final_clusters[topic] = {
                        'count': len(cluster_kws),
                        'keywords': sorted(cluster_kws, key=lambda x: x['count'], reverse=True)[:5]
                    }
            if final_clusters:
                return final_clusters

    # Fallback to rule-based clustering
    raw_clusters = cluster_by_topic(analytics.get('top_keywords', []))
    formatted = {}
    for topic, kws in raw_clusters.items():
        formatted[topic] = {
            'count': len(kws),
            'keywords': kws[:5]
        }
    return formatted

def analyze_search_intent_ai(analytics: Dict, pages: List[Dict], api_keys: dict = None) -> Dict:
    """Classify keyword search intent distribution using LLM if available."""
    if ai_analysis and (api_keys or {}):
        # We can use a lightweight prompt to classify the top 15 keywords
        kws = [k['kw'] for k in analytics.get('top_keywords', [])[:15]]
        prompt = f"Classify the search intent of these keywords into Informational, Commercial, Transactional, Navigational. Return ONLY JSON distribution like {{'Informational': 40, 'Commercial': 30, ...}} based on their prevalence: {', '.join(kws)}"
        
        # Try Groq or OpenAI
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception:
            res = None
            
        if res and res.get('result'):
            dist = res['result']
            # Ensure keys exist
            for k in ['Informational', 'Commercial', 'Transactional', 'Navigational']:
                if k not in dist: dist[k] = 0
            # Ensure key is a function for max
            top_intent = max(dist.keys(), key=lambda k: dist.get(k, 0))
            return { 'distribution': dist, 'top_intent': top_intent }

    # Fallback to simple rule-based
    return analyze_search_intent(analytics)

def analyze_search_intent(analytics: Dict) -> Dict:
    """Classify keyword search intent distribution (Rule-based, 2026 standards)."""
    intents = {'Informational': 0, 'Commercial': 0, 'Transactional': 0, 'Navigational': 0}
    kws = analytics.get('top_keywords', [])
    if not kws: return {'distribution': intents, 'top_intent': 'N/A'}

    TRANSACTIONAL = ['buy','shop','price','sale','order','store','checkout','discount','offer','deal',
                     'سعر','شراء','طلب','متجر','عرض','خصم','اشتري','احجز','book','subscribe','hire','get']
    COMMERCIAL    = ['best','review','vs','compare','top','rating','alternative','agency','service','company',
                     'افضل','أفضل','مراجعة','مقارنة','شركة','خدمة','وكالة','provider','solution','platform']
    INFORMATIONAL = ['how','what','why','guide','tutorial','tips','trends','learn','understand','explain',
                     'كيف','ماذا','لماذا','شرح','نصائح','دليل','تعلم','مقال','blog','article','case study']
    # Navigational = brand/domain names only — NOT the default

    for item in kws:
        kw = item['kw'].lower()
        if any(w in kw for w in TRANSACTIONAL):
            item['intent'] = 'Transactional'
        elif any(w in kw for w in COMMERCIAL):
            item['intent'] = 'Commercial'
        elif any(w in kw for w in INFORMATIONAL):
            item['intent'] = 'Informational'
        elif len(kw.split()) == 1 and kw.isalpha():  # single brand-like word
            item['intent'] = 'Navigational'
        else:
            # Default to Commercial for service/agency pages (not Navigational)
            item['intent'] = 'Commercial'
        intents[item['intent']] += item.get('count', 1)

    total = sum(intents.values()) or 1
    dist = {k: round((v / total) * 100, 1) for k, v in intents.items()}
    top_intent = max(intents, key=lambda k: intents[k])
    return {'distribution': dist, 'top_intent': top_intent}
def detect_content_gaps_ai(analytics: Dict, pages: List[Dict], api_keys: dict = None) -> List[str]:
    """Identify real content gaps via LLM."""
    if ai_analysis and (api_keys or {}):
        kws = [k['kw'] for k in analytics.get('top_keywords', [])[:20]]
        prompt = f"Based on these keywords found on a website: {', '.join(kws)}, identify 4 specific SEO content gaps or missing subtopics. Return ONLY a JSON list of strings."
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception:
            res = None
            
        if res and res.get('result') and isinstance(res['result'], list):
            return res['result']

    # Better generic fallback
    top_kw = "this topic"
    if analytics.get('top_keywords') and len(analytics['top_keywords']) > 0:
        top_kw = analytics['top_keywords'][0].get('kw', 'this topic')
        
    return [f'Advanced {top_kw} guide', 'Industry case studies', 'Latest trends in this sector', 'Expert Q&A']

def calculate_quality_score_ai(analytics: Dict, pages: List[Dict], api_keys: dict = None) -> Dict:
    """Calculate overall content quality score using LLM for depth."""
    if ai_analysis and (api_keys or {}):
        text_sample = " ".join([p.get('text', '')[:600] for p in pages[:2]])
        kws = [k['kw'] for k in analytics.get('top_keywords', [])[:15]]
        prompt = (
            f"PROFESSIONAL SEO AUDIT: Analyze this page content. "
            f"Keywords: {', '.join(kws)}. CONTENT: {text_sample}. "
            "Evaluate: 1. Semantic Depth 2. Keyword Placement 3. Readability. "
            "Return JSON: {'score': 0-100, 'grade': 'A-F', 'feedback': ['list', 'of', '3', 'professional', 'critical', 'notes']}"
        )
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception: res = None
            
        if res and res.get('result') and isinstance(res['result'], dict):
            r = res['result']
            return {
                'score': r.get('score', 70),
                'max_score': 100,
                'percentage': r.get('score', 70),
                'grade': r.get('grade', 'C'),
                'feedback': r.get('feedback', ['AI Audit completed'])
            }
            
    # Fallback to heuristic
    return calculate_quality_score(analytics)

def simulate_serp_intelligence_ai(analytics: Dict, url: str, api_keys: dict = None) -> List[Dict]:
    """Fetch real SERP landscape or use AI to estimate it."""
    primary_kw = analytics['top_keywords'][0]['kw'] if analytics.get('top_keywords') else 'digital marketing'
    api_keys = api_keys or {}
    
    # 1. Try real SerpApi
    serp_data = _serp_api_search(primary_kw, api_key=api_keys.get('serpapi'))
    if serp_data and serp_data.get('organic_results'):
        results = []
        for i, res in enumerate(serp_data['organic_results'][:5], 1):
            results.append({
                'rank': i,
                'domain': res.get('displayed_link', '').split('/')[0],
                'dr': 0, # Placeholder as we'd need another API for DR
                'backlinks': 'N/A',
                'length': 0,
                'content_type': 'Website',
                'intent': 'N/A',
                'why_ranks': res.get('snippet', '')[:100]
            })
        return results

    # 2. Try real ZenSerp
    zen_data = _zenserp_search(primary_kw, api_key=api_keys.get('zenserp'))
    if zen_data and zen_data.get('organic'):
        results = []
        for i, res in enumerate(zen_data['organic'][:5], 1):
            results.append({
                'rank': i,
                'domain': res.get('destination', '').split('/')[0],
                'dr': 0,
                'backlinks': 'N/A',
                'length': 0,
                'content_type': 'Website',
                'intent': 'N/A',
                'why_ranks': res.get('description', '')[:100]
            })
        return results

    # 3. AI Estimation (Better than hardcoded mock)
    if ai_analysis and (api_keys or {}):
        prompt = (
            f"Generate 5 realistic Google SERP results for the keyword '{primary_kw}'. "
            f"Include a mix of content types (blog, service page, guide, tool, directory). "
            f"Return ONLY a JSON list with keys: rank(1-5), domain, dr(0-100), "
            f"backlinks(string), length(word count), content_type(blog/service/guide/tool), "
            f"intent(Informational/Commercial/Transactional), why_ranks(one sentence)."
        )
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception:
            res = None
        if res and res.get('result') and isinstance(res['result'], list):
            return res['result']

    # Final fallback if all else fails
    return []

def get_market_intelligence_ai(competitors: List[Dict], summary: Dict, analytics: Dict, api_keys: dict = None) -> Dict:
    """
    Perform a deep-dive AI analysis on competitors and market positioning.
    Extends simple detection with success factors, positioning maps, and gap analysis.
    """
    market_list = competitors
    analysis_results = {
        'positioning_map': [],
        'success_factors': [],
        'competitive_gaps': [],
        'market_grade': 'B'
    }
    
    if ai_analysis and (api_keys or {}):
        top_kws = [k['kw'] for k in analytics.get('top_keywords', [])[:15]]
        
        # Prepare competitor context for AI
        comp_context = ""
        for c in market_list[:5]:
            ctxts = " | ".join(c.get('contexts', []))
            comp_context += f"- {c['domain']} (Mentions: {c['mentions']}). Context: {ctxts}\n"
            
        prompt = f"""
        Analyze these online competitors and niche trends based on these keywords: {', '.join(top_kws)}.
        Detected Competitors:
        {comp_context if comp_context else "None detected yet. Suggest top 5 industry leaders."}

        Produce a Strategic Intelligence Matrix in JSON format:
        {{
          "positioning_map": [
            {{"name": "Domain", "x": -100..100 (Authority), "y": -100..100 (Focus), "role": "Leader/Niche/Challenger"}}
          ],
          "success_factors": [
            {{"factor": "Specific Strategy", "impact": "High/Medium", "competitors": ["domain1", "domain2"]}}
          ],
          "competitive_gaps": [
            {{"gap": "Underserved Area", "opportunity": "High/Low", "description": "Why the user can win here"}}
          ],
          "market_grade": "A/B/C/D",
          "discovered_competitors": [
            {{"domain": "string", "mentions": "Market Discovery"}}
          ]
        }}
        Return ONLY valid JSON.
        """
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception: res = None
            
        if res and res.get('result') and isinstance(res['result'], dict):
            intel = res['result']
            analysis_results.update(intel)
            
            # If we discovered new competitors, add them to the list
            if not market_list and intel.get('discovered_competitors'):
                market_list = intel['discovered_competitors']
                summary = {
                    'total': len(market_list),
                    'avg_mentions': 0,
                    'top_competitor': market_list[0]['domain'],
                    'top_mentions': 0
                }

    return {
        'found': len(market_list),
        'summary': summary,
        'list': market_list[:10],
        'strategic_intel': analysis_results
    }

def generate_recommendations_ai(analytics: Dict, competitors: List[Dict], api_keys: dict = None) -> List[Dict]:
    """Generate high-impact actionable recommendations via AI."""
    if ai_analysis and (api_keys or {}):
        kws = [k['kw'] for k in analytics.get('top_keywords', [])[:15]]
        prompt = f"Based on these keywords: {', '.join(kws)}, provide 4 high-impact SEO recommendations. Return ONLY JSON list of objects: {{'type': 'string', 'priority': 'high/medium/low', 'title': 'short string', 'description': 'string', 'action': 'string'}}"
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception: res = None
            
        if res and res.get('result') and isinstance(res['result'], list):
            return res['result']

    return generate_recommendations(analytics, competitors)

def calculate_opportunity_score_smart(kw_item: Dict, quality_score: int) -> int:
    """Opportunity = (Volume / Difficulty) weighted by current page quality."""
    # Volume: use real volume if available, else count-based proxy
    volume = kw_item.get('volume')
    if not volume or volume == '—' or volume == 0:
        volume = kw_item.get('count', 1) * 300  # More realistic base
        
    # Difficulty: heuristic if not available
    difficulty = kw_item.get('difficulty') or (20 + kw_item.get('count', 1) * 3)
    difficulty = max(10, min(95, difficulty))
    
    # Base score: Higher volume = higher opportunity, Higher difficulty = lower
    # Formula: (Volume^0.5 / Difficulty) * 10 
    base_score = (pow(volume, 0.5) / difficulty) * 50
    
    # Adjust by quality: if page quality is low (e.g. 40), opportunity to rank for this keyword by fixing content is HIGH
    quality_mult = (100 - quality_score) / 50.0  # e.g. (100-30)/50 = 1.4x bonus
    score = int(base_score * quality_mult)
    
    # Normalize
    return max(1, min(99, score))

def extract_semantic_entities_ai(pages: List[Dict], api_keys: dict = None) -> Dict:
    """Extract real semantic entities via LLM."""
    if ai_analysis and (api_keys or {}):
        text = " ".join([p.get('text', '')[:500] for p in pages[:2]])
        prompt = f"Extract semantic entities from this text. Return JSON with keys: Brand, Category, Product, Audience, Location. TEXT: {text}"
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception:
            res = None
            
        if res and res.get('result'):
            return res['result']

    return {
        'Brand': 'Inferred from Content',
        'Category': 'Services',
        'Product': 'Digital Solutions',
        'Audience': 'Business / Consumer',
        'Location': 'Global'
    }


def calculate_quality_score(analytics: Dict) -> Dict:
    """Calculate content quality score using 2026 GEO/AI-SEO standards."""
    score = 0
    feedback = []
    summary = analytics.get('summary', {})
    top_kws = analytics.get('top_keywords', [])

    # 1. Keyword Intent Quality (25 pts) — are keywords actually searchable/intentful?
    primary_count = summary.get('primary_keywords', 0)
    weak_kws = [k for k in top_kws if len(k.get('kw', '')) <= 3 or k.get('count', 0) == 1]
    weak_ratio = len(weak_kws) / max(len(top_kws), 1)
    if weak_ratio < 0.2 and primary_count >= 8:
        score += 25
        feedback.append('✅ Strong keyword intent quality')
    elif weak_ratio < 0.4 and primary_count >= 4:
        score += 15
        feedback.append('⚠️ Keyword quality is moderate — many weak/non-searchable terms')
    else:
        score += 5
        feedback.append('❌ Poor keyword quality — most terms are too generic or non-searchable')

    # 2. Semantic Coverage / Entity Depth (25 pts)
    total_kws = summary.get('total_keywords', 0)
    clusters = len(analytics.get('clusters', {}))
    if total_kws >= 40 and clusters >= 4:
        score += 25
        feedback.append('✅ Excellent semantic coverage and entity depth')
    elif total_kws >= 20 and clusters >= 2:
        score += 15
        feedback.append('✅ Good semantic coverage')
    else:
        score += 5
        feedback.append('⚠️ Thin semantic coverage — add topic clusters and entities')

    # 3. Search Volume Presence (25 pts) — do keywords have real search demand?
    kws_with_volume = [k for k in top_kws if k.get('volume') and k.get('volume', 0) > 0]
    vol_ratio = len(kws_with_volume) / max(len(top_kws), 1)
    if vol_ratio >= 0.5:
        score += 25
        feedback.append('✅ Strong search volume data — keywords have real demand')
    elif vol_ratio >= 0.2:
        score += 12
        feedback.append('⚠️ Partial volume data — connect DataForSEO for full picture')
    else:
        score += 0
        feedback.append('❌ No search volume data — analysis is blind without it')

    # 4. Content Intent Alignment (25 pts) — not just density
    long_tail_count = summary.get('long_tail_keywords', 0)
    if long_tail_count >= 15:
        score += 25
        feedback.append('✅ Strong long-tail intent coverage')
    elif long_tail_count >= 7:
        score += 15
        feedback.append('⚠️ Add more long-tail intent keywords')
    else:
        score += 5
        feedback.append('❌ Missing long-tail keywords — users search in full phrases')

    return {
        'score': score,
        'max_score': 100,
        'percentage': round(score, 1),
        'grade': get_grade(score),
        'feedback': feedback
    }


def get_grade(percentage: float) -> str:
    """Convert percentage to letter grade."""
    if percentage >= 90:
        return 'A'
    elif percentage >= 80:
        return 'B'
    elif percentage >= 70:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'F'


def generate_recommendations(analytics: Dict, competitors: List[Dict]) -> List[Dict]:
    """Generate actionable 2026 GEO/AI-SEO recommendations."""
    recs = []
    summary = analytics.get('summary', {})
    top_kws = analytics.get('top_keywords', [])

    # 1. Keyword Quality
    weak_kws = [k['kw'] for k in top_kws if len(k.get('kw','')) <= 3 or k.get('count',0) == 1]
    if len(weak_kws) > len(top_kws) * 0.3:
        recs.append({'type':'keyword_quality','priority':'HIGH',
            'title':'Keyword Quality Problem',
            'description':f'{len(weak_kws)} of your top keywords are too short or appear only once — they have no real search demand.',
            'action':'Replace weak keywords with intent-driven phrases (3+ words) that users actually search for'})

    # 2. Search Volume
    no_vol = [k for k in top_kws if not k.get('volume')]
    if len(no_vol) > len(top_kws) * 0.7:
        recs.append({'type':'volume_data','priority':'HIGH',
            'title':'Missing Search Volume Data',
            'description':'Over 70% of keywords have no volume data — your analysis is blind. You cannot prioritize without knowing demand.',
            'action':'Add DataForSEO credentials in .env to get real volume, CPC, and competition data'})

    # 3. Intent Coverage
    intent = analytics.get('intent_distribution', {})
    nav_pct = intent.get('Navigational', 0)
    if nav_pct > 50:
        recs.append({'type':'intent','priority':'HIGH',
            'title':'Wrong Intent Classification',
            'description':f'{nav_pct}% Navigational intent detected — this is likely wrong. Service/agency pages should be Commercial + Informational.',
            'action':'Add Commercial keywords (best, agency, service, solution) and Informational content (guides, how-to, case studies)'})

    # 4. Competitor Gap
    if not competitors:
        recs.append({'type':'competitors','priority':'HIGH',
            'title':'No Competitor Intelligence',
            'description':'Zero competitors detected. Every niche has competitors — the crawler found no external links to analyze.',
            'action':'Add competitor domains manually or crawl deeper pages that reference industry players'})

    # 5. GEO / Local
    local_kws = [k for k in top_kws if any(loc in k.get('kw','').lower() for loc in
        ['saudi','ksa','riyadh','jeddah','egypt','cairo','uae','dubai','مصر','السعودية','الرياض','القاهرة','الإمارات'])]
    if not local_kws:
        recs.append({'type':'geo_local','priority':'MEDIUM',
            'title':'No Local/GEO Keywords Found',
            'description':'No location-specific keywords detected. AI search engines heavily weight local context.',
            'action':'Add city/country keywords: "[service] in Riyadh", "best [service] Saudi Arabia", etc.'})

    # 6. Entity Coverage
    clusters = len(analytics.get('clusters', {}))
    if clusters < 3:
        recs.append({'type':'entities','priority':'MEDIUM',
            'title':'Weak Entity & Topic Coverage',
            'description':f'Only {clusters} topic clusters — AI models need rich entity graphs to cite your content.',
            'action':'Add Named Entity content: Organization, People, Products, Locations with Schema.org markup'})

    # 7. Long-tail / AI Query Coverage
    lt = summary.get('long_tail_keywords', 0)
    if lt < 10:
        recs.append({'type':'longtail','priority':'MEDIUM',
            'title':'Missing AI Query Coverage',
            'description':f'Only {lt} long-tail keywords. ChatGPT and Perplexity answer full questions — not single words.',
            'action':'Create FAQ sections and "how to" content targeting full user questions (5+ word phrases)'})

    return recs


def format_professional_output(report: Dict) -> str:
    """Format report as professional text output."""
    lines = []
    
    lines.append("=" * 80)
    lines.append("🔍 SEARCH INTELLIGENCE ANALYSIS")
    lines.append("=" * 80)
    
    lines.append(f"\n✅ {report['message']}")
    lines.append(f"\n📄 Pages Analyzed: {report['pages_analyzed']}")
    lines.append(f"📝 Total Words: {report['total_words']}")
    
    # Quality Score
    quality = report['metrics']['quality_score']
    lines.append(f"\n🎯 QUALITY SCORE: {quality['score']}/{quality['max_score']} ({quality['percentage']}%) - Grade: {quality['grade']}")
    lines.append("-" * 80)
    for feedback in quality['feedback']:
        lines.append(f"  {feedback}")
    
    # Keyword Results
    lines.append(f"\n\n📊 KEYWORD RESULTS ({report['keyword_results']['total_found']} keywords found)")
    lines.append("=" * 80)
    
    # Primary Keywords
    primary = report['keyword_results']['classification']['primary']
    lines.append(f"\n1️⃣ PRIMARY KEYWORDS ({primary['count']} keywords)")
    lines.append("-" * 80)
    for kw in primary['keywords'][:10]:
        vol = f"Vol: {kw.get('volume', 'N/A')}" if kw.get('volume') else ""
        cpc = f"CPC: ${kw.get('cpc', 0):.2f}" if kw.get('cpc') else ""
        comp = f"Comp: {kw.get('competition', 'N/A')}" if kw.get('competition') else ""
        density = f"Density: {kw.get('density', 0):.2f}%" if kw.get('density') else ""
        
        meta = " | ".join(filter(None, [vol, cpc, comp, density]))
        lines.append(f"  • {kw['kw']} ({kw['count']}) {meta}")
    
    # Secondary Keywords
    secondary = report['keyword_results']['classification']['secondary']
    lines.append(f"\n2️⃣ SECONDARY KEYWORDS ({secondary['count']} keywords)")
    lines.append("-" * 80)
    for kw in secondary['keywords'][:5]:
        lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    # Topic Clusters
    lines.append(f"\n\n🎯 TOPIC CLUSTERS")
    lines.append("=" * 80)
    for topic, data in report['topic_clusters'].items():
        lines.append(f"\n{topic} ({data['count']} keywords)")
        for kw in data['keywords']:
            lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    # Competitors
    lines.append(f"\n\n🏆 COMPETITORS")
    lines.append("=" * 80)
    comp_summary = report['competitors']['summary']
    if report['competitors']['found'] > 0:
        lines.append(f"Found: {report['competitors']['found']} competitors")
        lines.append(f"Top Competitor: {comp_summary['top_competitor']} ({comp_summary['top_mentions']} mentions)")
        lines.append("\nTop Competitors:")
        for comp in report['competitors']['list'][:5]:
            lines.append(f"  • {comp['domain']} ({comp['mentions']} mentions)")
    else:
        lines.append(" No external competitors found.")
        lines.append("\nThis could mean:")
        lines.append("  • Page has no external links")
        lines.append("  • All links are to social media/CDNs")
        lines.append("  • Consider adding authoritative references")
    
    # Recommendations
    lines.append(f"\n\n💡 RECOMMENDATIONS")
    lines.append("=" * 80)
    for i, rec in enumerate(report['recommendations'], 1):
        priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec['priority'], '⚪')
        lines.append(f"\n{i}. {priority_icon} {rec['title']} [{rec['priority'].upper()}]")
        lines.append(f"   {rec['description']}")
        lines.append(f"   ➡️  Action: {rec['action']}")
    
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)

def _analyze_geo_local(analytics: Dict, pages: List[Dict], source_url: str) -> Dict:
    """Detect local/GEO signals and missing local keywords."""
    LOCAL_REGIONS = {
        'Saudi Arabia': ['سعودية','السعودية','رياض','جدة','مكة','دمام','saudi','riyadh','jeddah','ksa','mecca','dammam'],
        'Egypt':        ['مصر','قاهرة','اسكندرية','egypt','cairo','alexandria'],
        'UAE':          ['إمارات','دبي','أبوظبي','uae','dubai','abudhabi'],
        'Jordan':       ['الأردن','عمان','jordan','amman'],
        'Kuwait':       ['كويت','kuwait'],
    }
    all_text = ' '.join(p.get('text','') + ' ' + p.get('title','') for p in pages).lower()
    top_kws = [k.get('kw','').lower() for k in analytics.get('top_keywords', [])]

    detected_regions = []
    for region, signals in LOCAL_REGIONS.items():
        if any(s in all_text or any(s in kw for kw in top_kws) for s in signals):
            detected_regions.append(region)

    # Suggest missing local keywords based on detected region
    suggestions = []
    primary_kw = top_kws[0] if top_kws else 'your service'
    for region in detected_regions:
        cities = LOCAL_REGIONS[region][:2]
        for city in cities:
            suggestions.append(f'{primary_kw} in {city}')
            suggestions.append(f'best {primary_kw} {city}')

    if not detected_regions:
        suggestions = [
            f'{primary_kw} in Saudi Arabia',
            f'best {primary_kw} Riyadh',
            f'{primary_kw} agency Egypt',
            f'{primary_kw} UAE',
        ]

    has_maps = 'maps.google' in all_text or 'google.com/maps' in all_text
    has_schema_local = 'localBusiness' in all_text or 'LocalBusiness' in all_text

    return {
        'detected_regions': detected_regions,
        'has_local_keywords': len(detected_regions) > 0,
        'has_google_maps': has_maps,
        'has_local_schema': has_schema_local,
        'missing_local_keywords': suggestions[:8],
        'geo_score': min(100, len(detected_regions) * 25 + (20 if has_maps else 0) + (20 if has_schema_local else 0)),
        'verdict': 'Strong local presence' if detected_regions else '⚠️ No local/GEO signals detected — missing major ranking opportunity'
    }


def _score_keyword_quality(analytics: Dict) -> Dict:
    """Score each keyword by quality: searchability, length, intent signal."""
    top_kws = analytics.get('top_keywords', [])
    scored = []
    for kw in top_kws:
        word = kw.get('kw', '')
        words = word.split()
        vol = kw.get('volume') or 0
        count = kw.get('count', 1)

        # Quality signals
        has_volume   = vol > 0
        is_phrase    = len(words) >= 2
        is_long_tail = len(words) >= 3
        has_intent   = any(w in word.lower() for w in [
            'best','how','guide','service','agency','price','buy','review',
            'أفضل','كيف','دليل','خدمة','سعر','شركة'
        ])
        not_generic  = len(word) > 4 and count > 1

        q = 0
        if has_volume:   q += 35
        if is_phrase:    q += 20
        if is_long_tail: q += 15
        if has_intent:   q += 20
        if not_generic:  q += 10

        scored.append({**kw, 'quality_score': min(100, q),
                       'quality_label': 'Strong' if q >= 70 else ('Medium' if q >= 40 else 'Weak')})

    strong = [k for k in scored if k['quality_label'] == 'Strong']
    weak   = [k for k in scored if k['quality_label'] == 'Weak']
    return {
        'scored_keywords': scored[:20],
        'strong_count': len(strong),
        'weak_count': len(weak),
        'verdict': f'{len(strong)} strong keywords, {len(weak)} weak/non-searchable keywords found'
    }


def run_complete_analysis(pages: List[Dict], source_url: str, enrich_data: bool = True, api_keys: dict = None) -> Dict:
    """
    Run complete search intelligence analysis.
    
    Returns professional analytics report with:
    - Clean keyword extraction
    - Keyword classification (primary/secondary/long-tail)
    - Topic clustering
    - Keyword density
    - Coverage score
    - Competitor detection
    - DataForSEO enrichment (volume, CPC, competition)
    """
    
    # Build audit object
    audit_obj = {'pages': pages}
    
    # Extract keywords with analytics
    try:
        analytics = extract_keywords_from_audit(
            audit_obj,
            top_n=50,
            enrich=enrich_data,
            analytics=True
        )
        
        # Ensure analytics is a dict
        if not isinstance(analytics, dict):
            # Fallback: create basic analytics structure
            analytics = {
                'summary': {
                    'total_keywords': 0,
                    'avg_frequency': 0,
                    'primary_keywords': 0,
                    'secondary_keywords': 0,
                    'long_tail_keywords': 0
                },
                'top_keywords': [],
                'classification': {
                    'primary': [],
                    'secondary': [],
                    'long_tail': []
                },
                'clusters': {},
                'coverage': None
            }
    except Exception as e:
        # Fallback analytics on error
        analytics = {
            'summary': {
                'total_keywords': 0,
                'avg_frequency': 0,
                'primary_keywords': 0,
                'secondary_keywords': 0,
                'long_tail_keywords': 0
            },
            'top_keywords': [],
            'classification': {
                'primary': [],
                'secondary': [],
                'long_tail': []
            },
            'clusters': {},
            'coverage': None
        }
    
    # Detect competitors
    try:
        competitors = detect_competitors(pages, source_url, min_mentions=1)
        competitor_summary = get_competitor_summary(competitors)
    except Exception:
        competitors = []
        competitor_summary = {'total': 0, 'avg_mentions': 0, 'top_competitor': None, 'top_mentions': 0}
    
    # Calculate total words
    total_words = 0
    try:
        total_words = sum(len(str(p.get('text', '')).split()) for p in pages)
    except Exception:
        total_words = 0
    
    # Ensure analytics is the advanced dict format
    if isinstance(analytics, list):
        analytics = {'summary': {'total_keywords': len(analytics)}, 'top_keywords': analytics, 'classification': {}}
    
    analytics_dict = analytics if isinstance(analytics, dict) else {}
    
    # Build professional report
    report = {
        'status': 'completed',
        'message': 'Your GEO tool finished analyzing the page and extracted keywords and their frequency.',
        'pages_analyzed': len(pages),
        'total_words': total_words,
        
        # Keyword Results Section
        'keyword_results': {
            'total_found': int((analytics_dict.get('summary') or {}).get('total_keywords', 0)),
            'top_keywords': analytics_dict.get('top_keywords', [])[:30],
            'classification': {
                'primary': {
                    'count': len((analytics_dict.get('classification') or {}).get('primary', [])),
                    'keywords': (analytics_dict.get('classification') or {}).get('primary', [])[:10]
                },
                'secondary': {
                    'count': len((analytics_dict.get('classification') or {}).get('secondary', [])),
                    'keywords': (analytics_dict.get('classification') or {}).get('secondary', [])[:10]
                },
                'long_tail': {
                    'count': len((analytics_dict.get('classification') or {}).get('long_tail', [])),
                    'keywords': (analytics_dict.get('classification') or {}).get('long_tail', [])[:10]
                }
            }
        },
        
        # Topic Clusters (AI-Driven)
        'topic_clusters': cluster_topics_ai(analytics_dict, api_keys),
        
        # Metrics
        'metrics': {
            'coverage': analytics_dict.get('coverage', 0),
            'quality_score': calculate_quality_score(analytics_dict) if analytics_dict else {'score': 0, 'label': 'N/A'}
        },
        
        # Market Intelligence (Competitors)
        'competitors': get_market_intelligence_ai(competitors, competitor_summary, analytics_dict, api_keys),
        
        # Phase 2: Professional SEO (AI-Driven)
        'intent_analysis': analyze_search_intent_ai(analytics_dict, pages, api_keys),
        'content_gaps': detect_content_gaps_ai(analytics_dict, pages, api_keys),
        'serp_intelligence': simulate_serp_intelligence_ai(analytics_dict, source_url, api_keys),
        'entities': extract_semantic_entities_ai(pages, api_keys),
        'geo_local': _analyze_geo_local(analytics_dict, pages, source_url),
        'keyword_quality': _score_keyword_quality(analytics_dict),
        
        # Recommendations
        'recommendations': generate_recommendations_ai(analytics_dict, competitors, api_keys)
    }
    
    # Update metrics with AI Quality Score
    report['metrics']['quality_score'] = calculate_quality_score_ai(analytics_dict, pages, api_keys)
    
    # Calculate Keyword Opportunity Score for top keywords with smart difficulty
    q_score = 70
    metrics = report.get('metrics')
    if isinstance(metrics, dict):
        qs = metrics.get('quality_score')
        if isinstance(qs, dict):
            q_score_val = qs.get('score', 70)
            try:
                q_score = int(q_score_val)
            except (ValueError, TypeError):
                q_score = 70
        
    for kw in report.get('keyword_results', {}).get('top_keywords', []):
        if isinstance(kw, dict):
            kw['opportunity_score'] = calculate_opportunity_score_smart(kw, q_score)
    
    return report
