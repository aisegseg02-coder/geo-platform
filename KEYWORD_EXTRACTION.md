# Keyword Extraction - DataForSEO Integration

## ✅ What's Fixed

Your keyword extraction now returns **accurate, enriched keywords** with:
- ✅ Search volume (monthly searches)
- ✅ CPC (cost per click in USD)
- ✅ Competition level (LOW/MEDIUM/HIGH)
- ✅ Better text cleaning (removes HTML, scripts, styles)
- ✅ Phrase extraction (2-3 word combinations)
- ✅ Smart prioritization (titles counted 2x, headings boosted)

## 🚀 Quick Start

### 1. Set up credentials (already done!)
```bash
# Your .env file
DATAFORSEO_LOGIN=ai.seg01@seginvest.com
DATAFORSEO_PASSWORD=712e269a1e24e50f
```

### 2. Test the integration
```bash
cd /home/ali/Downloads/t/geo-platform
python3 test_keywords.py
```

### 3. Use in your API

**Extract keywords from URL:**
```bash
curl -X POST http://localhost:8000/api/keywords \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abayanoir.com", "max_pages": 2}'
```

**Get keywords for a job:**
```bash
curl http://localhost:8000/api/jobs/123/keywords
```

**Disable enrichment (faster, no API calls):**
```bash
curl http://localhost:8000/api/jobs/123/keywords?enrich=false
```

## 📊 Example Output

```json
{
  "ok": true,
  "keywords": [
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
}
```

## 🔧 API Endpoints Updated

1. **POST /api/keywords** - Extract keywords from URL
   - Params: `url`, `max_pages`, `enrich` (default: true)

2. **GET /api/jobs/{job_id}/keywords** - Get keywords for completed job
   - Query: `?enrich=true` (default) or `?enrich=false`

3. **POST /api/search/keywords** - Search intelligence endpoint
   - Uses same enrichment logic

## 💡 How It Works

### Before (Inaccurate)
```
❌ Raw HTML extraction
❌ No volume/CPC data
❌ Generic stopwords only
❌ Single words only
```

### After (Accurate)
```
✅ Clean text extraction (strips HTML/scripts)
✅ DataForSEO enrichment (volume, CPC, competition)
✅ Extended stopwords (shop, menu, cart, etc.)
✅ Phrase extraction (2-3 words)
✅ Smart weighting (titles 2x, phrases 2x)
```

## 📈 DataForSEO Free Tier

- **100 requests/day** (free)
- Each request can check up to 100 keywords
- Covers: Google Ads search volume, CPC, competition
- Location: USA (code 2840) - configurable

## 🎯 Next Steps

### Option 1: Integrate into UI
Update `frontend/search.html` to display volume/CPC columns:
```javascript
keywords.forEach(kw => {
  row.innerHTML = `
    <td>${kw.kw}</td>
    <td>${kw.count}</td>
    <td>${kw.volume || 'N/A'}</td>
    <td>$${kw.cpc || 'N/A'}</td>
    <td>${kw.competition || 'N/A'}</td>
  `;
});
```

### Option 2: Add Competitor Analysis
Use DataForSEO's competitor endpoints:
```python
# server/dataforseo_client.py
def get_competitor_keywords(domain):
    # Returns keywords your competitors rank for
    pass
```

### Option 3: Add Keyword Clustering
Use spaCy + KeyBERT for semantic grouping:
```bash
pip install keybert sentence-transformers
```

## 🐛 Troubleshooting

**No volume data?**
- Check credentials in `.env`
- Verify API quota (100/day limit)
- Some keywords may have no data (returns None)

**Slow extraction?**
- Use `enrich=False` for faster results
- Reduce `top_n` parameter (default: 40)
- Cache results in database

**Wrong keywords?**
- Add domain-specific stopwords to `keyword_engine.py`
- Adjust phrase extraction regex
- Increase `max_pages` for more context

## 📝 Files Modified

1. `server/keyword_engine.py` - Core extraction logic
2. `server/dataforseo_client.py` - NEW: DataForSEO API client
3. `server/api.py` - Added `enrich` parameter
4. `server/search_intel.py` - Added `enrich` parameter
5. `.env.example` - NEW: Credential template
6. `test_keywords.py` - NEW: Test script

## 🎉 Results

Your GEO Platform now extracts **meaningful, actionable keywords** with real search data instead of generic HTML noise!

**Before:** "phone", "012", "mall" (no context)
**After:** "abaya" (60.5K searches, $0.81 CPC, HIGH competition)
