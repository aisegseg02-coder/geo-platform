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
        'model': os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620'),
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
    
    # Build dynamic intro from snippets if available
    intro_extra = ""
    if snippets:
        intro_extra = f"\n\nBased on your research: {snippets[0][:150]}..." if not is_arabic else f"\n\nبناءً على أبحاثك: {snippets[0][:150]}..."

    if 'generate' in prompt_lower and 'article' in prompt_lower:
        if is_arabic:
            return json.dumps({
                "title": f"دليل تحسين محركات البحث لـ {keyword}",
                "meta_description": f"تحسين ظهورك لـ {keyword} باستخدام استراتيجيات GEO متقدمة.",
                "content": f"## مقدمة\n{keyword} هو مفتاح النمو. {intro_extra}\n\n### استراتيجية المحتوى\nالتركيز على الصلة الدلالية يضمن بقاء {keyword} في الصدارة.\n\n### تحليل المنافسين\nاستخدمنا بياناتك لتحسين هذا النص برؤى فريدة.",
                "faqs": [{"question": f"لماذا {keyword} مهم؟", "answer": "لأنه يبني سلطة دلالية في مجالك."}]
            }, ensure_ascii=False)
        return json.dumps({
            "title": f"Strategic Guide for {keyword}",
            "meta_description": f"Master visibility for {keyword} with our GEO-powered content structure.",
            "content": f"## Introduction\n{keyword} optimization is essential. {intro_extra}\n\n### Semantic Strategy\nBy focusing on semantic depth, we ensure {keyword} resonates with AI crawlers.\n\n### Competitive Edge\nWe integrated your recent crawl data to ensure this content outperforms common templates.",
            "faqs": [{"question": f"Is {keyword} ready for AI search?", "answer": "Yes, this structure is citable by LLMs."}]
        })
    elif 'analyze' in prompt_lower:
        return json.dumps({
            "score": 92,
            "issues": [f"Density for '{keyword}' needs slight adjustment."],
            "suggestions": [f"Bold the term '{keyword}' in the first paragraph."],
            "optimized_content": "SMART DEMO: Content structurally improved based on your parameters."
        })
    return json.dumps({"faqs": [{"question": "Demo Question?", "answer": "Demo Answer."}]})


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

def generate_article(keyword: str, lang: str = 'en', competitors_content: list = None,
                     prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Generate a full GEO-optimized article. Returns {title, meta_description, content, faqs, backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    comp_block = ''
    if competitors_content:
        comp_block = 'Competitor content snippets for reference:\n' + '\n---\n'.join(competitors_content[:3])

    prompt = f"""You are an expert SEO/GEO content writer.
Target keyword: {keyword}
Language: {lang_label}
{comp_block}

Write a GEO-optimized article that:
1. Starts with a direct answer in the first 60 words
2. Uses the keyword naturally 3-5 times
3. Includes an FAQ section with 5 questions and answers
4. Uses H2/H3 heading structure (use ## and ### markers)
5. Is optimized for AI search citation

Return ONLY a valid, minified JSON object with no preamble or code blocks. Use escaped newlines (\n) for content. Keys:
- title (string)
- meta_description (string, max 160 chars)
- content (string, full article with markdown headings)
- faqs (array of {{question, answer}})
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    parsed['keyword'] = keyword
    parsed['lang'] = lang
    return parsed


def optimize_content(content: str, keyword: str, lang: str = 'en',
                     prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Analyze and optimize existing content for GEO. Returns {score, issues, optimized_content, suggestions, backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    prompt = f"""You are a GEO (Generative Engine Optimization) expert.
Language: {lang_label}
Target keyword: {keyword}

Analyze this content and return a JSON object with:
- score (0-100, GEO readiness)
- issues (array of strings describing problems)
- suggestions (array of actionable fixes)
- optimized_content (rewritten version of the content, improved for AI citation)

Content to analyze:
{content[:3000]}
"""
    result = _llm_call(prompt, prefer=prefer_backend, api_keys=api_keys)
    parsed = _parse_json_from_text(result['text'])
    parsed['backend'] = result['backend']
    return parsed


def generate_faqs(topic: str, page_content: str = '', lang: str = 'en',
                  count: int = 5, prefer_backend: str = 'ollama', api_keys: dict = None) -> dict:
    """Generate FAQ pairs for a topic. Returns {faqs: [{question, answer}], backend}."""
    lang_label = 'Arabic' if lang == 'ar' else 'English'
    context = f"\nPage context:\n{page_content[:1500]}" if page_content else ''
    prompt = f"""Generate {count} FAQ question-answer pairs about: {topic}
Language: {lang_label}{context}

Rules:
- Questions should be what users actually ask AI assistants
- Answers should be concise (2-4 sentences), factual, and citable
- Return ONLY a JSON object: {{"faqs": [{{"question": "...", "answer": "..."}}]}}
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
