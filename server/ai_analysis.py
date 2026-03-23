import os
import json
import hashlib
from typing import List

try:
    import openai
except Exception:
    openai = None

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from langdetect import detect
except Exception:
    detect = None

if openai is not None:
    openai.api_key = os.getenv('OPENAI_API_KEY')

DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Professional Bilingual Recommendations
RECS_CONTENT = {
    'ar': {
        'headings': 'تحسين تسلسل العناوين: تأكد من وجود H1 واحد فقط واستخدام H2 ثم H3 بشكل منطقي لتسهيل الفهرسة.',
        'density': 'زيادة عمق المحتوى: استهدف 40-120 كلمة في الفقرات الرئيسية مع تقديم إجابات مباشرة وسهلة القراءة.',
        'entities': 'إضافة الكيانات المسماة: اذكر أسماء المنظمة، الأشخاص، والمنتجات بوضوح واربطها ببيانات Schema.',
        'faq': 'إنشاء صفحات الأسئلة والأجوبة (FAQ): أضف قسم للأسئلة الشائعة باستخدام JSON-LD لزيادة فرص الظهور في المحركات التوليدية.',
        'ai_visibility': 'تحسين الظهور في الذكاء الاصطناعي: أنشئ محتوى تعريفياً قصيراً (Definitional Content) يسهل على النماذج مثل ChatGPT وPerplexity اقتباسه.',
        'h1_missing': 'إضافة عنوان H1: أضف عنواناً رئيسياً واضحاً يحتوي على الكلمة المفتاحية واسم العلامة التجارية.',
        'short_paras': 'تطوير الفقرات: اجعل الفقرة الأولى تبدأ بإجابة مباشرة ومختصرة لزيادة احتمالية الاقتباس.',
        'thin_content': 'محتوى ضيق: أضف فقرات تعريفية وبيانات منظمة للمؤسسة (Organization Schema).',
        'critical_no_vis': {
            'title': ' Critical Issue: No AI Visibility',
            'why': 'Your brand is not recognized in AI answers',
            'fix': ['Add definition paragraph', 'Add FAQ', 'Add competitor comparison'],
            'impact': '+30% AI visibility',
            'tasks': [
                {'type': 'faq', 'label': 'توليد أسئلة FAQ ذكية', 'id': 'fix_faq'},
                {'type': 'generate', 'label': 'إنشاء نص تعريفي (Authority)', 'id': 'fix_def'},
                {'type': 'generate', 'label': 'مقارنة مع المنافسين', 'id': 'fix_comp'}
            ]
        },
        'summary_engine': {
            'current': 'SEO + Audit',
            'target': 'AI Growth Engine',
            'title': ' الخلاصة'
        },
        'top_5_additions': {
            'title': ' أهم 5 إضافات لازم تبدأ بيهم فورًا',
            'items': [
                'AI Citation Generator',
                'AI Query Coverage',
                'Competitor AI Gap',
                'Entity Authority Builder',
                'Predictive Impact Score'
                # These could also have IDs if we wanted to make them clickable later
            ]
        }
    },
    'en': {
        'headings': {'text': 'Fix heading hierarchy: Ensure one H1 per page and incremental H2 → H3 structure for better indexing.', 'task': 'optimize'},
        'density': {'text': 'Increase content depth: Aim for 40–120 words in core paragraphs with direct, readable answers.', 'task': 'optimize'},
        'entities': {'text': 'Add named entities: Clearly mention Organizations, People, and Products and link them via Schema.', 'task': 'semantic'},
        'faq': {'text': 'Create FAQ sections: Use FAQPage JSON-LD to increase chances of being featured in AI search results.', 'task': 'faq'},
        'ai_visibility': {'text': 'Optimize for AI: Create short, authoritative definitions of your services to encourage LLM citations.', 'task': 'generate'},
        'h1_missing': 'Add H1 heading: Ensure a clear H1 containing your primary keyword and brand name.',
        'short_paras': 'Expand paragraphs: Lead with a one-sentence "direct answer" to improve AI extraction likelihood.',
        'thin_content': 'Thin content: Add a definitional paragraph and an Organization JSON-LD block.',
        'critical_no_vis': {
            'title': ' Summary'
        },
        'top_5_additions': {
            'title': ' Top 5 Additions to Start Immediately',
            'items': [
                'AI Citation Generator',
                'AI Query Coverage',
                'Competitor AI Gap',
                'Entity Authority Builder',
                'Predictive Impact Score'
            ]
        }
    }
}

