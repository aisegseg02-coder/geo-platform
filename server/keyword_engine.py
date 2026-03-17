import re
from pathlib import Path
from html import unescape

try:
    from .dataforseo_client import enrich_keywords
except ImportError:
    def enrich_keywords(kws, **kwargs):
        return [{'kw': k, 'volume': None, 'cpc': None} for k in kws]

try:
    from .keyword_analytics import analyze_keywords, format_analytics_report
except ImportError:
    def analyze_keywords(kws, **kwargs):
        return {'summary': {}, 'top_keywords': kws}
    def format_analytics_report(analytics):
        return str(analytics)

try:
    import spacy
    _nlp = None
    try:
        _nlp = spacy.load('en_core_web_sm')
    except Exception:
        try:
            _nlp = spacy.load('xx_ent_wiki_sm')
        except Exception:
            _nlp = None
except Exception:
    _nlp = None

_STOPWORDS = set([
    'the','and','for','with','from','this','that','are','you','your','www','http','https','com','org','net','page','pages',
    'about','more','shop','home','contact','search','menu','cart','login','sign','account','view','add','buy','price'
])

def _clean_html(text):
    """Strip HTML tags and decode entities."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    return text

def extract_keywords_from_audit(audit_obj, top_n=20, enrich=True, analytics=False, expected_keywords=None):
    """Extract candidate keywords from an audit object.

    Tries to use spaCy noun-chunk extraction when available, otherwise
    falls back to simple regex tokenization and frequency counts. Returns
    a list of dicts: {kw: <keyword>, count: <n>, volume: <int>, cpc: <float>} ordered by count desc.
    
    Args:
        audit_obj: Audit dictionary with pages
        top_n: Number of keywords to return
        enrich: Whether to enrich with DataForSEO volume/CPC data
        analytics: Whether to return full analytics report
        expected_keywords: List of expected keywords for coverage analysis
    """
    pages = audit_obj.get('pages', []) if isinstance(audit_obj, dict) else []
    texts = []
    for p in pages:
        title = p.get('title', '')
        headings = ' '.join(h.get('text', '') if isinstance(h, dict) else str(h) for h in p.get('headings', []))
        paras = p.get('paragraphs', [])
        if isinstance(paras, list):
            paras = ' '.join(par.get('text', '') if isinstance(par, dict) else str(par) for par in paras)
        else:
            paras = str(paras)
        raw = p.get('text') or p.get('content') or p.get('html') or ''
        cleaned = _clean_html(raw)
        texts.append(f"{title} {title} {headings} {paras} {cleaned}")
    combined = '\n'.join(texts)
    if not combined.strip():
        return []

    # spaCy path
    if _nlp is not None:
        try:
            doc = _nlp(combined[:100000])  # limit to avoid memory issues
            candidates = []
            for chunk in doc.noun_chunks:
                txt = ' '.join([t.text for t in chunk if not t.is_stop]).strip().lower()
                if len(txt) < 3 or txt in _STOPWORDS:
                    continue
                candidates.append(txt)
            for ent in doc.ents:
                txt = ent.text.strip().lower()
                if len(txt) < 3 or txt in _STOPWORDS:
                    continue
                candidates.append(txt)
            counts = {}
            for c in candidates:
                counts[c] = counts.get(c, 0) + 1
            items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            results = [{'kw': k, 'count': v} for k, v in items]
            
            # If analytics requested, process through analytics
            if analytics:
                total_words = len(combined.split())
                analytics_report = analyze_keywords(results, total_words=total_words, expected_keywords=expected_keywords)
                
                # Enrich if requested
                if enrich and analytics_report['all_keywords']:
                    all_kws = analytics_report['all_keywords']
                    enriched = enrich_keywords([r['kw'] for r in all_kws[:50]])
                    enriched_map = {e['kw']: e for e in enriched}
                    
                    for r in all_kws:
                        if r['kw'] in enriched_map:
                            r.update(enriched_map[r['kw']])
                    for r in analytics_report['top_keywords']:
                        if r['kw'] in enriched_map:
                            r.update(enriched_map[r['kw']])
                    for category in ['primary', 'secondary', 'long_tail']:
                        for r in analytics_report['classification'][category]:
                            if r['kw'] in enriched_map:
                                r.update(enriched_map[r['kw']])
                    for cluster_kws in analytics_report['clusters'].values():
                        for r in cluster_kws:
                            if r['kw'] in enriched_map:
                                r.update(enriched_map[r['kw']])
                
                return analytics_report
            
            # Simple mode
            results = results[:top_n]
            if enrich:
                enriched = enrich_keywords([r['kw'] for r in results])
                enriched_map = {e['kw']: e for e in enriched}
                for r in results:
                    if r['kw'] in enriched_map:
                        r.update(enriched_map[r['kw']])
            return results
        except Exception:
            pass

    # simple regex fallback (supports Arabic letters too)
    words = re.findall(r"[\w\u0600-\u06FF]{3,}", combined.lower())
    # extract 2-3 word phrases
    phrases = re.findall(r"\b([\w\u0600-\u06FF]+(?:\s+[\w\u0600-\u06FF]+){1,2})\b", combined.lower())
    counts = {}
    for w in words:
        if w in _STOPWORDS or len(w) < 3:
            continue
        counts[w] = counts.get(w, 0) + 1
    for p in phrases:
        if len(p) > 5 and not any(s in p for s in _STOPWORDS):
            counts[p] = counts.get(p, 0) + 2  # boost phrases
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n * 2]  # Get more for analytics
    
    results = [{'kw': k, 'count': v} for k, v in items]
    
    # Calculate total words for density
    total_words = len(words)
    
    # Run analytics if requested
    if analytics:
        analytics_report = analyze_keywords(results, total_words=total_words, expected_keywords=expected_keywords)
        
        # Enrich with DataForSEO if requested
        if enrich and analytics_report['all_keywords']:
            # Enrich all keywords
            all_kws = analytics_report['all_keywords']
            enriched = enrich_keywords([r['kw'] for r in all_kws[:50]])  # Enrich top 50
            enriched_map = {e['kw']: e for e in enriched}
            
            # Update all keyword lists with enrichment data
            for r in all_kws:
                if r['kw'] in enriched_map:
                    r.update(enriched_map[r['kw']])
            
            # Update top_keywords
            for r in analytics_report['top_keywords']:
                if r['kw'] in enriched_map:
                    r.update(enriched_map[r['kw']])
            
            # Update classification keywords
            for category in ['primary', 'secondary', 'long_tail']:
                for r in analytics_report['classification'][category]:
                    if r['kw'] in enriched_map:
                        r.update(enriched_map[r['kw']])
            
            # Update cluster keywords
            for cluster_kws in analytics_report['clusters'].values():
                for r in cluster_kws:
                    if r['kw'] in enriched_map:
                        r.update(enriched_map[r['kw']])
        
        return analytics_report
    
    # Standard flow (no analytics)
    results = results[:top_n]
    
    # Enrich with DataForSEO if requested
    if enrich and results:
        enriched = enrich_keywords([r['kw'] for r in results])
        enriched_map = {e['kw']: e for e in enriched}
        for r in results:
            if r['kw'] in enriched_map:
                r.update(enriched_map[r['kw']])
    
    return results
