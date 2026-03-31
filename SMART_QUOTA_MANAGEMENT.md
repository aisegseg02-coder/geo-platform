# Smart API Quota Management System

## 🎯 Overview

The Moharek GEO Platform now includes **intelligent API quota management** that automatically switches between multiple API providers when one reaches its rate limit or quota.

---

## 🔄 How It Works

### **Multi-Provider Fallback Chain**

#### **LLM Providers (AI Analysis)**
```
Priority Order:
1. Ollama (Local, Free, Unlimited)
   ↓ (if unavailable)
2. OpenAI (gpt-4o-mini)
   ↓ (if quota exceeded)
3. Groq (llama-3.1-8b-instant)
   ↓ (if quota exceeded)
4. OpenRouter (gpt-4o-mini / gemini-flash-1.5)
```

#### **Search APIs (Rankings & Competitors)**
```
Priority Order:
1. SerpAPI (100 searches/month free)
   ↓ (if quota exceeded)
2. ZenSerp (50 searches/month free)
```

---

## 🧠 Smart Detection Logic

### **Rate Limit Detection**

The system detects quota exhaustion through:

1. **HTTP Status Codes**
   - `429 Too Many Requests`
   - `403 Forbidden` (quota exceeded)

2. **Error Messages**
   - "rate_limit_exceeded"
   - "insufficient_quota"
   - "quota exceeded"
   - "too many requests"
   - "credits exhausted"

3. **Response Validation**
   - Empty responses
   - Error objects in JSON
   - Timeout errors

### **Automatic Switching**

```python
# Example: LLM Router
providers = [
    {"name": "Ollama", "enabled": True},
    {"name": "OpenAI", "enabled": has_key},
    {"name": "Groq", "enabled": has_key},
    {"name": "OpenRouter", "enabled": has_key}
]

for provider in providers:
    try:
        result = provider.call(prompt)
        if is_quota_error(result):
            print(f"⚠ {provider.name} quota exceeded, switching...")
            continue  # Try next provider
        return result  # Success!
    except RateLimitError:
        continue  # Try next provider
```

---

## 📊 API Quotas & Limits

### **LLM Providers**

| Provider | Free Tier | Rate Limit | Notes |
|----------|-----------|------------|-------|
| **Ollama** | Unlimited | None | Local installation required |
| **OpenAI** | $5 credit | 3 RPM | gpt-4o-mini: $0.15/1M tokens |
| **Groq** | Free | 30 RPM | llama-3.1-8b: Very fast |
| **OpenRouter** | $1 credit | Varies | Multiple models available |

### **Search APIs**

| Provider | Free Tier | Rate Limit | Cost After |
|----------|-----------|------------|------------|
| **SerpAPI** | 100 searches/month | 1 RPS | $50/month for 5K |
| **ZenSerp** | 50 searches/month | 1 RPS | $30/month for 5K |

---

## 🔧 Implementation Details

### **1. Enhanced Error Handling**

```python
def _openai_chat(prompt: str, api_key: str = None) -> str:
    try:
        r = requests.post(...)
        
        # Detect 429 status
        if r.status_code == 429:
            return "ERROR: OpenAI rate limit exceeded (429)"
        
        # Check response for quota errors
        data = r.json()
        if "error" in data:
            if "quota" in data["error"]["message"].lower():
                return "ERROR: OpenAI quota exceeded"
        
        return data["choices"][0]["message"]["content"]
    except HTTPError as e:
        if e.response.status_code == 429:
            return "ERROR: Rate limit (429)"
```

### **2. Smart Router Logic**

```python
def _llm(prompt: str, api_keys: dict = None) -> str:
    providers = [
        {
            "name": "Ollama",
            "func": lambda: _ollama_chat(prompt),
            "quota_errors": ["connection refused", "timeout"]
        },
        {
            "name": "OpenAI",
            "func": lambda: _openai_chat(prompt, api_key),
            "quota_errors": ["429", "rate_limit", "quota"]
        },
        # ... more providers
    ]
    
    for provider in providers:
        try:
            result = provider["func"]()
            
            # Check if quota error
            is_quota = any(
                err in result.lower() 
                for err in provider["quota_errors"]
            )
            
            if is_quota:
                print(f"⚠ {provider['name']} quota exceeded")
                continue  # Try next
            
            if result and not result.startswith("ERROR:"):
                print(f"✓ {provider['name']} succeeded")
                return result
                
        except Exception as e:
            continue  # Try next
    
    return "ERROR: All providers exhausted"
```