def _is_arabic(text: str) -> bool:
    if not text: return False
    # Simple regex for Arabic characters range
    import re
    return bool(re.search(r'[\u0600-\u06FF]', text))


def _build_prompt(pages: List[dict]):
    lines = []
    for p in pages:
        title = p.get('title') or p.get('url')
        first_para = (p.get('paragraphs') or [None])[0] or ''
        lines.append(f"TITLE: {title}\nURL: {p.get('url')}\nTEXT: {first_para}\n---")
    return "\n".join(lines)


def _cache_key_for_prompt(prompt: str, prefix: str = 'openai') -> str:
    return f"{prefix}:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}"


def analyze_with_openai(pages: List[dict], api_key: str = None):
    key = api_key or os.getenv('OPENAI_API_KEY')
    if not key:
        return { 'enabled': False, 'reason': 'OPENAI_API_KEY not set' }

    prompt_content = _build_prompt(pages)
    system = (
        "You are an analytics assistant. Given crawled pages (title, url, text),"
        " produce a JSON object with keys: summary (one-paragraph), topics (array of top 6 topics),"
        " geo_features (array of suggested GEO-specific features to extract), suggestions (array of action items),"
        " and sentiment {score:-1..1}. Return ONLY valid JSON."
    )

    messages = [
        { 'role': 'system', 'content': system },
        { 'role': 'user', 'content': prompt_content }
    ]

    # check cache
    try:
        from server import cache
        ckey = _cache_key_for_prompt(prompt_content, 'openai_analyze')
        cached = cache.get(ckey)
        if cached is not None:
            return { 'enabled': True, 'result': cached, 'cached': True }
    except Exception:
        cached = None

    try:
        # retry OpenAI calls on transient errors
        try:
            from server import utils
        except Exception:
            utils = None

        def _call_openai():
            return openai.ChatCompletion.create(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )

        if utils is not None:
            resp = utils.retry(attempts=3, backoff_base=1.0)(_call_openai)()
        else:
            resp = _call_openai()
        
        # Use robust parsing (lazily imported to avoid circularity if needed, 
        # but content_engine is already in same package)
        try:
            from server.content_engine import _parse_json_from_text
            text = resp['choices'][0]['message']['content']
            parsed = _parse_json_from_text(text)
            try:
                from server import cache
                cache.set(ckey, parsed)
            except Exception: pass
            return { 'enabled': True, 'result': parsed }
        except Exception as e:
            return { 'enabled': True, 'raw': resp['choices'][0]['message']['content'], 'parse_error': str(e) }
    except Exception as e:
        return { 'enabled': True, 'error': str(e) }


def analyze_with_groq(pages: List[dict], api_key: str = None):
    if Groq is None:
        return { 'enabled': False, 'reason': 'groq client not installed' }

    # Initialize client
    groq_key = api_key or os.getenv('GROQ_API_KEY')
    if not groq_key:
        return { 'enabled': False, 'reason': 'GROQ_API_KEY not set' }
    try:
        client = Groq(api_key=groq_key)
    except Exception as e:
        return { 'enabled': False, 'reason': f'failed to init Groq client: {e}' }

    prompt = _build_prompt(pages)
    try:
        from server import cache
        ckey = _cache_key_for_prompt(prompt, 'groq_analyze')
        cached = cache.get(ckey)
        if cached is not None:
            return { 'enabled': True, 'result': cached, 'cached': True }
    except Exception:
        cached = None
    try:
        # attempt with retry wrapper when available
        try:
            from server import utils
        except Exception:
            utils = None

        def _call_groq():
            return client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
                messages=[{'role':'system','content':'You are an analytics assistant producing JSON output.'},
                          {'role':'user','content':prompt}],
                temperature=0.2,
                max_completion_tokens=2048,
                stream=False
            )

        if utils is not None:
            completion = utils.retry(attempts=3, backoff_base=1.0)(_call_groq)()
        else:
            completion = _call_groq()
        # completion may be a streaming iterator or a final object depending on client
        # Attempt to get textual content
        text = None
        if hasattr(completion, '__iter__') and not isinstance(completion, (str, bytes)):
            # join streamed pieces
            parts = []
            for chunk in completion:
                try:
                    # Ensure delta and content are not None before accessing
                    content_part = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ''
                    parts.append(content_part)
                except Exception:
                    # fallback: str(chunk)
                    parts.append(str(chunk))
            text = ''.join(parts)
        else:
            try:
                text = completion.choices[0].message.content
            except Exception:
                text = str(completion)

        if not text:
            return { 'enabled': True, 'raw': str(completion) }

        try:
            from server.content_engine import _parse_json_from_text
            parsed = _parse_json_from_text(text)
            try:
                from server import cache
                cache.set(ckey, parsed)
            except Exception: pass
            return { 'enabled': True, 'result': parsed }
        except Exception as e:
            return { 'enabled': True, 'raw': text, 'parse_error': str(e) }
    except Exception as e:
        return { 'enabled': True, 'error': str(e) }


