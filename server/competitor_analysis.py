"""Competitor Detection and Analysis."""
import re
from urllib.parse import urlparse
from typing import List, Dict, Set
from collections import defaultdict

def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www.
        domain = re.sub(r'^www\.', '', domain)
        return domain.lower()
    except:
        return ''

def is_valid_competitor(url: str, source_domain: str) -> bool:
    """Check if URL is a valid competitor (not internal, not social, not CDN)."""
    domain = extract_domain(url)
    
    if not domain:
        return False
    
    # Same domain = not competitor
    if domain == source_domain or source_domain in domain:
        return False
    
    # Filter out common non-competitor domains
    excluded_patterns = [
        # Social media
        r'facebook\.com', r'twitter\.com', r'instagram\.com', r'linkedin\.com',
        r'youtube\.com', r'tiktok\.com', r'pinterest\.com', r'snapchat\.com',
        # CDNs and services
        r'cloudflare\.com', r'amazonaws\.com', r'googleusercontent\.com',
        r'cloudfront\.net', r'akamai\.net', r'fastly\.net',
        # Analytics and ads
        r'google-analytics\.com', r'googletagmanager\.com', r'doubleclick\.net',
        r'facebook\.net', r'googlesyndication\.com', r'googleadservices\.com',
        # Payment and services
        r'paypal\.com', r'stripe\.com', r'shopify\.com',
        # Generic services
        r'google\.com', r'bing\.com', r'yahoo\.com', r'wikipedia\.org',
        r'w3\.org', r'schema\.org', r'creativecommons\.org',
        # Fonts and assets
        r'fonts\.googleapis\.com', r'fonts\.gstatic\.com',
        # Maps
        r'maps\.google\.com', r'openstreetmap\.org'
    ]
    
    for pattern in excluded_patterns:
        if re.search(pattern, domain):
            return False
    
    return True

def detect_competitors(pages: List[Dict], source_url: str, min_mentions: int = 1) -> List[Dict]:
    """
    Detect competitor domains from crawled pages with contextual snippets.
    
    Args:
        pages: List of page objects with 'links' and 'text' fields
        source_url: Source domain URL
        min_mentions: Minimum number of mentions to be considered competitor
    
    Returns:
        List of competitor dicts with domain, count, sample URLs, and context snippets
    """
    source_domain = extract_domain(source_url)
    
    # Count competitor mentions
    competitor_counts = defaultdict(int)
    competitor_urls = defaultdict(set)
    competitor_contexts = defaultdict(list)
    
    for page in pages:
        links = page.get('links', [])
        page_text = page.get('text', '')
        
        for link in links:
            if is_valid_competitor(link, source_domain):
                domain = extract_domain(link)
                competitor_counts[domain] += 1
                competitor_urls[domain].add(link)
                
                # Extract a small snippet of context if possible
                # In a real scenario, we'd use beautifulsoup to find parent elements
                # Here we do a simple text-based heuristic search
                if page_text and domain in page_text:
                    try:
                        idx = page_text.find(domain)
                        start = max(0, idx - 100)
                        end = min(len(page_text), idx + 100)
                        context = page_text[start:end].strip().replace('\n', ' ')
                        if context:
                            competitor_contexts[domain].append(context)
                    except:
                        pass
    
    # Filter by minimum mentions
    competitors = []
    for domain, count in competitor_counts.items():
        if count >= min_mentions:
            # Deduplicate and limit contexts
            unique_contexts = list(set(competitor_contexts[domain]))[:5]
            competitors.append({
                'domain': domain,
                'mentions': count,
                'sample_urls': list(competitor_urls[domain])[:3],
                'contexts': unique_contexts
            })
    
    # Sort by mentions (descending)
    competitors.sort(key=lambda x: x['mentions'], reverse=True)
    
    return competitors

def analyze_competitor_keywords(competitor_domain: str, pages: List[Dict]) -> Dict:
    """
    Analyze what keywords appear near competitor links.
    
    This helps understand the context in which competitors are mentioned.
    """
    # Find pages that mention this competitor
    relevant_pages = []
    for page in pages:
        links = page.get('links', [])
        for link in links:
            if competitor_domain in link:
                relevant_pages.append(page)
                break
    
    if not relevant_pages:
        return {'keywords': [], 'context': []}
    
    # Extract text around competitor mentions
    # This is a simplified version - could be enhanced with NLP
    contexts = []
    for page in relevant_pages:
        title = page.get('title', '')
        if title:
            contexts.append(title)
    
    return {
        'pages_mentioned': len(relevant_pages),
        'contexts': contexts[:5]
    }

def format_competitor_report(competitors: List[Dict], source_url: str) -> str:
    """Format competitor analysis as readable report."""
    lines = []
    lines.append("=" * 80)
    lines.append("COMPETITOR ANALYSIS REPORT")
    lines.append("=" * 80)
    
    source_domain = extract_domain(source_url)
    lines.append(f"\n🎯 Source Domain: {source_domain}")
    lines.append(f"📊 Competitors Found: {len(competitors)}")
    
    if not competitors:
        lines.append("\n❌ No competitors detected")
        lines.append("\nPossible reasons:")
        lines.append("  • Page has no external links")
        lines.append("  • All external links are to social media/CDNs")
        lines.append("  • Minimum mention threshold not met")
        return "\n".join(lines)
    
    lines.append("\n🏆 TOP COMPETITORS")
    lines.append("-" * 80)
    lines.append(f"{'Domain':<40} {'Mentions':<10} {'Sample URL'}")
    lines.append("-" * 80)
    
    for comp in competitors[:10]:
        sample = comp['sample_urls'][0] if comp['sample_urls'] else 'N/A'
        if len(sample) > 35:
            sample = sample[:32] + '...'
        lines.append(f"{comp['domain']:<40} {comp['mentions']:<10} {sample}")
    
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)

def get_competitor_summary(competitors: List[Dict]) -> Dict:
    """Get summary statistics for competitors."""
    if not competitors:
        return {
            'total': 0,
            'avg_mentions': 0,
            'top_competitor': None
        }
    
    total = len(competitors)
    avg_mentions = sum(c['mentions'] for c in competitors) / total
    top_competitor = competitors[0] if competitors else None
    
    return {
        'total': total,
        'avg_mentions': round(avg_mentions, 1),
        'top_competitor': top_competitor['domain'] if top_competitor else None,
        'top_mentions': top_competitor['mentions'] if top_competitor else 0
    }
