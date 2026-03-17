"""Complete Search Intelligence Analysis - Clean Professional Output."""
from typing import Dict, List
from server.keyword_engine import extract_keywords_from_audit
from server.keyword_analytics import analyze_keywords, clean_keyword, is_valid_keyword, cluster_by_topic
from server.competitor_analysis import detect_competitors, get_competitor_summary
from server.dataforseo_client import enrich_keywords
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
    """Classify keyword search intent distribution (Rule-based)."""
    intents = {'Informational': 0, 'Commercial': 0, 'Transactional': 0, 'Navigational': 0}
    kws = analytics.get('top_keywords', [])
    if not kws: return {'distribution': intents, 'top_intent': 'N/A'}
    
    # Simple rule-based intent classifier (English + Arabic)
    for item in kws:
        kw = item['kw'].lower()
        # Transactional
        if any(w in kw for w in ['buy', 'shop', 'price', 'sale', 'order', 'store', 'سعر', 'شراء', 'طلب', 'متجر']):
            item['intent'] = 'Transactional'
        # Commercial
        elif any(w in kw for w in ['best', 'review', 'vs', 'compare', 'top', 'افضل', 'أفضل', 'مراجعة', 'مقارنة']):
            item['intent'] = 'Commercial'
        # Informational
        elif any(w in kw for w in ['how', 'what', 'guide', 'tutorial', 'tips', 'trends', 'كيف', 'ماذا', 'شرح', 'نصائح', 'دليل']):
            item['intent'] = 'Informational'
        else:
            item['intent'] = 'Navigational'
        
        intents[item['intent']] += item.get('count', 1)

    total = sum(intents.values())
    if total == 0: total = 1
    dist = {k: round((v/total)*100, 1) for k, v in intents.items()}
    # Fix max key for lint
    top_intent = max(intents.keys(), key=lambda k: intents.get(k, 0))
    return {
        'distribution': dist,
        'top_intent': top_intent
    }
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
    """Simulate SERP landscape accurately using AI for the specific niche."""
    primary_kw = "this topic"
    if analytics.get('top_keywords'):
        primary_kw = analytics['top_keywords'][0]['kw']
        
    if ai_analysis and (api_keys or {}):
        prompt = f"Generate 3 realistic SERP results for the keyword '{primary_kw}'. Return ONLY a JSON list of objects with keys: rank (1-3), domain, dr (0-100), backlinks (string like '1.2k'), length (words, usually 1000-3000)."
        
        res = None
        try:
            if (api_keys or {}).get('groq'):
                res = ai_analysis.analyze_with_groq([{'url': 'dummy', 'text': prompt}], api_key=api_keys['groq'])
            elif (api_keys or {}).get('openai'):
                res = ai_analysis.analyze_with_openai([{'url': 'dummy', 'text': prompt}], api_key=api_keys['openai'])
        except Exception: res = None
            
        if res and res.get('result') and isinstance(res['result'], list):
            return res['result']

    # Fallback to smart-ish simulation
    domain = 'example.com'
    if url:
        domain = url.split('//')[-1].split('/')[0] if '//' in url else url
    return [
        {'rank': 1, 'domain': 'wikipedia.org', 'dr': 98, 'backlinks': '50k+', 'length': 4500},
        {'rank': 2, 'domain': 'authority-niche.com', 'dr': 85, 'backlinks': '2.4k', 'length': 2800},
        {'rank': 3, 'domain': f'direct-comp-{domain}', 'dr': 42, 'backlinks': '150', 'length': 1500}
    ]

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
    """Calculate overall content quality score."""
    score = 0
    max_score = 100
    feedback = []
    
    # Keyword diversity (30 points)
    total_kws = analytics['summary']['total_keywords']
    if total_kws >= 50:
        score += 30
        feedback.append('✅ Excellent keyword diversity')
    elif total_kws >= 30:
        score += 20
        feedback.append('✅ Good keyword diversity')
    elif total_kws >= 15:
        score += 10
        feedback.append('⚠️ Moderate keyword diversity')
    else:
        feedback.append('❌ Low keyword diversity - add more content')
    
    # Primary keywords (25 points)
    primary_count = analytics['summary']['primary_keywords']
    if primary_count >= 10:
        score += 25
        feedback.append('✅ Strong primary keyword presence')
    elif primary_count >= 5:
        score += 15
        feedback.append('✅ Good primary keywords')
    else:
        score += 5
        feedback.append('⚠️ Need more primary keywords')
    
    # Topic clustering (25 points)
    clusters = len(analytics.get('clusters', {}))
    if clusters >= 4:
        score += 25
        feedback.append('✅ Well-organized topic structure')
    elif clusters >= 2:
        score += 15
        feedback.append('✅ Basic topic organization')
    else:
        score += 5
        feedback.append('⚠️ Limited topic coverage')
    
    # Keyword density balance (20 points)
    avg_freq = analytics['summary']['avg_frequency']
    if 3 <= avg_freq <= 8:
        score += 20
        feedback.append('✅ Optimal keyword density')
    elif 2 <= avg_freq <= 10:
        score += 10
        feedback.append('✅ Acceptable keyword density')
    else:
        feedback.append('⚠️ Keyword density needs adjustment')
    
    return {
        'score': score,
        'max_score': max_score,
        'percentage': round(score / max_score * 100, 1),
        'grade': get_grade(score / max_score * 100),
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
    """Generate actionable recommendations."""
    recommendations = []
    
    # Keyword recommendations
    primary_count = analytics['summary']['primary_keywords']
    if primary_count < 5:
        recommendations.append({
            'type': 'keywords',
            'priority': 'high',
            'title': 'Increase Primary Keywords',
            'description': f'You have only {primary_count} primary keywords. Aim for at least 5-10 strong keywords.',
            'action': 'Add more content focused on your main topics'
        })
    
    # Density recommendations
    avg_freq = analytics['summary']['avg_frequency']
    if avg_freq < 2:
        recommendations.append({
            'type': 'density',
            'priority': 'medium',
            'title': 'Improve Keyword Frequency',
            'description': 'Keywords appear too infrequently. Increase repetition naturally.',
            'action': 'Mention key terms 3-5 times per page'
        })
    elif avg_freq > 10:
        recommendations.append({
            'type': 'density',
            'priority': 'medium',
            'title': 'Reduce Keyword Stuffing',
            'description': 'Keywords appear too frequently. This may hurt SEO.',
            'action': 'Use synonyms and vary your language'
        })
    
    # Topic coverage
    clusters = len(analytics.get('clusters', {}))
    if clusters < 3:
        recommendations.append({
            'type': 'topics',
            'priority': 'medium',
            'title': 'Expand Topic Coverage',
            'description': f'Only {clusters} topic clusters found. Diversify your content.',
            'action': 'Cover related subtopics and use cases'
        })
    
    # Competitor recommendations
    if len(competitors) == 0:
        recommendations.append({
            'type': 'competitors',
            'priority': 'low',
            'title': 'Add External Links',
            'description': 'No competitor links found. Consider linking to authoritative sources.',
            'action': 'Link to industry resources and references'
        })
    
    # Long-tail keywords
    long_tail_count = analytics['summary']['long_tail_keywords']
    if long_tail_count < 10:
        recommendations.append({
            'type': 'long_tail',
            'priority': 'medium',
            'title': 'Target Long-tail Keywords',
            'description': 'Add more specific, detailed keyword phrases.',
            'action': 'Create content for specific user queries'
        })
    
    return recommendations


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
        
        # New Hooks for Phase 2: Professional SEO (AI-Driven)
        'intent_analysis': analyze_search_intent_ai(analytics_dict, pages, api_keys),
        'content_gaps': detect_content_gaps_ai(analytics_dict, pages, api_keys),
        'serp_intelligence': simulate_serp_intelligence_ai(analytics_dict, source_url, api_keys),
        'entities': extract_semantic_entities_ai(pages, api_keys),
        
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
