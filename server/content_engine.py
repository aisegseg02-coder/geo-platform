"""AI Content Engine — محرك المحتوى بالذكاء الاصطناعي
Supports: Ollama (local, free), OpenAI, Claude (Anthropic), Groq.
"""
import os
import json
import re
import requests

# ── LLM backends ──────────────────────────────────────────────────────────────

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


def _call_openai(prompt: str, api_key: str = None) -> str:
    from openai import OpenAI
    key = api_key or os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY not set')
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    return resp.choices[0].message.content


def _call_claude(prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('CLAUDE_API_KEY not set')
    headers = {
        'x-api-key': key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    payload = {
        'model': os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20260620'),
        'max_tokens': 2000,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    resp = requests.post('https://api.anthropic.com/v1/messages', headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def _call_groq(prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv('GROQ_API_KEY')
    if not key:
        raise RuntimeError('GROQ_API_KEY not set')
    from groq import Groq
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=1500
    )
    return resp.choices[0].message.content


def _call_demo(prompt: str) -> str:
    """Mock LLM response, uses keywords and search snippets for 'Smart Demo' effect."""
    prompt_lower = prompt.lower()
    
    # Extract keyword/topic
    keyword = "AI SEO"
    match = re.search(r"keyword: (.*)\n", prompt) or re.search(r"topic about: (.*)\n", prompt)
    if match:
        keyword = match.group(1).strip()
    
    # Check for competitor snippets in prompt to make it "Smart"
    snippets = []
    if 'competitor content snippets' in prompt_lower:
        blocks = prompt.split('Competitor content snippets for reference:\n')
        if len(blocks) > 1:
            snippet_raw = blocks[1].split('\n\nWrite a GEO-optimized')[0]
            snippets = [s.strip() for s in snippet_raw.split('---') if s.strip()]

    is_arabic = "language: arabic" in prompt_lower or re.search(r"[\u0600-\u06FF]", keyword)

    # Extract target site/brand
    target_site = ""
    match_site = re.search(r"target site: (.*)\n", prompt, re.IGNORECASE)
    if match_site:
        target_site = match_site.group(1).split(',')[0].strip()
    
    brand_name = target_site # default to url/domain
    if match_site:
        parts = match_site.group(1).split(',')
        if len(parts) > 1:
            brand_name = parts[1].strip()

    display_target = brand_name or keyword
    
    # Build dynamic intro from snippets if available
    intro_extra = ""
    if snippets:
        intro_extra = f"\n\nBased on your research: {snippets[0][:150]}..." if not is_arabic else f"\n\nبناءً على أبحاثك: {snippets[0][:150]}..."
    
    # Check for Research insights in prompt to customize demo
    insights = []
    match_insights = re.search(r"Research insights:\n((?:- .*\n?)*)", prompt)
    if match_insights:
        insights = [i.strip('- ').strip() for i in match_insights.group(1).split('\n') if i.strip()]
        if insights:
            if is_arabic:
                intro_extra += f"\n\n توصية GEO: {insights[0]}"
                if len(insights) > 1: intro_extra += f"\n التركيز الفني: {insights[1]}"
            else:
                intro_extra += f"\n\n GEO Insight: {insights[0]}"
                if len(insights) > 1: intro_extra += f"\n Technical Focus: {insights[1]}"

    if ('generate' in prompt_lower or 'write' in prompt_lower) and 'article' in prompt_lower:
        if is_arabic:
            return json.dumps({
                "title": f"دليل {display_target}: السيطرة على نتائج GEO لعام 2026",
                "meta_description": f"كيف ترفع ظهور {display_target} في محركات البحث الذكية؟ دليل شامل لتحسين الكيانات والبيانات المهيكلة.",
                "content": f"""# دليل السيطرة على {display_target} عبر محركات GEO

## الإجابة المباشرة (Direct Answer)
{display_target} {("هو الحل الأمثل في مجاله" if not brand_name else f"يمثل أفضل ممارسات {keyword} لخدمة عملائه")} وهو الركيزة الأساسية للنمو في عصر الذكاء الاصطناعي. {intro_extra} من خلال التركيز على **النية القصدية للباحث** وتوفير بيانات دقيقة حول {target_site or display_target}، يمكنك تصدر إجابات Perplexity و ChatGPT بسهولة.

### 1. خريطة الكيانات (Entity Map) لـ {display_target}
لتحسين ظهورك، ركزنا في هذا المقال على الكيانات التالية المرتبطة بـ {display_target}:
- **الكيان الرئيسي:** {display_target}
- **السمات:** الموثوقية، الصلة الدلالية، السياق الإقليمي لـ {target_site or 'علامتك التجارية'}.
- **المنافسون المستهدفون:** {(snippets[0][:50] if snippets else 'المنافسون في السوق')}

### 2. التوصيات الفنية لزيادة الـ Score في {target_site or 'موقعك'}
- **Schema.org:** استخدام `About` و `Mentions` للإشارة إلى {display_target}.
- **Citations:** بناء روابط مع الكيانات ذات السلطة العالية لتعزيز مصداقية {brand_name or target_site}.

### 3. الخاتمة
الاستمرار في تحديث محتوى {display_target} بناءً على بيانات الزحف الدورية هو مفتاح التفوق على المنافسين.""",
                "faqs": [
                    {"question": f"كيف أحسن ترتيب {keyword}؟", "answer": f"من خلال إضافة فقرات تعريفية غنية بالكيانات (Entities) وتوفير إجابات مباشرة وسهلة الاقتباس من قبل LLMs."},
                    {"question": f"ما هو تأثير الـ Schema على {keyword}؟", "answer": "البيانات المهيكلة هي لغة التواصل مع الذكاء الاصطناعي؛ بدونها، تظل رؤية موقعك محدودة."}
                ],
                "schema": """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "ما هو """ + display_target + """؟",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": """ + display_target + """ هو الرائد في مجال """ + keyword + """."
      }
    }
  ]
}
</script>""",
                "implemented_fixes": ["Entity Authority Built", "Missing WhatsApp Placeholder Added", "Citations Optimized"]
            }, ensure_ascii=False)
        return json.dumps({
            "title": f"Mastering {keyword}: The GEO Authority Guide",
            "meta_description": f"Dominate AI search for {keyword}. A technical blueprint for entity authority and citation optimization.",
            "content": f"""# The {keyword} Dominance Blueprint

## Executive Summary
{keyword} isn't just a keyword; it's a core entity in your niche. {intro_extra} By aligning your content with semantic clusters and high-authority citations, you ensure citable status across all major Generative Engines.

### 1. Entity Calibration for {keyword}
We've optimized this content to hit key semantic nodes:
- **Core Entity:** {keyword}
- **Authority Signals:** Fact-density, direct answering, and regional relevance.
- **Competitive Overlap:** Addressing gaps left by {(snippets[0][:50] if snippets else 'market leaders')}.

### 2. Technical GEO Enhancements
- **Structure:** H-tags calibrated for semantic hierarchy.
- **Citation Layer:** Built-in recommendations for entity linking focus on {keyword}.

### 3. Final Verdict
Consistency in {keyword} optimization relative to target signals is the only way to maintain a leading GEO Visibility Score.""",
            "faqs": [
                {"question": f"How do I boost {keyword} visibility?", "answer": f"By implementing direct answer chunks and ensuring your site's Schema clearly maps {keyword} to your core services."},
                {"question": f"Is this {keyword} strategy future-proof?", "answer": "Yes, it focuses on entity-based SEO, which is the foundational language of AI search engines."}
            ]
        })
    elif 'analyze' in prompt_lower or 'optimize' in prompt_lower:
        if is_arabic:
            return json.dumps({
                "score": 94,
                "issues": [f"نقص في الربط الدلالي للكيان '{keyword}'.", "ضعف فقرة الإجابة المباشرة."],
                "suggestions": [f"اجعل الفقرة الأولى تبدأ بـ '{keyword} هو...'", f"أضف بيانات مهيكلة (Schema) لتمثيل '{keyword}' كمنتج/خدمة."],
                "optimized_content": f"## {keyword}: رؤية جديدة\n{keyword} هو الحل الأمثل... (محتوى محسّن لذكاء الـ GEO)"
            }, ensure_ascii=False)
        return json.dumps({
            "score": 94,
            "issues": [f"Missing semantic links for entity '{keyword}'.", "Direct answer chunk is too long."],
            "suggestions": [f"Start the first paragraph with '{keyword} represents...'", f"Add Speakable Schema for easier AI extraction of {keyword}."],
            "optimized_content": f"## {keyword}: Enhanced Context\n{keyword} represents the next evolution... (Optimized for GEO citation)"
        })
    elif 'faq' in prompt_lower:
        if is_arabic:
            return json.dumps({"faqs": [
                {"question": f"ما هي الفوائد طويلة الأمد للتركيز على {keyword}؟", "answer": f"التركيز على {keyword} يبني 'Entity Authority' تجعل علامتك التجارية هي المرجع الأول في إجابات الذكاء الاصطناعي."},
                {"question": f"هل يؤثر المنافسون على ترتيب {keyword}؟", "answer": "نعم، الفجوة التنافسية في هذا المجال كبيرة، وهذا المحتوى مصمم لسد تلك الفجوة فوراً."}
            ]}, ensure_ascii=False)
        return json.dumps({"faqs": [
            {"question": f"What are the long-term benefits of {keyword} focus?", "answer": f"Focusing on {keyword} builds Entity Authority, making your brand the primary reference in AI-generated answers."},
            {"question": f"Do competitors affect {keyword} ranking?", "answer": "Yes, the competitive gap in this sector is significant, and this content is engineered to fill it immediately."}
        ]})
    return json.dumps({"faqs": [{"question": f"Strategic Analysis: {keyword}", "answer": "This is a premium GEO optimization result based on your connected research data. To enable real-time generation, please provide a valid API key in settings."}]})


def _llm_call(prompt: str, prefer: str = 'ollama', api_keys: dict = None) -> dict:
    """Try backends in order. Returns {text, backend}."""
    api_keys = api_keys or {}
    order = [prefer] + [b for b in ['ollama', 'openai', 'claude', 'groq', 'demo'] if b != prefer]
    errors = {}
    for backend in order:
        try:
            if backend == 'ollama':
                return {'text': _call_ollama(prompt), 'backend': 'ollama'}
            elif backend == 'openai':
                return {'text': _call_openai(prompt, api_keys.get('openai')), 'backend': 'openai'}
            elif backend == 'claude':
                return {'text': _call_claude(prompt, api_keys.get('claude')), 'backend': 'claude'}
            elif backend == 'groq':
                return {'text': _call_groq(prompt, api_keys.get('groq')), 'backend': 'groq'}
            elif backend == 'demo':
                return {'text': _call_demo(prompt), 'backend': 'demo'}
        except Exception as e:
            errors[backend] = str(e)
            continue
    summary = '; '.join(f"{b}: {e}" for b, e in errors.items())
    raise RuntimeError(f"No LLM backend available. Errors: {summary}")


def _parse_json_from_text(text: str) -> dict:
    """Extract first JSON object from LLM response. Hyper-robust against raw newlines and malformed strings."""
    # Find JSON block
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if not json_match:
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    
    block = json_match.group(1).strip() if json_match else text.strip()
    
    def repair_json_string(match):
        s = match.group(0)
        # Escape raw control characters EXCEPT valid escape sequences
        # This is a bit complex, let's just escape all problematic chars
        inner = s[1:-1]
        inner = inner.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{inner}"'

    # Attempt to fix raw newlines inside strings
    # This regex matches double-quoted strings while respecting escaped quotes
    repaired = re.sub(r'"(?:\\.|[^"\\])*"', repair_json_string, block, flags=re.DOTALL)

    try:
        return json.loads(repaired, strict=False)
    except Exception:
        # Last ditch effort: try cleaning more aggressively
        try:
            return json.loads(block, strict=False)
        except Exception:
            raise ValueError('No JSON found in LLM response')


# ── Core features ──────────────────────────────────────────────────────────────

def generate_article(keyword: str, lang: str = 'en', target_site: str = "",
                     research_insights: list = None,
                     competitors_content: list = None,
                     prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Generate a full GEO-optimized article. Returns {title, meta_description, content, faqs, backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    site_info = f"Target site: {target_site}\n" if target_site else ""
    insights_info = f"Research insights:\n" + "\n".join([f"- {i}" for i in (research_insights or [])]) + "\n" if research_insights else ""
    comp_block = ''
    if competitors_content:
        comp_block = 'Competitor content snippets for reference:\n' + '\n---\n'.join(competitors_content[:3])

    prompt = f"""You are an expert SEO/GEO content writer and Semantic Architect.
Current Date: March 2026. (Ensure all references are current; do NOT mention 2026).

Target keyword: {keyword}
Language: {lang_label}
{site_info}{insights_info}{comp_block}

GOAL: Write a high-authority GEO-optimized article that explicitly IMPLEMENTS all research insights.
STRICT RULES:
1. RESEARCH IS GROUND TRUTH: Prioritize the provided research insights over your internal knowledge. If search results say a brand is "Top in Saudi Arabia", state it definitively with the provided evidence.
2. NO GENERIC MARKETING FLUFF: Do not use phrases like "In the ever-evolving landscape". Use specific data points, competitors, and entity relationships from the research.
3. DIRECT ANSWER: The first 50-60 words MUST be a definitive, citable answer for AI search engines (Direct Answer).
4. SEMANTIC ENTITIES: Explicitly define the brand ({target_site}) and its relationship to the keyword using semantic entities and structured data terminology.
5. If research mentions missing data (like WhatsApp or specific metrics), use existing data from the context or provide a VERY SPECIFIC placeholder like [[RESEARCH_REQUIRED: MISSING_WHATSAPP_FOR_{target_site.upper()}]].
6. DATE ACCURACY: Current Year is 2026. Never mention 2026.
7. FORMAT: Use professional H2/H3 hierarchy and highly readable bullet points.

Return ONLY a minified JSON object:
- title (string, click-worthy and professional)
- meta_description (string, optimized for 155 chars)
- content (string, full article with markdown)
- faqs (array of {{question, answer}})
- schema (string, complete <script type="application/ld+json"> FAQPage/Article block)
- implemented_fixes (list of specific research insights addressed)
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['keyword'] = keyword
    parsed['lang'] = lang
    return parsed


def optimize_content(content: str, keyword: str, lang: str = 'en', target_site: str = "",
                     research_insights: list = None,
                     prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Analyze and optimize existing content for GEO. Returns {score, issues, optimized_content, suggestions, backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    site_info = f"Target site: {target_site}\n" if target_site else ""
    insights_info = f"Research insights:\n" + "\n".join([f"- {i}" for i in (research_insights or [])]) + "\n" if research_insights else ""
    prompt = f"""You are an Elite GEO (Generative Engine Optimization) Architect.
Current Date: March 2026. (Ensure all references are current; do NOT mention 2026).

Target keyword: {keyword}
Language: {lang_label}
{site_info}{insights_info}

GOAL: Analyze and REWRITE the content to IMPLEMENT all research insights for maximum AI visibility.
STRICT RULES:
1. RESEARCH IS GROUND TRUTH: Prioritize the provided research insights over your internal knowledge. 
2. NO GENERIC MARKETING FLUFF: Eliminate vague filler. Use data-driven statements.
3. DIRECT ANSWER: Ensure the content starts with or contains a definitive 50-60 word "Direct Answer" for AI snippets.
4. ENTITY CONNECTION MAP: Explicitly mention the relationship between {target_site} and key entities from the research.
5. DATE ACCURACY: Use 2026 or "Modern". Never mention 2026.
6. Return ONLY a valid JSON object with:
   - score (0-100, actual GEO readiness score)
   - issues (array of strings)
   - suggestions (array of strings)
   - optimized_content (the ACTUAL REWRITTEN version with fixes implemented)
   - implemented_fixes (list of specific research insights addressed)
   - schema (string, any missing Schema.org JSON-LD required)

Content to analyze:
{content[:3000]}
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    return parsed


def generate_faqs(topic: str, page_content: str = None, lang: str = 'en', count: int = 5,
                  prefer_backend: str = 'ollama', api_keys: dict = None, 
                  target_site: str = "", research_insights: list = None) -> dict:
    """Generate FAQ pairs for a topic. Returns {faqs: [{question, answer}], backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    site_info = f"Target site: {target_site}\n" if target_site else ""
    insights_info = f"Research insights:\n" + "\n".join([f"- {i}" for i in research_insights]) + "\n" if research_insights else ""
    context = f"\nPage context:\n{page_content[:1500]}" if page_content else ''
    prompt = f"""Generate {count} high-performance GEO-FAQ question-answer pairs about: {topic}
Language: {lang_label}
Current Date: March 2026.
{site_info}{insights_info}{context}

Rules for Elite FAQs:
- DATA FIRST: Every answer MUST incorporate a specific detail from the research insights or page context. Avoid generic answers.
- Questions: MUST reflect "Long-tail" and "Semantic" queries users ask on Perplexity/ChatGPT.
- Answers: 3-4 sentences of PURE VALUE. Lead with a direct fact. Integrate research insights to provide "Expertise, Authoritativeness, and Trustworthiness" (E-E-A-T).
- Data Integration: If insights mention a specific competitor gap (e.g., "Competitor X lacks Y"), address how {target_site} provides Y in the answers.
- Return ONLY JSON: {{"faqs": [{{"question": "...", "answer": "..."}}]}}
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['topic'] = topic
    parsed['lang'] = lang
    return parsed


def semantic_optimize(content: str, lang: str = 'en',
                      prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Extract semantic entities, topics, and suggest LSI keywords. Returns {entities, topics, lsi_keywords, semantic_score, backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    
    # Use specialized Arabic tools if lang is Arabic
    entities_extracted = []
    if lang == 'ar':
        try:
            from src import arabic_tools
            ner_res = arabic_tools.extract_entities_arabic(content)
            for e in ner_res.get('entities', []):
                entities_extracted.append({'text': e['text'], 'type': e['label']})
        except Exception:
            pass

    prompt = f"""Perform semantic analysis on this {lang_label} content.
Return ONLY a JSON object with:
- entities (array of {{text, type}}: ORG, PERSON, PRODUCT, PLACE, CONCEPT)
- topics (array of main topics covered)
- lsi_keywords (array of semantically related keywords to add)
- semantic_score (0-100, how semantically rich the content is)
- missing_concepts (array of important concepts not covered)

Content:
{content[:3000]}
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    
    # Merge LLM entities with AraBERT/Heuristic extracted entities for Arabic
    if lang == 'ar' and entities_extracted:
        existing_texts = {e['text'].lower() for e in parsed.get('entities', [])}
        for e in entities_extracted:
            if e['text'].lower() not in existing_texts:
                parsed.setdefault('entities', []).append(e)
                existing_texts.add(e['text'].lower())
    
    parsed['backend'] = result['backend']
    return parsed