### **3. Search API Switching**

```python
def get_competitor_insights(...):
    serp_exhausted = False
    zen_exhausted = False
    
    for query in queries:
        result = None
        
        # Try SerpAPI first
        if not serp_exhausted:
            result = _serp_api_search(query)
            if result.get("error") == "rate_limit":
                serp_exhausted = True
                result = None
        
        # Fallback to ZenSerp
        if not result and not zen_exhausted:
            result = _zenserp_search(query)
            if result.get("error") == "rate_limit":
                zen_exhausted = True
        
        if result:
            process_result(result)
```

---

## 📈 Benefits

### **1. Cost Optimization**
- Uses free local Ollama first
- Only uses paid APIs when necessary
- Automatically switches to cheaper alternatives

### **2. Reliability**
- No single point of failure
- Continues working even if one API is down
- Graceful degradation

### **3. Performance**
- Ollama (local) is fastest
- Falls back to cloud only when needed
- Parallel processing where possible

### **4. Transparency**
- Clear logging of which provider is used
- Quota exhaustion warnings
- Error messages show which API failed

---

## 🎮 Usage Examples

### **Example 1: LLM Analysis**

```python
# User makes request
result = _llm("Analyze this brand: elbatt.com", api_keys)

# System tries:
# 1. Ollama (local) → Connection refused
# 2. OpenAI → Rate limit (429)
# 3. Groq → Success! ✓

# Output: "elbatt.com is an e-commerce platform..."
```

**Console Output:**
```
⚠ Ollama: Connection refused
⚠ OpenAI quota exceeded, trying next provider
✓ Groq succeeded
```

### **Example 2: Search Rankings**

```python
# Fetch competitor data
insights = get_competitor_insights("elbatt", url, api_keys)

# System tries:
# Query 1: SerpAPI → Success ✓
# Query 2: SerpAPI → Rate limit (429)
# Query 2: ZenSerp → Success ✓
# Query 3: ZenSerp → Success ✓
```

**Console Output:**
```
✓ SerpAPI: Query 1 completed
⚠ SerpAPI quota exhausted, switching to ZenSerp
✓ ZenSerp: Query 2 completed
✓ ZenSerp: Query 3 completed
```

---

## 🔍 Monitoring & Debugging

### **Server Logs**

The system provides detailed logging:

```bash
# Success
✓ OpenAI succeeded

# Quota exceeded
⚠ OpenAI quota exceeded, trying next provider
⚠ SerpAPI rate limit exceeded (429)

# All failed
❌ LLM FAILURE: Ollama: timeout | OpenAI: 429 | Groq: quota | OpenRouter: credits
```

### **API Response Indicators**

```json
{
  "ok": true,
  "analysis": {...},
  "provider_used": "Groq",
  "fallback_count": 2,
  "warnings": [
    "OpenAI quota exceeded",
    "Switched to Groq"
  ]
}
```

---

## ⚙️ Configuration

### **Environment Variables**

```bash
# LLM Providers
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...
OLLAMA_HOST=http://localhost:11434

# Search APIs
SERPAPI_KEY=b31a84f7e45cc6c60f6de3627bf6650a...
ZENSERP_KEY=a50d7a20-2698-11f1-a47e-edf101aaf1cf
```

### **Priority Customization**

You can customize the provider order by modifying `geo_services.py`:

```python
providers = [
    {"name": "Groq", ...},      # Try Groq first
    {"name": "OpenAI", ...},    # Then OpenAI
    {"name": "Ollama", ...},    # Then local
]
```

---

## 🚨 Error Handling

### **Graceful Degradation**

```python
# If all LLM providers fail
if result.startswith("ERROR:"):
    # Use heuristic fallback
    industry = detect_industry_from_keywords(content)
    competitors = get_default_competitors(industry)
    return {
        "industry": industry,
        "competitors": competitors,
        "note": "Using fallback data (all AI providers exhausted)"
    }
```

