"""AI Content Engine — محرك المحتوى بالذكاء الاصطناعي
Supports: Groq (fast/free), OpenAI, Claude, Ollama.
2026 Standards: Grounded content, Entity graphs, Multi-schema, GEO local, Proof sections.
"""
import os
import json
import re
import requests

# ── LLM backends ──────────────────────────────────────────────────────────────

def _call_groq(prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv('GROQ_API_KEY')
    if not key:
        raise RuntimeError('GROQ_API_KEY not set')
    from groq import Groq
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.2,
        max_tokens=3000
    )
    return resp.choices[0].message.content


def _call_openai(prompt: str, api_key: str = None) -> str:
    from openai import OpenAI
    key = api_key or os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY not set')
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.2,
        max_tokens=3000
    )
    return resp.choices[0].message.content


def _call_claude(prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('CLAUDE_API_KEY not set')
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
        json={'model': os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022'),
              'max_tokens': 3000, 'messages': [{'role': 'user', 'content': prompt}]},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def _call_ollama(prompt: str, model: str = None) -> str:
    host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    model = model or os.getenv('OLLAMA_MODEL', 'llama3')
    resp = requests.post(f"{host}/api/chat", json={
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()['message']['content']


def _call_demo(prompt: str) -> str:
    """Honest demo — shows the STRUCTURE of what real output looks like, clearly marked as demo."""
    prompt_lower = prompt.lower()
    is_arabic = 'arabic' in prompt_lower or bool(re.search(r'[\u0600-\u06FF]', prompt))

    kw_match = re.search(r'keyword[:\s]+([^\n]+)', prompt, re.IGNORECASE)
    keyword = kw_match.group(1).strip() if kw_match else 'your keyword'

    site_match = re.search(r'target site[:\s]+([^\n,]+)', prompt, re.IGNORECASE)
    brand = site_match.group(1).strip() if site_match else 'YourBrand'

    # Extract any real page content passed in
    content_match = re.search(r'PAGE CONTENT[:\s]+(.*?)(?:\n\n|\Z)', prompt, re.DOTALL | re.IGNORECASE)
    real_snippet = content_match.group(1).strip()[:300] if content_match else ''

    if 'faq' in prompt_lower:
        if is_arabic:
            return json.dumps({"faqs": [
                {"question": f"ما هي خدمات {brand}؟",
                 "answer": f"[DEMO] {brand} تقدم خدمات متخصصة في مجال {keyword}. لتوليد إجابات حقيقية مبنية على بيانات موقعك، أضف مفتاح Groq API في الإعدادات."},
                {"question": f"كيف يساعد {brand} في تحسين الظهور؟",
                 "answer": f"[DEMO] من خلال استراتيجيات {keyword} المدعومة بالذكاء الاصطناعي. أضف Groq API للحصول على إجابات مبنية على بيانات زحف موقعك الفعلية."}
            ]}, ensure_ascii=False)
        return json.dumps({"faqs": [
            {"question": f"What does {brand} offer for {keyword}?",
             "answer": f"[DEMO] {brand} provides specialized {keyword} services. Add a Groq API key in Settings to generate answers grounded in your actual crawled data."},
            {"question": f"How does {brand} improve {keyword} rankings?",
             "answer": "[DEMO] Through AI-powered strategies. Connect your API key to generate evidence-based answers from your site's real content."}
        ]})

    if 'optimize' in prompt_lower or 'analyze' in prompt_lower:
        if is_arabic:
            return json.dumps({
                "score": 0,
                "issues": [
                    "⚠️ وضع تجريبي — لا يوجد مفتاح API",
                    "لا يمكن تحليل المحتوى بدون Groq أو OpenAI",
                    "أضف مفتاح API في الإعدادات للحصول على تحليل حقيقي"
                ],
                "suggestions": [
                    "أضف مفتاح Groq API (مجاني) للحصول على تحليل فوري",
                    "تأكد من ربط بيانات الزحف أولاً من مستودع الأبحاث"
                ],
                "optimized_content": f"[DEMO MODE] أضف مفتاح Groq API للحصول على محتوى محسّن حقيقي مبني على بيانات {brand}.",
                "schema": ""
            }, ensure_ascii=False)
        return json.dumps({
            "score": 0,
            "issues": ["⚠️ Demo mode — no API key connected", "Real analysis requires Groq or OpenAI key"],
            "suggestions": ["Add a free Groq API key in Settings", "Connect crawled data from Research Repository first"],
            "optimized_content": f"[DEMO MODE] Add Groq API key to get real optimized content grounded in {brand}'s actual data.",
            "schema": ""
        })

    # Article generation demo
    if is_arabic:
        return json.dumps({
            "title": f"[DEMO] {brand}: دليل {keyword} — أضف Groq API للمحتوى الحقيقي",
            "meta_description": f"[DEMO] وصف تعريفي لـ {brand} في مجال {keyword}. أضف مفتاح API للحصول على وصف حقيقي.",
            "content": f"""# [وضع تجريبي — أضف Groq API للمحتوى الحقيقي]

## ما الذي ستحصل عليه بعد إضافة مفتاح API؟

### 1. الإجابة المباشرة (Direct Answer)
محتوى محدد وقابل للاقتباس من محركات الذكاء الاصطناعي، مبني على بيانات موقع {brand} الفعلية.
{f'بيانات من موقعك: {real_snippet}' if real_snippet else ''}

### 2. خريطة الكيانات (Entity Graph)
```
{brand} → (Organization/LocalBusiness)
    ├── provides → [{keyword}]
    ├── operates_in → [المدينة/الدولة]
    ├── competes_with → [المنافسون]
    └── recognized_by → [Google, Bing, Perplexity]
```

### 3. طبقة GEO المحلية
- كلمات مفتاحية محلية: "{keyword} في الرياض"، "{keyword} السعودية"
- Google Maps integration
- LocalBusiness Schema

### 4. قسم الإثبات (Proof Section)
- أرقام وإحصائيات حقيقية من موقعك
- Case studies
- نتائج قابلة للقياس

### 5. Schema متكامل
Organization + LocalBusiness + Service + FAQ

---
⚙️ لتفعيل المحتوى الحقيقي: أضف مفتاح Groq API في الإعدادات (مجاني على groq.com)""",
            "faqs": [
                {"question": f"[DEMO] ما هي خدمات {brand}؟",
                 "answer": "أضف Groq API للحصول على إجابات مبنية على بيانات موقعك الفعلية."}
            ],
            "schema": "",
            "implemented_fixes": ["DEMO MODE — add API key for real implementation"],
            "backend": "demo"
        }, ensure_ascii=False)

    return json.dumps({
        "title": f"[DEMO] {brand}: {keyword} Guide — Add Groq API for Real Content",
        "meta_description": f"[DEMO] Add a Groq API key to generate content grounded in {brand}'s actual crawled data.",
        "content": f"""# [DEMO MODE — Add Groq API for Real Content]

## What you'll get with a real API key:

### 1. Direct Answer (AI-Citable)
A specific, evidence-based 50-word answer about {brand} and {keyword}, built from your crawled pages.
{f'Your site data: {real_snippet}' if real_snippet else ''}

### 2. Entity Graph
```
{brand} → (Organization)
    ├── provides → [{keyword}]
    ├── operates_in → [City/Country]
    ├── competes_with → [Real competitors]
    └── cited_by → [ChatGPT, Perplexity, Google SGE]
```

### 3. GEO Local Layer
- Local keywords: "{keyword} in [City]", "best {keyword} [Country]"
- Google Maps signals
- LocalBusiness Schema

### 4. Proof Section
- Real metrics from your site
- Case studies
- Measurable outcomes

### 5. Full Schema Stack
Organization + LocalBusiness + Service + FAQ

---
⚙️ To activate: Add free Groq API key in Settings (groq.com)""",
        "faqs": [
            {"question": f"[DEMO] What does {brand} offer for {keyword}?",
             "answer": "Add Groq API key to generate answers grounded in your actual site data."}
        ],
        "schema": "",
        "implemented_fixes": ["DEMO MODE — add API key for real implementation"],
        "backend": "demo"
    })


def _llm_call(prompt: str, prefer: str = 'groq', api_keys: dict = None) -> dict:
    """Try backends in order. Returns {text, backend}."""
    api_keys = api_keys or {}
    order = [prefer] + [b for b in ['groq', 'openai', 'claude', 'ollama', 'demo'] if b != prefer]
    errors = {}
    for backend in order:
        try:
            if backend == 'groq':
                return {'text': _call_groq(prompt, api_keys.get('groq')), 'backend': 'groq'}
            elif backend == 'openai':
                return {'text': _call_openai(prompt, api_keys.get('openai')), 'backend': 'openai'}
            elif backend == 'claude':
                return {'text': _call_claude(prompt, api_keys.get('claude')), 'backend': 'claude'}
            elif backend == 'ollama':
                return {'text': _call_ollama(prompt), 'backend': 'ollama'}
            elif backend == 'demo':
                return {'text': _call_demo(prompt), 'backend': 'demo'}
        except Exception as e:
            errors[backend] = str(e)
            continue
    return {'text': _call_demo(prompt), 'backend': 'demo'}


def _parse_json_from_text(text: str) -> dict:
    """Extract first JSON object from LLM response."""
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if not json_match:
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    block = json_match.group(1).strip() if json_match else text.strip()

    def repair(match):
        inner = match.group(0)[1:-1]
        inner = inner.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{inner}"'

    repaired = re.sub(r'"(?:\\.|[^"\\])*"', repair, block, flags=re.DOTALL)
    try:
        return json.loads(repaired, strict=False)
    except Exception:
        try:
            return json.loads(block, strict=False)
        except Exception:
            raise ValueError('No JSON found in LLM response')


def _build_context_block(crawl_data: dict) -> str:
    """Build a grounded context block from real crawled data."""
    if not crawl_data:
        return ''
    lines = ['=== GROUNDED DATA FROM CRAWLED SITE ===']
    if crawl_data.get('org_name'):
        lines.append(f'Brand: {crawl_data["org_name"]}')
    if crawl_data.get('url'):
        lines.append(f'Site: {crawl_data["url"]}')
    if crawl_data.get('keywords'):
        kws = [k.get('kw', k) if isinstance(k, dict) else k for k in crawl_data['keywords'][:15]]
        lines.append(f'Top Keywords: {", ".join(kws)}')
    if crawl_data.get('headings'):
        lines.append(f'Site Structure: {" | ".join(crawl_data["headings"][:8])}')
    if crawl_data.get('page_content'):
        lines.append(f'Page Content Sample:\n{crawl_data["page_content"][:1000]}')
    if crawl_data.get('competitors'):
        lines.append(f'Detected Competitors: {", ".join(crawl_data["competitors"][:5])}')
    if crawl_data.get('geo_score'):
        gs = crawl_data['geo_score']
        lines.append(f'Current GEO Score: {gs.get("score", 0)}% — {gs.get("status", "")}')
    if crawl_data.get('issues'):
        lines.append(f'Critical Issues: {"; ".join(crawl_data["issues"][:5])}')
    if crawl_data.get('local_regions'):
        lines.append(f'Detected Regions: {", ".join(crawl_data["local_regions"])}')
    lines.append('=== END GROUNDED DATA ===')
    return '\n'.join(lines)


def _build_schema(brand: str, keyword: str, url: str, lang: str,
                  faqs: list = None, local_regions: list = None) -> str:
    """Build a complete multi-type Schema.org JSON-LD block."""
    schemas = []

    # Organization
    org = {
        "@context": "https://schema.org",
        "@type": ["Organization", "LocalBusiness"] if local_regions else ["Organization"],
        "name": brand,
        "url": url or f"https://{brand.lower().replace(' ', '')}.com",
        "description": f"{brand} provides {keyword} services",
        "knowsAbout": [keyword],
    }
    if local_regions:
        org["areaServed"] = local_regions
        org["@type"] = "LocalBusiness"
    schemas.append(org)

    # Service
    schemas.append({
        "@context": "https://schema.org",
        "@type": "Service",
        "name": keyword,
        "provider": {"@type": "Organization", "name": brand},
        "areaServed": local_regions or ["Global"],
        "description": f"Professional {keyword} services by {brand}"
    })

    # FAQPage
    if faqs:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["question"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}}
                for f in faqs[:5]
            ]
        })

    blocks = '\n'.join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas
    )
    return blocks


