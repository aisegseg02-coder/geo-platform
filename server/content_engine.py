"""AI Content Engine — محرك المحتوى بالذكاء الاصطناعي
Supports: Groq (fast/free), OpenAI, Claude, Ollama.
2026 Standards: Grounded content, Entity graphs, Multi-schema, GEO local, Proof sections.
"""
import os
import json
import re
import requests
import sys

# ── LLM backends ──────────────────────────────────────────────────────────────

def _call_groq(prompt: str, api_key: str = None) -> str:
    import requests
    keys = [api_key.strip()] if api_key and api_key.strip() else []
    for suffix in ['', '_2', '_3', '_4', '_5']:
        k = os.getenv(f'GROQ_API_KEY{suffix}')
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    
    if not keys:
        raise RuntimeError('No GROQ_API_KEY found in .env or passed')
    
    last_err = None
    for key in keys:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 3000
                },
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All GROQ keys failed. Last error: {last_err}")


def _call_openai(prompt: str, api_key: str = None) -> str:
    import requests
    keys = [api_key.strip()] if api_key and api_key.strip() else []
    for suffix in ['', '_2', '_3', '_4', '_5']:
        k = os.getenv(f'OPENAI_API_KEY{suffix}')
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    
    if not keys:
        raise RuntimeError('No OPENAI_API_KEY found in .env or passed')
    
    last_err = None
    for key in keys:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 3000
                },
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All OPENAI keys failed. Last error: {last_err}")


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

    # Extract keyword
    kw_match = re.search(r'(?:TARGET KEYWORD|keyword)[:\s]+([^\n]+)', prompt, re.IGNORECASE)
    keyword = kw_match.group(1).strip() if kw_match else 'your keyword'

    # Extract brand — try multiple patterns
    brand = 'YourBrand'
    for pattern in [
        r'Brand[:\s]+([^\n,]+)',
        r'BRAND[:\s]+([^\n,]+)',
        r'BRAND/SITE[:\s]+([^\n,]+)',
        r'target site[:\s]+([^\n,]+)',
    ]:
        m = re.search(pattern, prompt, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Clean URL from brand
            if ',' in candidate:
                parts = [p.strip() for p in candidate.split(',')]
                candidate = next((p for p in parts if not p.startswith('http')), parts[-1])
            if candidate.startswith('http'):
                candidate = candidate.split('//')[-1].split('/')[0].replace('www.', '')
            if candidate and candidate != 'YourBrand':
                brand = candidate
                break

    # Extract real page content if passed
    content_match = re.search(r'Page Content[:\s]+(.*?)(?:\n\n|\Z)', prompt, re.DOTALL | re.IGNORECASE)
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

    if 'optimize' in prompt_lower or 'analyze' in prompt_lower or 'audit' in prompt_lower:
        if is_arabic:
            return json.dumps({
                "score": 42,
                "score_breakdown": {"direct_answer": 8, "entities": 12, "intent": 5, "proof": 7, "schema": 10},
                "issues": [
                    "فشل في الاتصال بمحركات الذكاء الاصطناعي (أضف مفتاح API)",
                    "غياب الإجابة المباشرة (Direct Answer) القابلة للاقتباس",
                    "ضعف في كثافة الكيانات المرتبطة بالعلامة التجارية"
                ],
                "suggestions": [
                    "أضف مفتاح Groq API في 'إعدادات النظام' لتفعيل التحليل الحقيقي",
                    "اربط بيانات الزحف من 'سجل الأبحاث' لضبط سياق الـ GEO",
                    "استخدم ميزة 'الهوية الذكية' أولاً لبناء أساس المعرفة"
                ],
                "implemented_fixes": [
                    "تفعيل وضع المعاينة (Demo Mode) لهيكلة البيانات",
                    "تهيئة واجهة v2.0-ULTRA لاستقبال البيانات الحقيقية",
                    "فحص توافق مفاتيح API (لم يتم العثور على مفتاح)"
                ],
                "optimized_content": f"# [وضع العرض] تحسين {keyword} لموقع {brand}\n\nهذا مجرد نموذج عرض لشكل النتائج. للحصول على محتوى محسّن حقيقي مبني على بيانات موقعك، يرجى إضافة مفتاح API صحيح في الإعدادات.",
                "schema": "",
                "backend": "demo"
            }, ensure_ascii=False)
        return json.dumps({
            "score": 42,
            "score_breakdown": {"direct_answer": 8, "entities": 12, "intent": 5, "proof": 7, "schema": 10},
            "issues": ["⚠️ No API key connected (Demo Mode)", "Direct Answer missing or too generic", "Entity density below required threshold"],
            "suggestions": ["Add a Groq API key in System Settings", "Connect Research data to enable grounding", "Run 'Smart Identity' module first"],
            "implemented_fixes": [
                "Initialized v2.0-ULTRA Premium Interface",
                f"Mapped semantic requirements for {keyword}",
                f"Validated site context for {brand}"
            ],
            "optimized_content": f"# [DEMO] {keyword} Optimization for {brand}\n\nAdd your Groq or OpenAI API key in Settings to generate a real, grounded version of this content.",
            "schema": "",
            "backend": "demo"
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
 لتفعيل المحتوى الحقيقي: أضف مفتاح Groq API في الإعدادات (مجاني على groq.com)""",
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
 To activate: Add free Groq API key in Settings (groq.com)""",
        "faqs": [
            {"question": f"[DEMO] What does {brand} offer for {keyword}?",
             "answer": "Add Groq API key to generate answers grounded in your actual site data."}
        ],
        "schema": "",
        "implemented_fixes": ["DEMO MODE — add API key for real implementation"],
        "backend": "demo"
    })


def _llm_call(prompt: str, prefer: str = 'groq', api_keys: dict = None) -> dict:
    """Try backends in order. Returns {text, backend, errors}."""
    api_keys = {k: (v.strip() if v else None) for k, v in (api_keys or {}).items()}
    order = [prefer] + [b for b in ['groq', 'openai', 'claude', 'ollama', 'demo'] if b != prefer]
    errors = {}
    for backend in order:
        try:
            if backend == 'groq':
                text = _call_groq(prompt, api_keys.get('groq'))
                return {'text': text, 'backend': 'groq'}
            elif backend == 'openai':
                text = _call_openai(prompt, api_keys.get('openai'))
                return {'text': text, 'backend': 'openai'}
            elif backend == 'claude':
                text = _call_claude(prompt, api_keys.get('claude'))
                return {'text': text, 'backend': 'claude'}
            elif backend == 'ollama':
                text = _call_ollama(prompt)
                return {'text': text, 'backend': 'ollama'}
            elif backend == 'demo':
                text = _call_demo(prompt)
                # Parse demo result to inject errors for transparency
                try:
                    res = json.loads(text)
                    if isinstance(res, dict):
                        res['backend_errors'] = errors
                        text = json.dumps(res, ensure_ascii=False)
                except: pass
                return {'text': text, 'backend': 'demo', 'errors': errors}
        except Exception as e:
            errors[backend] = str(e)
            print(f"[ContentEngine] Backend {backend} failed: {e}")
            continue
    return {'text': _call_demo(prompt), 'backend': 'demo', 'errors': errors}


def _parse_json_from_text(text: str) -> dict:
    """Extract first JSON object from LLM response with robust fallback and repair."""
    if not text or not text.strip():
        raise ValueError('Empty LLM response')

    # Strip conversational LLM wrappers or markdown
    text = text.strip()
    if "```json" in text.lower():
        # Get the content between ```json and the next ```
        parts = re.split(r'```json', text, flags=re.IGNORECASE)
        if len(parts) > 1:
            text = parts[1].split("```")[0]
    elif "```" in text:
        # Fallback for generic markdown blocks
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
            
    # Find the absolute outermost JSON object boundaries
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end >= start:
        block = text[start:end+1]
    else:
        block = text.strip()

    # Try direct parse first
    try:
        return json.loads(block, strict=False)
    except Exception:
        pass

    # Try repair: escape unescaped newlines in strings
    def repair_newlines(match):
        inner = match.group(0)[1:-1]
        inner = inner.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{inner}"'

    try:
        repaired = re.sub(r'"(?:\\.|[^"\\])*"', repair_newlines, block, flags=re.DOTALL)
        return json.loads(repaired, strict=False)
    except Exception as e:
        # Log failure for diagnosis
        print(f"[ContentEngine] JSON Parsing Failed. Block snippet:\n{text[:300]}...\nError: {e}", file=sys.stderr)
        raise ValueError('No JSON found in LLM response')


def _build_context_block(crawl_data: dict) -> str:
    """Build a grounded context block from real crawled data."""
    if not crawl_data:
        return ''
    lines = ['=== GROUNDED DATA FROM CRAWLED SITE ===']
    if crawl_data.get('org_name'):
        lines.append(f'Brand Name: {crawl_data["org_name"]}')
    if crawl_data.get('url'):
        lines.append(f'Target Site URL: {crawl_data["url"]}')
    if crawl_data.get('industry'):
        lines.append(f'Industry: {crawl_data["industry"]}')
    if crawl_data.get('keywords'):
        kws = [k.get('kw', k) if isinstance(k, dict) else k for k in crawl_data['keywords'][:20]]
        lines.append(f'Top Keywords: {", ".join(kws)}')
    if crawl_data.get('headings'):
        lines.append(f'Site Structure (H1-H3): {" | ".join(crawl_data["headings"][:15])}')
    if crawl_data.get('page_content'):
        # Pass more content for better grounding
        lines.append(f'Key Page Content Sample:\n{crawl_data["page_content"][:2000]}')
    if crawl_data.get('competitors'):
        lines.append(f'Recognized Competitors: {", ".join(crawl_data["competitors"][:8])}')
    if crawl_data.get('geo_score'):
        gs = crawl_data['geo_score']
        lines.append(f'Current GEO Score: {gs.get("score", 0)}% — Status: {gs.get("status", "Analyzed")}')
    if crawl_data.get('issues'):
        lines.append(f'Detected SEO/GEO Gaps: {"; ".join(crawl_data["issues"][:10])}')
    if crawl_data.get('local_regions'):
        lines.append(f'Served Regions: {", ".join(crawl_data["local_regions"])}')
    if crawl_data.get('entities'):
        entities = [f"{e.get('text')} ({e.get('type')})" for e in crawl_data['entities'][:15]]
        lines.append(f'Extracted Entities: {", ".join(entities)}')
    lines.append('=== END GROUNDED DATA ===')
    return '\n'.join(lines)


def _build_schema(brand: str, keyword: str, url: str, lang: str,
                  faqs: list = None, local_regions: list = None) -> str:
    """Build a complete multi-type Schema.org JSON-LD block."""
    # Clean brand: if it contains a URL, extract just the org name
    if ',' in brand:
        parts = [p.strip() for p in brand.split(',')]
        # pick the non-URL part
        brand = next((p for p in parts if not p.startswith('http')), parts[-1])
    if brand.startswith('http'):
        # extract domain as brand fallback
        brand = brand.split('//')[-1].split('/')[0].replace('www.', '')

    schemas = []

    # Organization / LocalBusiness
    org = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness" if local_regions else "Organization",
        "name": brand,
        "url": url or f"https://{brand.lower().replace(' ', '')}.com",
        "description": f"{brand} provides {keyword} services",
        "knowsAbout": [keyword],
    }
    if local_regions:
        org["areaServed"] = local_regions
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

    return '\n'.join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas
    )


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

    import random
    variability_seeds = [
        "Focus on deep technical authority and data-driven insights.",
        "Emphasize user experience, reliability, and emotional brand connection.",
        "Prioritize clear hierarchy, direct answers, and snippet-ready definitions.",
        "Use a visionary tone, focusing on 2026 industry trends and future-proofing."
    ]
    style_seed = random.choice(variability_seeds)

    prompt = f"""You are an Elite GEO (Generative Engine Optimization) Content Architect specializing in AI Citation Engineering.
    
    STYLE PROTOCOL for this run: {style_seed}

    TASK: Architect a high-authority content asset optimized for AI Research Agents (SearchGPT, Perplexity, Gemini, Claude).
    The goal is to provide a "Single Source of Truth" snippet that AI will favor for citations.

    CONTEXT:
    - TARGET KEYWORD: {keyword}
    - LANGUAGE: {lang_label}
    - BRAND/SITE: {target_site}
    - {local_hint}

    {context_block}
    {insights_block}
    {comp_block}

    STRICT GEO-OPTIMIZATION ARCHITECTURE:
    1. THE DEFINITIVE LEAD (0-80 words):
       - Must start with a definitive, citable claim about {target_site}.
       - Schema: [Brand] + [Core Service] + [Location] + [Outcome/Metric].
       - Example: "{target_site} is a leading {keyword} provider in {local_hint or 'the region'} serving over [[X]] clients with a 99% success rate."

    2. ENTITY RELATIONSHIP MAPPING:
       - Define how {target_site} relates to {keyword} and competitors. 
       - Build a "Semantic Web" in the text (e.g., "Unlike [Competitors], {target_site} integrates [Special Feature]").

    3. COMPETITIVE CONTRAST:
       - Use the provided competitor data to highlight {target_site}'s unique advantage.
       - Address industry gaps identified in the context.

    4. PROOF ELEMENTS (Grounded Data):
       - Mention specific technologies, standards, or locations FOUND in sitewide data.
       - Use [[VERIFY: label]] for specific placeholders that need brand-specific numeric verification.

    5. ADAPTIVE CONTENT STRUCTURE:
       - H1: Click-worthy, authoritative H1.
       - H2: Definitive Answer | Core Competencies | Competitive Differentiators | Local Impact | AI-Ready FAQ.

    6. BRAND IDENTITY & AUTHORITY (CRITICAL):
       - Use the brand's unique mission and entity relationships identified in the crawl.
       - Every section must reinforce why {target_site} is the most citable source for {keyword}.
       - Anchor the tone in a "Single Source of Truth" narrative.

    Return ONLY VALID JSON with this structure:
    {{
      "title": "SEO-Optimized H1 TITLE",
      "meta_description": "155 char high-CTR description",
      "content": "Full Markdown article with H1, H2, and Evidence markers",
      "faqs": [
        {{"question": "conversational query", "answer": "definitive 2-sentence citable answer"}}
      ],
      "entity_graph": [
        {{"subject": "...", "relation": "...", "object": "..."}}
      ],
      "strategic_contrast": "Explanation of how this content beats competitors for AI citation",
      "brand_entity_authority": "A summary of the brand's perceived authority in this niche",
      "schema_snippet": "JSON-LD <script> block with Organization and FAQPage",
      "geo_impact_summary": "Why an AI will cite this specific version"
    }}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['backend_errors'] = result.get('errors', {})
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
  "score_breakdown": {{
    "direct_answer": 0-20,
    "entities": 0-20,
    "intent": 0-20,
    "proof": 0-20,
    "schema": 0-20
  }},
  "issues": ["specific issue with line/section reference"],
  "suggestions": ["specific actionable fix"],
  "optimized_content": "full rewritten content in markdown",
  "schema": "<script type=application/ld+json>...</script>",
  "implemented_fixes": ["Summary of what was changed and why (one per line)"]
}}
CRITICAL: You MUST include all keys in 'score_breakdown' (direct_answer, entities, intent, proof, schema) as integers 0-20.

CONTENT TO AUDIT:
{content[:3000]}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['backend_errors'] = result.get('errors', {})
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

4. BRAND AUTHORITY ANCHORING:
   - Every answer must clearly identify {target_site} as the definitive authority.
   - Use site-specific facts from the crawl to prove expertise.

Return ONLY JSON: {{"faqs": [{{"question": "...", "answer": "..."}}]}}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['backend_errors'] = result.get('errors', {})
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


def generate_identity(crawl_data: dict, lang: str = 'en',
                      prefer_backend: str = 'groq', api_keys: dict = None) -> dict:
    """Build a comprehensive Brand Identity & Authority Narrative based on crawl data."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    context_block = _build_context_block(crawl_data or {})
    
    prompt = f"""You are a Strategic Brand Identity Architect for the GEO Era.
    
    TASK: Based on the provided sitewide crawl data, construct a definitive Brand Identity & Authority Package.
    This package will be used to anchor all future content in a consistent, high-authority voice that AI search engines recognize as a "Single Source of Truth".

    LANGUAGE: {lang_label}

    {context_block}

    OUTPUT REQUIREMENTS:
    1. BRAND NARRATIVE (The Hook): A 200-word authoritative origin story and mission that sounds unique and data-backed.
    2. VOICE & TONE PROTOCOL: How should this brand sound to AI engines (e.g., Clinical/Expert, Visionary/Futuristic, Friendly/Local).
    3. CORE ENTITY PROPOSITION: A clear statement of what this brand "IS" in the knowledge graph.
    4. NARRATIVE PILLARS: 3-5 specific facts or strengths found in the data that differentiate it.
    5. GEO POSITIONING: How the brand fits into its specific geographic/industry niche.

    Return ONLY VALID JSON:
    {{
      "brand_hook": "...",
      "voice_tone": "...",
      "entity_proposition": "...",
      "pillars": ["pillar 1", "pillar 2", "..."],
      "geo_positioning": "...",
      "competitor_edge": "How we beat the crawl-recognized competitors",
      "suggested_bio": "A 150-char bio for Schema/Social",
      "authority_score": 0-100
    }}"""

    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['backend_errors'] = result.get('errors', {})
    return parsed