def analyze_pages(pages: List[dict], api_keys: dict = None):
    api_keys = api_keys or {}
    out = { 'openai': analyze_with_openai(pages, api_key=api_keys.get('openai')) }
    groq_res = analyze_with_groq(pages, api_key=api_keys.get('groq'))
    out['groq'] = groq_res
    return out


def compute_geo_score(pages: List[dict], audit: dict = None, ai_visibility: dict = None):
    """
    Compute a simple GEO visibility score (0-100) from pages, optional audit dict and ai_visibility results.
    Heuristic-based scoring:
      - headings structure (20)
      - paragraph density (20)
      - named entities presence (20)
      - FAQ/schema signals (20)
      - AI visibility mentions (20)
    Returns dict with score, status, and breakdown.
    """
    total_pages: int = max(1, len(pages))
    headings_ok_count: int = 0
    density_scores: List[float] = []
    entity_counts: int = 0
    faq_count: int = 0

    for p in pages:
        if p.get('headings'):
            # headings_ok heuristic: presence of an H1 and not skipping levels
            # where audit may contain headings_ok, but pages don't; we check tags
            tags = [h.get('tag','') for h in p.get('headings', [])]
            if 'h1' in tags:
                headings_ok_count += 1

        dens = 0
        paras = p.get('paragraphs', [])
        if paras:
            avg = sum(len(x.split()) for x in paras) / len(paras)
            # ideal avg words between 40 and 200
            if avg >= 40 and avg <= 200:
                dens = 1.0
            else:
                dens = min(1.0, avg/40.0)
        density_scores.append(dens)

        # entities
        # check if audit provided entities summary
        # fallback: 0
        # assume audit structure contains 'entities' per page if provided
        # we'll try to find in audit dict
        try:
            # audit may have audits list matching pages
            if audit and 'audits' in audit:
                for a in audit.get('audits', []):
                    if a.get('url') == p.get('url'):
                        ents = a.get('entities', {}).get('entities') if isinstance(a.get('entities', {}), dict) else a.get('entities')
                        if ents:
                            entity_counts += len(ents)
                        break
        except Exception:
            pass

        # faq heuristic: look for h3 headings paired with paragraphs
        for h in p.get('headings', []):
            if h.get('tag') == 'h3' and paras:
                faq_count += 1

    headings_score = float(headings_ok_count / total_pages) * 20.0
    density_score = float(sum(density_scores) / total_pages) * 20.0
    entity_score = (20.0 if entity_counts > 0 else 0.0)
    faq_score = float(min(faq_count, total_pages) / total_pages) * 20.0

    # AI visibility: compute mention ratio from ai_visibility results if present
    ai_score = 0.0
    if ai_visibility and ai_visibility.get('enabled') and ai_visibility.get('results'):
        res = ai_visibility.get('results')
        mentions = sum(1 for r in res if r.get('mentioned'))
        ai_score = (mentions / max(1, len(res))) * 20

    raw_score = headings_score + density_score + entity_score + faq_score + ai_score
    score = int(round(raw_score))

    status = 'Good' if score >= 75 else ('Needs Work' if score >= 40 else 'Critical')

    # simple counts for UI
    critical_issues = 0
    warnings = 0
    passed = 0
    for p in pages:
        paras = p.get('paragraphs', [])
        avg = (sum(len(x.split()) for x in paras) / len(paras)) if paras else 0
        if not p.get('headings') or avg < 20:
            critical_issues += 1
        elif avg < 40:
            warnings += 1
        else:
            passed += 1

    return {
        'score': score,
        'status': status,
        'breakdown': {
            'headings': int(round(headings_score)),
            'density': int(round(density_score)),
            'entities': int(round(entity_score)),
            'faq': int(round(faq_score)),
            'ai_visibility': int(round(ai_score))
        },
        'counts': {
            'critical': critical_issues,
            'warnings': warnings,
            'passed': passed
        }
    }