# ── Core features ──────────────────────────────────────────────────────────────

def generate_article(keyword: str, lang: str = 'en', target_site: str = '',
                     research_insights: list = None,
                     competitors_content: list = None,
                     crawl_data: dict = None,
                     prefer_backend: str = 'groq', api_keys: dict = None) -> dict:
    """Generate a full GEO-optimized article grounded in real crawled data."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    context_block = _build_context_block(crawl_data or {})
    insights_block = ('Research Insights (implement these):\n' +
                      '\n'.join(f'- {i}' for i in (research_insights or [])) + '\n') if research_insights else ''
    comp_block = ('Competitor Content (use as reference, do NOT copy):\n' +
                  '\n---\n'.join((competitors_content or [])[:2])) if competitors_content else ''

    local_regions = (crawl_data or {}).get('local_regions', [])
    local_hint = f'Target Regions: {", ".join(local_regions)}' if local_regions else ''

    prompt = f"""You are an expert GEO (Generative Engine Optimization) content architect for 2026.

TASK: Write a high-authority article that AI engines (ChatGPT, Perplexity, Google SGE) will cite.

TARGET KEYWORD: {keyword}
LANGUAGE: {lang_label}
BRAND/SITE: {target_site}
{local_hint}

{context_block}
{insights_block}
{comp_block}

