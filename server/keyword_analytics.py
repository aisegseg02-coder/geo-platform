"""Advanced Keyword Analytics with Topic Clustering and Density Analysis."""
import re
from collections import defaultdict
from typing import List, Dict, Tuple

try:
    import spacy
    _nlp = None
    try:
        _nlp = spacy.load('en_core_web_sm')
    except:
        pass
except:
    _nlp = None

# Extended stopwords for better filtering
STOPWORDS = set([
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'you', 'your',
    'www', 'http', 'https', 'com', 'org', 'net', 'page', 'pages', 'about',
    'more', 'shop', 'home', 'contact', 'search', 'menu', 'cart', 'login',
    'sign', 'account', 'view', 'add', 'buy', 'price', 'our', 'all', 'new',
    'get', 'now', 'here', 'click', 'read', 'see', 'find', 'back', 'next',
    'prev', 'skip', 'main', 'content', 'footer', 'header', 'sidebar', 'nav',
    'navigation', 'copyright', 'reserved', 'rights', 'privacy', 'terms',
    'conditions', 'policy', 'subscribe', 'newsletter', 'email', 'follow',
    'share', 'like', 'tweet', 'post', 'comment', 'reply', 'submit'
])

# Arabic stopwords
ARABIC_STOPWORDS = set([
    'في', 'من', 'إلى', 'على', 'عن', 'مع', 'هذا', 'هذه', 'التي', 'الذي',
    'كل', 'بعض', 'أو', 'لكن', 'ثم', 'قد', 'كان', 'لم', 'لن', 'أن', 'إن',
    'ما', 'لا', 'نحن', 'هم', 'هي', 'هو', 'أنت', 'أنا', 'نا', 'كم', 'كيف'
])

ALL_STOPWORDS = STOPWORDS | ARABIC_STOPWORDS


def clean_keyword(kw: str) -> str:
    """Clean a keyword by removing brackets, parentheses, and extra whitespace."""
    # Remove brackets and parentheses
    kw = re.sub(r'[\[\]\(\)\{\}]', '', kw)
    # Remove leading/trailing punctuation
    kw = re.sub(r'^[^\w\u0600-\u06FF]+|[^\w\u0600-\u06FF]+$', '', kw)
    # Normalize whitespace
    kw = ' '.join(kw.split())
    return kw.strip()


def is_valid_keyword(kw: str, min_length: int = 3) -> bool:
    """Check if a keyword is valid (not stopword, not too short, not junk)."""
    kw_lower = kw.lower()
    
    # Too short
    if len(kw) < min_length:
        return False
    
    # All stopwords
    words = kw_lower.split()
    if all(w in ALL_STOPWORDS for w in words):
        return False
    
    # Contains only numbers or special chars
    if re.match(r'^[\d\s\-\.\,]+$', kw):
        return False
    
    # Looks like navigation/UI text
    ui_patterns = [
        r'^\d+\s*(items?|products?|results?)',
        r'^(skip|back|next|prev|home|menu)',
        r'(copyright|reserved|privacy|terms)',
        r'^\d+\s*$',  # Just numbers
        r'^[\W_]+$',  # Just punctuation
    ]
    for pattern in ui_patterns:
        if re.search(pattern, kw_lower):
            return False
    
    return True


def calculate_keyword_density(keywords: List[Dict], total_words: int) -> List[Dict]:
    """Calculate keyword density percentage."""
    for kw in keywords:
        word_count = len(kw['kw'].split())
        frequency = kw['count']
        # Density = (keyword frequency × word count) / total words × 100
        density = (frequency * word_count / total_words * 100) if total_words > 0 else 0
        kw['density'] = round(density, 2)
    return keywords