def infer_brand_name(pages: List[dict]) -> str:
    """
    Robustly extract brand name using multiple strategies:
    1. Explicit org_name from metadata
    2. og:site_name / meta title from HTML
    3. H1 heading from the first page
    4. Page title (before separator)
    5. Domain name from URL (cleaned up)
    """
    if not pages:
        return "Company"

    for page in pages[:5]:  # Check up to first 5 pages
        # Strategy 1: Check for og:site meta
        meta = page.get('meta', {}) or {}
        og_site = meta.get('og:site_name') or meta.get('application-name')
        if og_site and og_site.lower() not in ('company', 'website', 'home'):
            return og_site.strip()

        # Strategy 2: H1 headings (most reliable)
        for h in page.get('headings', []):
            if h.get('tag') == 'h1':
                txt = h.get('text', '').strip()
                if txt and len(txt) < 60 and txt.lower() not in ('home', 'welcome', 'company'):
                    return txt

        # Strategy 3: Page title before separator
        if page.get('title'):
            title_str = str(page.get('title') or '').strip()
            # Split on common separators: |, -, —, »
            import re
            parts = re.split(r'[\|\-—»]', title_str)
            title = parts[0].strip()
            if title and len(title) < 60 and title.lower() not in ('home', 'welcome', 'company', 'homepage'):
                return title

    # Strategy 4: Extract brand from URL domain (e.g. moharek.com → Moharek)
    first_url = pages[0].get('url', '') if pages else ''
    if first_url:
        try:
            from urllib.parse import urlparse
            import re
            parsed = urlparse(first_url)
            domain = parsed.netloc or parsed.path
            # Strip www. and TLD
            domain_clean = re.sub(r'^www\.', '', domain)
            domain_clean = re.sub(r'\.[a-z]{2,}$', '', domain_clean)
            domain_clean = domain_clean.replace('-', ' ').replace('_', ' ').strip()
            if domain_clean and len(domain_clean) > 1:
                return domain_clean.title()  # Capitalize each word
        except Exception:
            pass

    return "Company"