STRICT RULES — VIOLATIONS WILL MAKE THE CONTENT USELESS:
1. DIRECT ANSWER FIRST: The opening 50-70 words MUST be a specific, citable statement about {target_site}.
   - Include: what they do, where they operate, one measurable outcome or differentiator.
   - BAD: "{target_site} represents best practices..." (generic, uncitable)
   - GOOD: "{target_site} is a [specific service] company in [location] that helps [audience] achieve [specific result] through [method]."

2. NO KEYWORD SPAM: Use the keyword naturally. Never repeat "{keyword}" more than once per paragraph.

3. ENTITY GRAPH: Include a section mapping relationships:
   {target_site} → provides → [{keyword}]
   {target_site} → operates_in → [real locations from data]
   {target_site} → competes_with → [real competitors from data]

4. GEO LOCAL LAYER: If location data exists, include city-specific keywords naturally.
   Example: "{keyword} in Riyadh", "best {keyword} Saudi Arabia"

5. PROOF SECTION: Include a "Results & Evidence" section with:
   - Specific metrics (use [[METRIC_NEEDED]] if not in data)
   - Case study structure (use [[CASE_STUDY_NEEDED]] if not in data)
   - Never invent fake numbers

6. CONTENT STRUCTURE (H-tags):
   H1: [Brand] + [Keyword] + [Location if applicable]
   H2: Direct Answer | Services | GEO Local | Proof/Results | FAQ

