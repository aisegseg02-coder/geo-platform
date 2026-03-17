#!/usr/bin/env python3
"""Test keyword extraction with DataForSEO enrichment."""
import os
import sys
import json

# Set credentials
os.environ['DATAFORSEO_LOGIN'] = 'ai.seg01@seginvest.com'
os.environ['DATAFORSEO_PASSWORD'] = '712e269a1e24e50f'

sys.path.insert(0, os.path.dirname(__file__))

from server.keyword_engine import extract_keywords_from_audit
from server.search_intel import keywords_from_url

def test_with_audit():
    """Test with existing audit.json"""
    print("=" * 60)
    print("TEST 1: Extract keywords from existing audit")
    print("=" * 60)
    
    audit_path = 'output/audit.json'
    if not os.path.exists(audit_path):
        print(f"❌ {audit_path} not found")
        return
    
    with open(audit_path, 'r') as f:
        audit = json.load(f)
    
    print("\n Extracting keywords with DataForSEO enrichment...")
    keywords = extract_keywords_from_audit(audit, top_n=15, enrich=True)
    
    print(f"\n Found {len(keywords)} keywords:\n")
    print(f"{'Keyword':<30} {'Count':<8} {'Volume':<12} {'CPC':<8} {'Competition'}")
    print("-" * 80)
    
    for kw in keywords:
        vol = kw.get('volume', 'N/A')
        cpc = kw.get('cpc')
        comp = kw.get('competition', 'N/A')
        if isinstance(cpc, float):
            cpc = f"${cpc:.2f}"
        elif cpc is None:
            cpc = 'N/A'
        print(f"{kw['kw']:<30} {kw['count']:<8} {str(vol):<12} {str(cpc):<8} {comp}")

def test_with_url():
    """Test with live URL crawl"""
    print("\n" + "=" * 60)
    print("TEST 2: Extract keywords from live URL")
    print("=" * 60)
    
    test_url = "https://abayanoir.com"
    print(f"\n🌐 Crawling {test_url}...")
    
    try:
        result = keywords_from_url(test_url, max_pages=2, top_n=15, enrich=True)
        keywords = result['keywords']
        
        print(f"\n✅ Found {len(keywords)} keywords:\n")
        print(f"{'Keyword':<30} {'Count':<8} {'Volume':<12} {'CPC':<8} {'Competition'}")
        print("-" * 80)
        
        for kw in keywords:
            vol = kw.get('volume', 'N/A')
            cpc = kw.get('cpc')
            comp = kw.get('competition', 'N/A')
            if isinstance(cpc, float):
                cpc = f"${cpc:.2f}"
            elif cpc is None:
                cpc = 'N/A'
            print(f"{kw['kw']:<30} {kw['count']:<8} {str(vol):<12} {str(cpc):<8} {comp}")
    except Exception as e:
        print(f" Error: {e}")

if __name__ == '__main__':
    test_with_audit()
    test_with_url()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("  1. Keywords now include volume, CPC, and competition data")
    print("  2. Use enrich=True (default) to get DataForSEO data")
    print("  3. Use enrich=False for faster extraction without API calls")
    print("  4. Free tier: 100 requests/day")
