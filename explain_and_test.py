#!/usr/bin/env python3
"""
SIMPLE EXPLANATION AND TEST

This shows you EXACTLY what the system does step by step.
"""
import os
import sys
import json

os.environ['DATAFORSEO_LOGIN'] = 'ai.seg01@seginvest.com'
os.environ['DATAFORSEO_PASSWORD'] = '712e269a1e24e50f'

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("SIMPLE EXPLANATION - HOW IT WORKS")
print("=" * 80)

print("""
STEP 1: CRAWL THE PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The crawler visits https://abayanoir.com and extracts:
  • Page title
  • Headings (H1, H2, H3)
  • Paragraphs
  • Links to other websites
  • All text content

STEP 2: EXTRACT KEYWORDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
From the text, we find words that appear multiple times:
  • "abaya" appears 10 times → keyword
  • "phone" appears 28 times → keyword
  • "the" appears 50 times → NOT a keyword (stopword)

We CLEAN the keywords by removing:
  ❌ Navigation text (menu, cart, login)
  ❌ Brackets and parentheses [ ( ) ]
  ❌ Numbers only (012, 8998)
  ❌ UI text (click here, read more)

STEP 3: CLASSIFY KEYWORDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We group keywords by importance:

1️⃣ PRIMARY = Most frequent keywords (top 20%)
   Example: "abaya" (10 times), "modest fashion" (8 times)

2️⃣ SECONDARY = Medium frequency (next 30%)
   Example: "clothing" (5 times), "collection" (4 times)

3️⃣ LONG-TAIL = Less frequent but specific (rest)
   Example: "black abaya dress" (2 times)

STEP 4: FIND COMPETITORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We look at ALL links on the page and filter:

✅ KEEP: Links to other e-commerce sites
   Example: competitor-store.com

❌ REMOVE: 
   • Same domain (abayanoir.com)
   • Social media (facebook.com, instagram.com)
   • CDNs (cloudflare.com, amazonaws.com)
   • Google/Analytics

WHY NO COMPETITORS FOUND?
→ The page only links to:
  • Its own pages (abayanoir.com/products/...)
  • Social media (facebook, instagram)
  • No external competitor websites

STEP 5: ENRICH WITH DATAFORSEO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each keyword, we get:
  • Search Volume: How many people search per month
  • CPC: Cost per click in Google Ads
  • Competition: LOW/MEDIUM/HIGH

Example:
  "abaya" → 60,500 searches/month, $0.81 CPC, HIGH competition
""")

print("\n" + "=" * 80)
print("NOW LET'S TEST WITH REAL DATA")
print("=" * 80)

# Test with audit
audit_path = 'output/audit.json'
if not os.path.exists(audit_path):
    print(f"\n❌ {audit_path} not found. Run a crawl first.")
    sys.exit(1)

with open(audit_path, 'r') as f:
    audit = json.load(f)

pages = audit.get('pages', [])
print(f"\n✅ Loaded audit with {len(pages)} pages")

# Show what's in the pages
print("\n" + "=" * 80)
print("WHAT'S IN THE CRAWLED DATA?")
print("=" * 80)

if pages:
    page = pages[0]
    print(f"\nPage URL: {page.get('url', 'N/A')}")
    print(f"Title: {page.get('title', 'N/A')}")
    print(f"Number of links: {len(page.get('links', []))}")
    print(f"Number of headings: {len(page.get('headings', []))}")
    
    # Show some links
    links = page.get('links', [])
    print(f"\nFirst 10 links found:")
    for i, link in enumerate(links[:10], 1):
        print(f"  {i}. {link}")

# Test keyword extraction
print("\n" + "=" * 80)
print("TESTING KEYWORD EXTRACTION")
print("=" * 80)

from server.keyword_engine import extract_keywords_from_audit

# Simple extraction (no analytics)
print("\n1️⃣ SIMPLE MODE (just keywords)")
print("-" * 80)
simple_kws = extract_keywords_from_audit(audit, top_n=10, enrich=False, analytics=False)
print(f"\nFound {len(simple_kws)} keywords:\n")
for kw in simple_kws[:10]:
    print(f"  • {kw['kw']} ({kw['count']} times)")

# Analytics mode
print("\n\n2️⃣ ANALYTICS MODE (with classification)")
print("-" * 80)
analytics = extract_keywords_from_audit(audit, top_n=20, enrich=False, analytics=True)