### **User-Friendly Messages**

```javascript
// Frontend displays
if (data.note.includes("exhausted")) {
  showWarning("⚠️ API quotas reached. Using cached data.");
}
```

---

## 📊 Quota Tracking

### **Recommended: Add Usage Tracking**

```python
# Track API usage
usage_stats = {
    "openai": {"calls": 0, "tokens": 0, "cost": 0},
    "groq": {"calls": 0, "tokens": 0},
    "serpapi": {"calls": 0, "remaining": 100}
}

def _openai_chat(...):
    result = call_api()
    usage_stats["openai"]["calls"] += 1
    usage_stats["openai"]["tokens"] += result.usage.total_tokens
    return result
```

### **Dashboard Display**

```
API Usage Today:
├─ OpenAI: 45/100 calls (45%)
├─ Groq: 120/unlimited calls
├─ SerpAPI: 23/100 searches (23%)
└─ ZenSerp: 5/50 searches (10%)
```

---

## 🎯 Best Practices

### **1. Set Up All Providers**
- Don't rely on a single API
- Configure at least 2 LLM providers
- Have backup search API

### **2. Monitor Usage**
- Check logs regularly
- Track which providers are used most
- Plan upgrades before hitting limits

### **3. Optimize Requests**
- Cache frequent queries
- Batch similar requests
- Use local Ollama for development

### **4. Handle Errors Gracefully**
- Always have fallback data
- Show clear messages to users
- Log errors for debugging

---

## 🔮 Future Enhancements

### **Planned Features**

1. **Smart Caching**
   ```python
   # Cache LLM responses for 24h
   cache_key = hash(prompt)
   if cache_key in redis:
       return redis.get(cache_key)
   ```

2. **Load Balancing**
   ```python
   # Distribute load across providers
   if openai_usage < 50%:
       use_openai()
   else:
       use_groq()
   ```

3. **Cost Tracking**
   ```python
   # Track spending per provider
   monthly_cost = {
       "openai": calculate_cost(tokens),
       "serpapi": searches * 0.50
   }
   ```

4. **Quota Prediction**
   ```python
   # Predict when quota will run out
   daily_rate = calls_today / hours_elapsed
   hours_remaining = quota_left / daily_rate
   ```

---

## 📞 Troubleshooting

### **Issue: All LLM providers failing**

**Solution:**
1. Check API keys in `.env`
2. Verify internet connection
3. Check provider status pages
4. Try Ollama locally

### **Issue: Search APIs exhausted**

**Solution:**
1. Wait for quota reset (monthly)
2. Upgrade to paid plan
3. Use cached competitor data
4. Reduce analysis frequency

### **Issue: Slow responses**

**Solution:**
1. Use Ollama for faster local processing
2. Reduce max_tokens in prompts
3. Cache frequent queries
4. Batch requests

---

## ✅ Testing

### **Test Quota Handling**

```bash
# Simulate quota exhaustion
export OPENAI_API_KEY="invalid_key"
export GROQ_API_KEY="valid_key"

# Run analysis
curl -X POST http://localhost:8000/api/analyze \
  -d '{"job_id": 196}'

# Expected: Should use Groq after OpenAI fails
```

### **Test Search API Fallback**

```bash
# Exhaust SerpAPI quota (make 100+ requests)
for i in {1..101}; do
  curl "https://serpapi.com/search?q=test&api_key=$SERPAPI_KEY"
done

# Next request should use ZenSerp
curl -X POST http://localhost:8000/api/analyze -d '{"job_id": 196}'
```

---

## 📚 Related Documentation

- [REAL_DATA_INTEGRATION_SUMMARY.md](./REAL_DATA_INTEGRATION_SUMMARY.md) - Complete system overview
- [API Documentation](./API_DOCS.md) - Endpoint reference
- [.env.example](./.env.example) - Configuration template

---

**Last Updated:** 2026-03-29  
**Version:** 2.1 (Smart Quota Management)  
**Status:** ✅ Production Ready