def classify_keywords(keywords: List[Dict]) -> Dict[str, List[Dict]]:
    """Classify keywords into primary, secondary, and long-tail."""
    if not keywords:
        return {'primary': [], 'secondary': [], 'long_tail': []}
    
    # Sort by count
    sorted_kws = sorted(keywords, key=lambda x: x['count'], reverse=True)
    
    # Primary: top 20% by frequency
    primary_count = max(3, len(sorted_kws) // 5)
    primary = sorted_kws[:primary_count]
    
    # Secondary: next 30%
    secondary_count = max(5, len(sorted_kws) * 3 // 10)
    secondary = sorted_kws[primary_count:primary_count + secondary_count]
    
    # Long-tail: rest
    long_tail = sorted_kws[primary_count + secondary_count:]
    
    return {
        'primary': primary,
        'secondary': secondary,
        'long_tail': long_tail
    }


def cluster_by_topic(keywords: List[Dict]) -> Dict[str, List[Dict]]:
    """Group keywords by semantic topic."""
    # Simple topic clustering based on common words
    clusters = defaultdict(list)
    
    for kw_obj in keywords:
        kw = kw_obj['kw'].lower()
        
        # SEO-related
        if any(term in kw for term in ['seo', 'search', 'ranking', 'optimization', 'محرك', 'بحث']):
            clusters['SEO & Search'].append(kw_obj)
        # E-commerce
        elif any(term in kw for term in ['shop', 'store', 'product', 'price', 'buy', 'متجر', 'منتج']):
            clusters['E-commerce'].append(kw_obj)
        # Content/Blog
        elif any(term in kw for term in ['blog', 'article', 'post', 'content', 'مقال', 'محتوى']):
            clusters['Content'].append(kw_obj)
        # Location
        elif any(term in kw for term in ['city', 'location', 'address', 'مدينة', 'موقع', 'عنوان']):
            clusters['Location'].append(kw_obj)
        # Brand/Product names
        elif kw_obj['count'] >= 5 and len(kw.split()) <= 2:
            clusters['Brand/Product'].append(kw_obj)
        # General
        else:
            clusters['General'].append(kw_obj)
    
    # Remove empty clusters
    return {k: v for k, v in clusters.items() if v}


def calculate_coverage_score(keywords: List[Dict], expected_keywords: List[str]) -> Dict:
    """Calculate topic coverage score based on expected keywords."""
    found = set(kw['kw'].lower() for kw in keywords)
    expected = set(k.lower() for k in expected_keywords)
    
    matched = found & expected
    missing = expected - found
    
    coverage = (len(matched) / len(expected) * 100) if expected else 0
    
    return {
        'score': round(coverage, 1),
        'matched': list(matched),
        'missing': list(missing),
        'total_expected': len(expected),
        'total_found': len(matched)
    }


def analyze_keywords(keywords: List[Dict], total_words: int = 0, 
                     expected_keywords: List[str] = None) -> Dict:
    """
    Comprehensive keyword analysis with classification, clustering, and metrics.
    
    Args:
        keywords: List of keyword dicts with 'kw' and 'count'
        total_words: Total word count on page (for density calculation)
        expected_keywords: Expected keywords for coverage analysis
    
    Returns:
        Complete analytics report
    """
    # Clean and filter keywords
    cleaned = []
    for kw_obj in keywords:
        kw = clean_keyword(kw_obj['kw'])
        if is_valid_keyword(kw):
            cleaned.append({**kw_obj, 'kw': kw})
    
    # Remove duplicates (case-insensitive)
    seen = {}
    unique = []
    for kw_obj in cleaned:
        kw_lower = kw_obj['kw'].lower()
        if kw_lower not in seen:
            seen[kw_lower] = kw_obj
            unique.append(kw_obj)
        else:
            # Merge counts if duplicate
            seen[kw_lower]['count'] += kw_obj['count']
    
    # Re-sort by count
    unique = sorted(unique, key=lambda x: x['count'], reverse=True)
    
    # Calculate density
    if total_words > 0:
        unique = calculate_keyword_density(unique, total_words)
    
    # Classify keywords
    classification = classify_keywords(unique)
    
    # Cluster by topic
    clusters = cluster_by_topic(unique)
    
    # Calculate coverage if expected keywords provided
    coverage = None
    if expected_keywords:
        coverage = calculate_coverage_score(unique, expected_keywords)
    
    # Calculate metrics
    total_keywords = len(unique)
    avg_frequency = sum(k['count'] for k in unique) / total_keywords if total_keywords > 0 else 0
    
    # Top keywords (top 10)
    top_keywords = unique[:10]
    
    return {
        'summary': {
            'total_keywords': total_keywords,
            'total_words': total_words,
            'avg_frequency': round(avg_frequency, 1),
            'primary_keywords': len(classification['primary']),
            'secondary_keywords': len(classification['secondary']),
            'long_tail_keywords': len(classification['long_tail'])
        },
        'top_keywords': top_keywords,
        'classification': classification,
        'clusters': clusters,
        'coverage': coverage,
        'all_keywords': unique
    }


def format_analytics_report(analytics: Dict) -> str:
    """Format analytics as a readable text report."""
    lines = []
    lines.append("=" * 80)
    lines.append("KEYWORD ANALYTICS REPORT")
    lines.append("=" * 80)
    
    # Summary
    summary = analytics['summary']
    lines.append("\n📊 SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total Keywords Found: {summary['total_keywords']}")
    lines.append(f"Total Words on Page: {summary['total_words']}")
    lines.append(f"Average Keyword Frequency: {summary['avg_frequency']}")
    lines.append(f"Primary Keywords: {summary['primary_keywords']}")
    lines.append(f"Secondary Keywords: {summary['secondary_keywords']}")
    lines.append(f"Long-tail Keywords: {summary['long_tail_keywords']}")
    
    # Top Keywords
    lines.append("\n🔝 TOP KEYWORDS")
    lines.append("-" * 80)
    lines.append(f"{'Keyword':<40} {'Frequency':<12} {'Density':<10}")
    lines.append("-" * 80)
    for kw in analytics['top_keywords']:
        density = f"{kw.get('density', 0):.2f}%" if 'density' in kw else 'N/A'
        lines.append(f"{kw['kw']:<40} {kw['count']:<12} {density:<10}")
    
    # Classification
    lines.append("\n📋 KEYWORD CLASSIFICATION")
    lines.append("-" * 80)
    
    classification = analytics['classification']
    
    lines.append("\n1️⃣ PRIMARY KEYWORDS (High Priority)")
    for kw in classification['primary'][:5]:
        lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    lines.append("\n2️⃣ SECONDARY KEYWORDS (Medium Priority)")
    for kw in classification['secondary'][:5]:
        lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    lines.append("\n3️⃣ LONG-TAIL KEYWORDS (Low Priority)")
    for kw in classification['long_tail'][:5]:
        lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    # Topic Clusters
    lines.append("\n🎯 TOPIC CLUSTERS")
    lines.append("-" * 80)
    for topic, kws in analytics['clusters'].items():
        lines.append(f"\n{topic} ({len(kws)} keywords)")
        for kw in kws[:3]:
            lines.append(f"  • {kw['kw']} ({kw['count']})")
    
    # Coverage
    if analytics.get('coverage'):
        coverage = analytics['coverage']
        lines.append("\n📈 TOPIC COVERAGE")
        lines.append("-" * 80)
        lines.append(f"Coverage Score: {coverage['score']}%")
        lines.append(f"Matched Keywords: {coverage['total_found']}/{coverage['total_expected']}")
        if coverage['missing']:
            lines.append("\nMissing Keywords:")
            for kw in coverage['missing'][:5]:
                lines.append(f"  ❌ {kw}")
    
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)
