#!/usr/bin/env python3
"""Test comprehensive keyword analytics."""
import os
import sys
import json

# Set credentials
os.environ['DATAFORSEO_LOGIN'] = 'ai.seg01@seginvest.com'
os.environ['DATAFORSEO_PASSWORD'] = '712e269a1e24e50f'

sys.path.insert(0, os.path.dirname(__file__))

from server.keyword_engine import extract_keywords_from_audit
from server.keyword_analytics import format_analytics_report

def test_analytics():
    """Test full analytics with existing audit."""
    print("=" * 80)
    print("COMPREHENSIVE KEYWORD ANALYTICS TEST")
    print("=" * 80)
    
    audit_path = 'output/audit.json'
    if not os.path.exists(audit_path):
        print(f"❌ {audit_path} not found")
        return
    
    with open(audit_path, 'r') as f:
        audit = json.load(f)
    
    # Define expected keywords for coverage analysis
    expected_keywords = [
        'seo', 'search engine optimization', 'محرك', 'بحث',
        'local seo', 'ai seo', 'youtube seo', 'aso',
        'ranking', 'keywords', 'backlinks', 'content'
    ]
    
    print("\n🔍 Extracting keywords with full analytics...")
    print(f"📋 Expected keywords: {len(expected_keywords)}")
    
    # Get full analytics
    analytics = extract_keywords_from_audit(
        audit, 
        top_n=50, 
        enrich=True, 
        analytics=True,
        expected_keywords=expected_keywords
    )
    
    # Print formatted report
    print("\n" + format_analytics_report(analytics))
    
    # Print JSON structure
    print("\n" + "=" * 80)
    print("JSON STRUCTURE (for API response)")
    print("=" * 80)
    
    # Show structure without full data
    structure = {
        'summary': analytics['summary'],
        'top_keywords': analytics['top_keywords'][:3],
        'classification': {
            'primary': f"{len(analytics['classification']['primary'])} keywords",
            'secondary': f"{len(analytics['classification']['secondary'])} keywords",
            'long_tail': f"{len(analytics['classification']['long_tail'])} keywords"
        },
        'clusters': {k: f"{len(v)} keywords" for k, v in analytics['clusters'].items()},
        'coverage': analytics.get('coverage')
    }
    
    print(json.dumps(structure, indent=2, ensure_ascii=False))
    
    # Show example API response
    print("\n" + "=" * 80)
    print("EXAMPLE API RESPONSE")
    print("=" * 80)
    
    api_response = {
        'ok': True,
        'analytics': {
            'summary': analytics['summary'],
            'top_keywords': analytics['top_keywords'][:5],
            'classification': {
                'primary': analytics['classification']['primary'][:3],
                'secondary': analytics['classification']['secondary'][:3],
                'long_tail': analytics['classification']['long_tail'][:3]
            },
            'clusters': {k: v[:2] for k, v in analytics['clusters'].items()},
            'coverage': analytics.get('coverage')
        }
    }
    
    print(json.dumps(api_response, indent=2, ensure_ascii=False))

def test_simple_vs_analytics():
    """Compare simple extraction vs analytics."""
    print("\n" + "=" * 80)
    print("COMPARISON: Simple vs Analytics")
    print("=" * 80)
    
    audit_path = 'output/audit.json'
    if not os.path.exists(audit_path):
        return
    
    with open(audit_path, 'r') as f:
        audit = json.load(f)
    
    # Simple extraction
    print("\n1️⃣ SIMPLE EXTRACTION (analytics=False)")
    print("-" * 80)
    simple = extract_keywords_from_audit(audit, top_n=10, enrich=False, analytics=False)
    print(f"{'Keyword':<30} {'Count':<10}")
    print("-" * 80)
    for kw in simple[:5]:
        print(f"{kw['kw']:<30} {kw['count']:<10}")
    
    # Analytics extraction
    print("\n2️⃣ ANALYTICS EXTRACTION (analytics=True)")
    print("-" * 80)
    analytics = extract_keywords_from_audit(audit, top_n=10, enrich=False, analytics=True)
    print(f"Total Keywords: {analytics['summary']['total_keywords']}")
    print(f"Primary: {analytics['summary']['primary_keywords']}")
    print(f"Secondary: {analytics['summary']['secondary_keywords']}")
    print(f"Long-tail: {analytics['summary']['long_tail_keywords']}")
    print(f"\nTop 5 Keywords:")
    for kw in analytics['top_keywords'][:5]:
        density = kw.get('density', 0)
        print(f"  • {kw['kw']} (count: {kw['count']}, density: {density:.2f}%)")

if __name__ == '__main__':
    test_analytics()
    test_simple_vs_analytics()
    
    print("\n" + "=" * 80)
    print("✅ ANALYTICS TEST COMPLETED!")
    print("=" * 80)
    print("\n💡 API Usage:")
    print("  Simple:    POST /api/keywords?analytics=false")
    print("  Analytics: POST /api/keywords?analytics=true")
    print("\n📊 Analytics includes:")
    print("  ✅ Keyword classification (primary/secondary/long-tail)")
    print("  ✅ Topic clustering (SEO, E-commerce, Content, etc.)")
    print("  ✅ Keyword density calculation")
    print("  ✅ Coverage score (vs expected keywords)")
    print("  ✅ Clean, filtered keywords (no navigation/junk)")