7. SCHEMA: Generate Organization + LocalBusiness (if local) + Service + FAQPage schemas.

8. CITATIONS: Reference authoritative sources where relevant (Google, industry reports).

Return ONLY valid JSON:
{{
  "title": "click-worthy H1 with brand + keyword + location",
  "meta_description": "155 chars max, includes keyword + location + value prop",
  "content": "full markdown article",
  "faqs": [{{"question": "...", "answer": "specific, citable, 3-4 sentences"}}],
  "entity_graph": [{{"subject": "...", "relation": "...", "object": "..."}}],
  "local_keywords": ["keyword in city", ...],
  "proof_placeholders": ["[[METRIC_NEEDED: X]]", ...],
  "schema": "<script type=application/ld+json>...</script>",
  "implemented_fixes": ["list of specific improvements made"]
}}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['keyword'] = keyword
    parsed['lang'] = lang

    # Build schema from data if LLM didn't provide a good one
    if not parsed.get('schema') or len(parsed.get('schema', '')) < 100:
        parsed['schema'] = _build_schema(
            brand=target_site or keyword,
            keyword=keyword,
            url=(crawl_data or {}).get('url', ''),
            lang=lang,
            faqs=parsed.get('faqs', []),
            local_regions=local_regions
        )
    return parsed


def optimize_content(content: str, keyword: str, lang: str = 'en', target_site: str = '',
                     research_insights: list = None,
                     crawl_data: dict = None,
                     prefer_backend: str = 'groq', api_keys: dict = None) -> dict:
    """Analyze and optimize existing content for GEO. Returns grounded improvements."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    context_block = _build_context_block(crawl_data or {})
    insights_block = ('Research Insights:\n' +
                      '\n'.join(f'- {i}' for i in (research_insights or [])) + '\n') if research_insights else ''

    prompt = f"""You are an Elite GEO Content Auditor for 2026.

TASK: Audit and rewrite this content to maximize AI engine citation probability.

KEYWORD: {keyword}
LANGUAGE: {lang_label}
BRAND: {target_site}

{context_block}
{insights_block}

