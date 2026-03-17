"""Lightweight Search Intelligence helpers.

Provides keyword research and competitor scraping using free tools in this repo:
- uses `src.crawler` to fetch pages
- uses `server.keyword_engine` for keyword extraction

These are intentionally minimal and safe fallbacks when external APIs/keys
are not available.
"""
from typing import List, Dict
import os
try:
    from googleapiclient.discovery import build
except Exception:
    build = None

from server import keyword_engine


def keywords_from_url(url: str, max_pages: int = 1, top_n: int = 40, enrich: bool = True):
    try:
        from src import crawler
    except Exception:
        raise RuntimeError('crawler not available')
    pages = crawler.crawl_seed(url, max_pages=max_pages)
    audit_obj = {'pages': pages}
    kws = keyword_engine.extract_keywords_from_audit(audit_obj, top_n=top_n, enrich=enrich)
    return { 'keywords': kws, 'pages': [{'url': p.get('url'), 'title': p.get('title')} for p in pages] }


def competitor_links(url: str, max_pages: int = 3):
    try:
        from src import crawler
    except Exception:
        raise RuntimeError('crawler not available')
    pages = crawler.crawl_seed(url, max_pages=max_pages)
    external = {}
    for p in pages:
        for l in p.get('links', []):
            if not l.startswith(url):
                external[l] = external.get(l, 0) + 1
    items = sorted(external.items(), key=lambda x: x[1], reverse=True)
    return { 'competitors': [{'url': u, 'count': c} for u,c in items] }


def gsc_query(site_url: str, start_date: str, end_date: str, row_limit: int = 2500):
    """Try to call Google Search Console API if `googleapiclient` and credentials are available.

    Returns {'enabled': False, 'reason': ...} when not available.
    """
    if build is None:
        return { 'enabled': False, 'reason': 'googleapiclient not installed' }
    # Credentials are expected in environment via GOOGLE_APPLICATION_CREDENTIALS JSON path
    try:
        service = build('searchconsole', 'v1')
        body = {'startDate': start_date, 'endDate': end_date, 'dimensions': ['query'], 'rowLimit': row_limit}
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        return { 'enabled': True, 'result': resp }
    except Exception as e:
        return { 'enabled': False, 'reason': str(e) }