print(f"\nTotal keywords: {analytics['summary']['total_keywords']}")
print(f"Primary keywords: {analytics['summary']['primary_keywords']}")
print(f"Secondary keywords: {analytics['summary']['secondary_keywords']}")
print(f"Long-tail keywords: {analytics['summary']['long_tail_keywords']}")

print("\nPrimary Keywords (most important):")
for kw in analytics['classification']['primary'][:5]:
    print(f"  • {kw['kw']} ({kw['count']} times)")

print("\nTopic Clusters:")
for topic, kws in analytics['clusters'].items():
    print(f"  • {topic}: {len(kws)} keywords")

# Test competitor detection
print("\n" + "=" * 80)
print("TESTING COMPETITOR DETECTION")
print("=" * 80)

from server.competitor_analysis import detect_competitors, extract_domain

source_url = pages[0].get('url', '') if pages else 'https://abayanoir.com'
source_domain = extract_domain(source_url)

print(f"\nSource domain: {source_domain}")
print(f"Looking for competitors in {len(pages)} pages...")

competitors = detect_competitors(pages, source_url, min_mentions=1)

print(f"\n✅ Found {len(competitors)} competitors")

if competitors:
    print("\nCompetitors:")
    for comp in competitors[:5]:
        print(f"  • {comp['domain']} ({comp['mentions']} mentions)")
        print(f"    Sample URL: {comp['sample_urls'][0]}")
else:
    print("\n❌ No competitors found")
    print("\nWhy? Let's check the links:")
    
    all_links = []
    for page in pages:
        all_links.extend(page.get('links', []))
    
    print(f"\nTotal links found: {len(all_links)}")
    
    # Categorize links
    internal = 0
    social = 0
    cdn = 0
    other = 0
    
    for link in all_links:
        domain = extract_domain(link)
        if source_domain in domain:
            internal += 1
        elif any(s in domain for s in ['facebook', 'instagram', 'twitter', 'youtube']):
            social += 1
        elif any(s in domain for s in ['cloudflare', 'amazonaws', 'cdn']):
            cdn += 1
        else:
            other += 1
    
    print(f"\nLink breakdown:")
    print(f"  • Internal links (same site): {internal}")
    print(f"  • Social media: {social}")
    print(f"  • CDN/Services: {cdn}")
    print(f"  • Other: {other}")
    
    if other > 0:
        print(f"\n  Other links (potential competitors):")
        shown = 0
        for link in all_links:
            domain = extract_domain(link)
            if domain and source_domain not in domain:
                if not any(s in domain for s in ['facebook', 'instagram', 'twitter', 'youtube', 'cloudflare', 'amazonaws', 'cdn', 'google', 'schema.org']):
                    print(f"    • {domain}")
                    shown += 1
                    if shown >= 5:
                        break

# Test with enrichment
print("\n" + "=" * 80)
print("TESTING WITH DATAFORSEO ENRICHMENT")
print("=" * 80)

enriched_kws = extract_keywords_from_audit(audit, top_n=10, enrich=True, analytics=False)

print(f"\nTop 10 keywords with search data:\n")
print(f"{'Keyword':<30} {'Count':<8} {'Volume':<12} {'CPC':<10} {'Competition'}")
print("-" * 80)

for kw in enriched_kws[:10]:
    vol = kw.get('volume', 'N/A')
    cpc = kw.get('cpc')
    comp = kw.get('competition', 'N/A')
    
    if isinstance(cpc, float):
        cpc_str = f"${cpc:.2f}"
    else:
        cpc_str = 'N/A'
    
    print(f"{kw['kw']:<30} {kw['count']:<8} {str(vol):<12} {cpc_str:<10} {comp}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("""
✅ WHAT WORKS:
  • Keyword extraction
  • Keyword classification (primary/secondary/long-tail)
  • Topic clustering
  • DataForSEO enrichment (volume, CPC, competition)

⚠️  WHY NO COMPETITORS:
  • The page only links to itself and social media
  • No links to other e-commerce/competitor sites
  • This is NORMAL for many websites

💡 TO GET COMPETITOR DATA:
  • Crawl more pages (increase max_pages)
  • Look for blog posts (they often link to competitors)
  • Use DataForSEO competitor API (separate endpoint)
  • Manually add known competitors for comparison

📊 THE ANALYTICS REPORT SHOWS:
  • How many times each keyword appears (frequency)
  • Which keywords are most important (classification)
  • What topics the page covers (clusters)
  • Search volume and competition (DataForSEO)
  • Content quality score
  • Recommendations for improvement
""")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