AUDIT CRITERIA (score each 0-20):
1. Direct Answer Quality: Does it open with a specific, citable statement? (not generic marketing)
2. Entity Coverage: Are brand, location, service, audience entities clearly defined?
3. Keyword Intent Match: Does content match what users actually search for?
4. Proof & Evidence: Are there specific numbers, results, case studies?
5. Schema Readiness: Is content structured for JSON-LD extraction?

REWRITE RULES:
- Fix the Direct Answer to be specific and citable
- Remove keyword spam (natural usage only)
- Add entity relationships explicitly
- Add [[PROOF_NEEDED: metric type]] where evidence is missing
- Add GEO local keywords if location data available
- Improve H-tag hierarchy

Return ONLY valid JSON:
{{
  "score": 0-100,
  "score_breakdown": {{"direct_answer": 0-20, "entities": 0-20, "intent": 0-20, "proof": 0-20, "schema": 0-20}},
  "issues": ["specific issue with line/section reference"],
  "suggestions": ["specific actionable fix"],
  "optimized_content": "full rewritten content in markdown",
  "schema": "<script type=application/ld+json>...</script>",
  "implemented_fixes": ["what was changed and why"]
}}

CONTENT TO AUDIT:
{content[:3000]}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    return parsed


def generate_faqs(topic: str, page_content: str = None, lang: str = 'en', count: int = 5,
                  prefer_backend: str = 'groq', api_keys: dict = None,
                  target_site: str = '', research_insights: list = None,
                  crawl_data: dict = None) -> dict:
    """Generate FAQ pairs grounded in real crawled data."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    context_block = _build_context_block(crawl_data or {})
    insights_block = ('Research Insights:\n' +
                      '\n'.join(f'- {i}' for i in (research_insights or [])) + '\n') if research_insights else ''
    context = f'\nPage Content:\n{page_content[:1500]}' if page_content else ''

    prompt = f"""Generate {count} high-performance GEO FAQ pairs for AI engine citation.

TOPIC: {topic}
LANGUAGE: {lang_label}
BRAND: {target_site}

{context_block}
{insights_block}{context}

FAQ QUALITY RULES:
1. Questions must be REAL user queries (long-tail, conversational, as asked on Perplexity/ChatGPT)
   - BAD: "What is {topic}?" (too generic)
   - GOOD: "How does {target_site} help businesses improve {topic} in [location]?"

2. Answers must be SPECIFIC and CITABLE:
   - Lead with a direct fact from the crawled data
   - Include brand name, service, location where relevant
   - 3-4 sentences max
   - Never use generic phrases like "in today's digital landscape"

3. Cover these intent types: Informational, Commercial, Local/GEO

Return ONLY JSON: {{"faqs": [{{"question": "...", "answer": "..."}}]}}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['topic'] = topic
    parsed['lang'] = lang
    return parsed


def semantic_optimize(content: str, lang: str = 'en',
                      prefer_backend: str = 'groq', api_keys: dict = None) -> dict:
    """Extract semantic entities, build entity graph, suggest LSI keywords."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'

    entities_extracted = []
    if lang == 'ar':
        try:
            from src import arabic_tools
            ner_res = arabic_tools.extract_entities_arabic(content)
            for e in ner_res.get('entities', []):
                entities_extracted.append({'text': e['text'], 'type': e['label']})
        except Exception:
            pass

    prompt = f"""Perform deep semantic analysis on this {lang_label} content for GEO optimization.

Return ONLY valid JSON:
{{
  "entities": [{{"text": "...", "type": "ORG|PERSON|PRODUCT|PLACE|CONCEPT|SERVICE"}}],
  "entity_graph": [{{"subject": "...", "relation": "provides|operates_in|competes_with|serves|part_of", "object": "..."}}],
  "topics": ["main topics covered"],
  "lsi_keywords": ["semantically related keywords to add"],
  "missing_entities": ["important entities not mentioned"],
  "local_signals": ["any location/GEO signals found"],
  "semantic_score": 0-100,
  "missing_concepts": ["important concepts not covered"]
}}

Content:
{content[:3000]}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])

    if lang == 'ar' and entities_extracted:
        existing = {e['text'].lower() for e in parsed.get('entities', [])}
        for e in entities_extracted:
            if e['text'].lower() not in existing:
                parsed.setdefault('entities', []).append(e)

    parsed['backend'] = result['backend']
    return parsed