def generate_recommendations(pages: List[dict], geo_score: dict = None, api_keys: dict = None, ai_analysis_results: dict = None):
    """
    Produce actionable recommendations and example schema snippets based on pages and GEO score breakdown.
    Prioritizes results from AI analysis (OpenAI/Groq) if provided.
    """
    api_keys = api_keys or {}
    recs = {'actions': [], 'per_page': []}

    # Use AI-driven global suggestions if available
    if ai_analysis_results:
        # Look into groq or openai result
        ai_res = None
        if ai_analysis_results.get('groq', {}).get('result'):
            ai_res = ai_analysis_results['groq']['result']
        elif ai_analysis_results.get('openai', {}).get('result'):
            ai_res = ai_analysis_results['openai']['result']
        
        if ai_res and ai_res.get('suggestions'):
            recs['actions'] = ai_res.get('suggestions') or []
    
    # Detect dominant language - Safely handle empty paragraphs
    is_ar = False
    for p in pages[:3]:
        paras = p.get('paragraphs') or []
        sample_text = p.get('title', '') + ' ' + (paras[0] if paras else '')
        if _is_arabic(sample_text):
            is_ar = True
            break
    lang = 'ar' if is_ar else 'en'
    content = RECS_CONTENT[lang]

    # Fallback/Heuristic actions if AI didn't provide any or as supplements
    if not recs['actions'] and geo_score:
        b = geo_score.get('breakdown', {})
        if b.get('headings', 0) < 12:
            recs['actions'].append(content['headings'])
        if b.get('density', 0) < 12:
            recs['actions'].append(content['density'])
        if b.get('entities', 0) < 10:
            recs['actions'].append(content['entities'])
        if b.get('faq', 0) < 10:
            recs['actions'].append(content['faq'])
        if b.get('ai_visibility', 0) < 10:
            recs['actions'].append(content['ai_visibility'])
            # Inject new rich recommendations
            recs['critical_issue'] = content['critical_no_vis']
            recs['summary_engine'] = content['summary_engine']
            recs['top_additions'] = content['top_5_additions']

    # Per-page recommendations
    for p in pages:
        page_rec = {'url': p.get('url'), 'title': p.get('title'), 'issues': [], 'suggestions': [], 'schema_example': None}
        tags = [h.get('tag','') for h in p.get('headings', [])]
        if 'h1' not in tags:
            page_rec['issues'].append('Missing H1' if lang == 'en' else 'عنوان H1 مفقود')
            page_rec['suggestions'].append(content['h1_missing'])
        # paragraph length
        paras = p.get('paragraphs', [])
        avg = (sum(len(x.split()) for x in paras) / len(paras)) if paras else 0
        if avg < 30:
            page_rec['issues'].append('Short paragraphs' if lang == 'en' else 'فقرات قصيرة جداً')
            page_rec['suggestions'].append(content['short_paras'])

        # FAQ suggestion: collect h3 candidate - Improved cleaning
        import re
        faq_candidates = [h['text'].strip() for h in p.get('headings', []) if h.get('tag') == 'h3']
        valid_q = None
        for q in faq_candidates:
            # Avoid headings that are obviously UI elements or too long/short
            if len(q) > 10 and len(q) < 100 and not q.startswith('[') and not q.endswith(']'):
                valid_q = q
                break

        if valid_q:
            ans = (paras[0] if paras else '')[:300]
            schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": valid_q,
                        "acceptedAnswer": { "@type": "Answer", "text": ans }
                    }
                ]
            }
            page_rec['schema_example'] = schema
            page_rec['suggestions'].append('Add the FAQ JSON-LD for the question above to improve AI extraction.' if lang == 'en' else 'أضف بيانات FAQ JSON-LD للسؤال أعلاه لتحسين استخلاص الإجابة بالذكاء الاصطناعي.')

        # Entities hint
        if not p.get('headings') and not paras:
            page_rec['issues'].append('Thin content' if lang == 'en' else 'محتوى ضعيف')
            page_rec['suggestions'].append(content['thin_content'])

        # AI Rewrite: Use the common LLM chain logic
        if (api_keys.get('openai') or api_keys.get('groq') or os.getenv('OPENAI_API_KEY') or os.getenv('GROQ_API_KEY')) and paras:
            try:
                # We reuse the _llm chain from geo_services if possible, 
                # but to avoid circularity we'll define a simple request here or rely on analyze_with_openai
                prompt = (
                    f"Rewrite this Arabic/English paragraph for AI Search Optimization (ASO). "
                    f"Make it authoritative, lead with a direct definition, and include the brand name. "
                    f"Return ONLY the rewritten text. TEXT: {paras[0][:800]}"
                )
                
                # Check for Groq first (free/fast)
                rewrite = ""
                key = api_keys.get('groq') or os.getenv('GROQ_API_KEY')
                if key:
                   res = analyze_with_groq([{ 'url': p.get('url'), 'title': p.get('title'), 'paragraphs': [prompt] }], api_key=key)
                   if res.get('raw') and isinstance(res['raw'], str): 
                       rewrite = res['raw']
                   elif res.get('result'):
                       # If it parsed as a dict but we wanted a string, extract the summary/rewrite if possible
                       if isinstance(res['result'], dict):
                           rewrite = res['result'].get('summary') or res['result'].get('rewrite') or str(res['result'])
                       else:
                           rewrite = str(res['result'])

                if not rewrite:
                   key = api_keys.get('openai') or os.getenv('OPENAI_API_KEY')
                   if key:
                       res = analyze_with_openai([{ 'url': p.get('url'), 'title': p.get('title'), 'paragraphs': [prompt] }], api_key=key)
                       if res.get('raw') and isinstance(res['raw'], str):
                           rewrite = res['raw']
                       elif res.get('result'):
                           if isinstance(res['result'], dict):
                               rewrite = res['result'].get('summary') or res['result'].get('rewrite') or str(res['result'])
                           else:
                               rewrite = str(res['result'])

                # Final cleanup: If we still have a tuple-like string (due to str() on a message object)
                if rewrite and ("ChatCompletionMessage" in rewrite or "choices=" in rewrite):
                    # Attempt to extract content via regex if LLM returned a raw object representation
                    import re
                    match = re.search(r"content=['\"](.*?)['\"]", rewrite, re.DOTALL)
                    if match: rewrite = match.group(1)
                
                if rewrite and len(rewrite) > 10:
                    label = "AI ASO Rewrite" if lang == 'en' else "اقتراح إعادة صياغة لتحسين الظهور (ASO)"
                    page_rec['suggestions'].append({'rewrite': rewrite.strip(), 'label': label})
            except Exception:
                pass

        recs['per_page'].append(page_rec)

    return recs
