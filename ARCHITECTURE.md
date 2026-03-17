# Keyword Extraction Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                 │
│  POST /api/search/keywords {"url": "https://example.com"}           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CRAWLER (Scrapy + Playwright)                   │
│  • Fetches pages from URL                                            │
│  • Extracts: title, headings, paragraphs, links, HTML               │
│  • Returns: List of page objects                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KEYWORD ENGINE (keyword_engine.py)                │
│                                                                       │
│  Step 1: Clean HTML                                                  │
│  ├─ Strip <script> and <style> tags                                 │
│  ├─ Remove HTML tags                                                 │
│  └─ Decode HTML entities                                             │
│                                                                       │
│  Step 2: Extract Text                                                │
│  ├─ Title (weighted 2x)                                              │
│  ├─ Headings (H1, H2, H3)                                            │
│  ├─ Paragraphs                                                       │
│  └─ Cleaned HTML content                                             │
│                                                                       │
│  Step 3: Keyword Extraction                                          │
│  ├─ Option A: spaCy (if available)                                  │
│  │   ├─ Noun chunks                                                  │
│  │   └─ Named entities                                               │
│  └─ Option B: Regex fallback                                         │
│      ├─ Single words (3+ chars)                                      │
│      └─ Phrases (2-3 words, weighted 2x)                             │
│                                                                       │
│  Step 4: Filter & Count                                              │
│  ├─ Remove stopwords (the, and, shop, menu, etc.)                   │
│  ├─ Count frequency                                                  │
│  └─ Sort by count (descending)                                       │
│                                                                       │
│  Output: [{"kw": "abaya", "count": 10}, ...]                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DATAFORSEO CLIENT (dataforseo_client.py)                │
│                                                                       │
│  IF enrich=True:                                                     │
│  ├─ Send keywords to DataForSEO API                                 │
│  ├─ Endpoint: /v3/keywords_data/google_ads/search_volume/live       │
│  ├─ Auth: Basic (login:password)                                     │
│  └─ Receive: volume, cpc, competition                                │
│                                                                       │
│  IF enrich=False:                                                    │
│  └─ Skip API call (faster, no quota usage)                           │
│                                                                       │
│  Output: [{"kw": "abaya", "count": 10, "volume": 60500,             │
│            "cpc": 0.81, "competition": "HIGH"}, ...]                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API RESPONSE                                 │
│  {                                                                    │
│    "ok": true,                                                        │
│    "keywords": [                                                      │
│      {                                                                │
│        "kw": "abaya",                                                 │
│        "count": 10,                                                   │
│        "volume": 60500,                                               │
│        "cpc": 0.81,                                                   │
│        "competition": "HIGH"                                          │
│      }                                                                │
│    ]                                                                  │
│  }                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Input
```
URL: https://abayanoir.com
```

### Crawler Output
```json
{
  "pages": [
    {
      "url": "https://abayanoir.com",
      "title": "Abaya Noir – Your Basics & More",
      "headings": [
        {"tag": "h1", "text": ""},
        {"tag": "h2", "text": "New Arrivals"},
        {"tag": "h2", "text": "Shop by Category"}
      ],
      "paragraphs": [
        "Discover our collection of modest fashion...",
        "Premium quality abayas for every occasion..."
      ],
      "html": "<html>...</html>"
    }
  ]
}
```

### Keyword Engine Output (before enrichment)
```json
[
  {"kw": "abaya", "count": 10},
  {"kw": "modest fashion", "count": 8},
  {"kw": "new arrivals", "count": 6},
  {"kw": "collection", "count": 5}
]
```

### DataForSEO Enrichment
```
Request to DataForSEO:
POST https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live
{
  "keywords": ["abaya", "modest fashion", "new arrivals", "collection"],
  "location_code": 2840,
  "language_code": "en"
}

Response:
{
  "tasks": [{
    "result": [
      {"keyword": "abaya", "search_volume": 60500, "cpc": 0.81, "competition": "HIGH"},
      {"keyword": "modest fashion", "search_volume": 2900, "cpc": 1.03, "competition": "MEDIUM"},
      ...
    ]
  }]
}
```

### Final Output (enriched)
```json
[
  {
    "kw": "abaya",
    "count": 10,
    "volume": 60500,
    "cpc": 0.81,
    "competition": "HIGH"
  },
  {
    "kw": "modest fashion",
    "count": 8,
    "volume": 2900,
    "cpc": 1.03,
    "competition": "MEDIUM"
  }
]
```

## Performance Characteristics

| Operation | Time | API Calls | Notes |
|-----------|------|-----------|-------|
| Crawl (1 page) | ~2s | 0 | Playwright rendering |
| Extract keywords | ~0.1s | 0 | Local processing |
| Enrich (40 kws) | ~1s | 1 | DataForSEO API |
| **Total (enrich=true)** | **~3s** | **1** | Full pipeline |
| **Total (enrich=false)** | **~2s** | **0** | No enrichment |

## Error Handling

```python
# Graceful degradation at each step

1. Crawler fails → Return error to user
2. spaCy not available → Use regex fallback
3. DataForSEO fails → Return keywords without volume/CPC
4. No keywords found → Return empty array
```

## Configuration

### Environment Variables
```bash
DATAFORSEO_LOGIN=ai.seg01@seginvest.com
DATAFORSEO_PASSWORD=712e269a1e24e50f
```

### API Parameters
```python
extract_keywords_from_audit(
    audit_obj,      # Required: audit dictionary
    top_n=20,       # Optional: number of keywords (default: 20)
    enrich=True     # Optional: enable DataForSEO (default: True)
)
```

### DataForSEO Settings
```python
location_code = 2840  # USA (can be changed)
language_code = "en"  # English (can be changed)
```

## Monitoring

### Key Metrics
- Keywords extracted per request
- DataForSEO API calls per day (limit: 100)
- Average response time
- Enrichment success rate

### Logging
```python
import logging

logging.info(f"Extracted {len(keywords)} keywords")
logging.info(f"Enrichment: {enrich}, API calls: {1 if enrich else 0}")
```

## Scaling Considerations

### Current Limits
- DataForSEO: 100 requests/day (free tier)
- Each request: up to 100 keywords
- Daily capacity: ~10,000 keywords

### Optimization Strategies
1. **Caching**: Store enriched keywords in database
2. **Batching**: Group multiple URLs in one job
3. **Selective enrichment**: Only enrich top 20 keywords
4. **Upgrade tier**: Paid plans for higher limits

## Testing

### Unit Tests
```bash
# Test keyword extraction
python3 -c "from server.keyword_engine import extract_keywords_from_audit; ..."

# Test DataForSEO client
python3 -c "from server.dataforseo_client import enrich_keywords; ..."
```

### Integration Tests
```bash
# Full pipeline test
python3 test_keywords.py
```

### API Tests
```bash
# Test endpoint
curl -X POST http://localhost:8000/api/search/keywords \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 2}'
```
