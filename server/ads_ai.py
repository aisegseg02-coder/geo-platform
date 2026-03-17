"""
Ads AI Layer — AI-powered bidding suggestions, ad copy generation,
and negative keyword detection.
Backends (in priority order): Ollama (free/local) → Groq → OpenAI
"""
import json
import os
from typing import List, Dict, Optional

# ── Ollama (free, local) ───────────────────────────────────────────────────────
try:
    import ollama as _ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    _ollama = None
    OLLAMA_AVAILABLE = False

OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')

# ── Groq / OpenAI (cloud) ──────────────────────────────────────────────────────
try:
    from server import ai_analysis
except ImportError:
    ai_analysis = None


def _parse_json(text: str):
    """Extract first JSON object or array from a text response."""
    import re
    # try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip markdown fences
    clean = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
    try:
        return json.loads(clean)
    except Exception:
        pass
    # find first {...} or [...]
    for pattern in (r'(\[.*\])', r'(\{.*\})'):
        m = re.search(pattern, clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


def _call_ollama(prompt: str) -> Optional[str]:
    """Call local Ollama. Returns raw text or None."""
    if not OLLAMA_AVAILABLE:
        return None
    try:
        resp = _ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return resp['message']['content']
    except Exception as e:
        print(f'[AdsAI] Ollama error: {e}')
        return None


def _call_groq(prompt: str, api_key: str) -> Optional[str]:
    """Call Groq API. Returns raw text or None."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_completion_tokens=2048,
            stream=False
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f'[AdsAI] Groq error: {e}')
        return None


def _call_openai(prompt: str, api_key: str) -> Optional[str]:
    """Call OpenAI API. Returns raw text or None."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_tokens=2048
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f'[AdsAI] OpenAI error: {e}')
        return None


def _call_ai(prompt: str, api_keys: dict) -> Optional[str]:
    """
    Try backends in order: Ollama (free) → Groq → OpenAI.
    Returns raw text string or None.
    """
    # 1. Ollama — always try first (free, no key needed)
    text = _call_ollama(prompt)
    if text:
        return text
    # 2. Groq
    if api_keys and api_keys.get('groq'):
        text = _call_groq(prompt, api_keys['groq'])
        if text:
            return text
    # 3. OpenAI
    if api_keys and api_keys.get('openai'):
        text = _call_openai(prompt, api_keys['openai'])
        if text:
            return text
    return None


# ── 1. AI Bid Suggestions ──────────────────────────────────────────────────────
_DEMO_BID_SUGGESTIONS = [
    {"keyword": "تحسين محركات البحث", "current_cpc": 2.10, "suggested_cpc": 2.50,
     "action": "increase", "reason": "Quality Score 8 + 12 conversions — strong performer", "expected_impact": "+18% conversions"},
    {"keyword": "شركة سيو", "current_cpc": 1.60, "suggested_cpc": 1.80,
     "action": "increase", "reason": "Good QS 7 with steady conversions", "expected_impact": "+10% impression share"},
    {"keyword": "سيو عربي", "current_cpc": 0.95, "suggested_cpc": 0.65,
     "action": "decrease", "reason": "Low QS (6) and only 2 conversions — overbidding", "expected_impact": "-30% wasted spend"},
    {"keyword": "keyword ranking tool", "current_cpc": 1.20, "suggested_cpc": 0.0,
     "action": "pause", "reason": "QS 5 and zero conversions with $104 spend — bleeding budget", "expected_impact": "Save $104/month"},
    {"keyword": "SEO services Saudi Arabia", "current_cpc": 1.90, "suggested_cpc": 2.30,
     "action": "increase", "reason": "Highest QS (9), best converter — maximize exposure", "expected_impact": "+25% conversion volume"},
]


def ai_bid_suggestion(keyword_data: List[Dict], api_keys: dict = None) -> List[Dict]:
    """
    Analyze keyword performance and suggest bid adjustments.
    Returns list of action items: increase / decrease / pause / keep.
    """
    if not api_keys:
        return _DEMO_BID_SUGGESTIONS

    sample = keyword_data[:20]  # Limit for prompt size
    prompt = f"""
You are a Google Ads bidding expert. Analyze these keywords and suggest optimal CPC bid adjustments.

Keywords data:
{json.dumps(sample, ensure_ascii=False, indent=2)}

For EACH keyword return an object with:
- keyword: string
- current_cpc: number
- suggested_cpc: number (0 if pausing)
- action: "increase" | "decrease" | "pause" | "keep"
- reason: one sentence explaining why (in English or Arabic)
- expected_impact: brief expected outcome

Rules:
- QS < 4 → suggest pause
- 0 conversions + cost > $50 → pause
- CTR < 1.5% and 0 conversions → decrease 25%
- Conversions > 0 and QS >= 7 → increase 15-25%

Return ONLY a valid JSON array. No extra text.
"""
    res = _call_ai(prompt, api_keys)
    if res and res.get('result') and isinstance(res['result'], list):
        return res['result']
    return _DEMO_BID_SUGGESTIONS


# ── 2. Ad Copy Generator ───────────────────────────────────────────────────────
_DEMO_AD_COPY = {
    "headlines": [
        "خدمات السيو الاحترافية",
        "تصدر نتائج جوجل مع محرك",
        "نتائج مضمونة في 90 يوم",
        "سيو بالذكاء الاصطناعي",
        "زد زوار موقعك 3 أضعاف",
        "خبرة 10 سنوات في السيو العربي",
        "احصل على عملاء أكثر اليوم",
        "SEO للشركات السعودية",
        "استراتيجية سيو متكاملة",
        "ظهور في ChatGPT وجوجل",
    ],
    "descriptions": [
        "نحسن ظهور موقعك في جوجل وChatGPT. احصل على عملاء أكثر بتكلفة أقل.",
        "خبرة 10 سنوات في السيو العربي. استراتيجيات مثبتة للشركات السعودية.",
        "تحسين شامل — تقني، محتوى، روابط. نتائج قابلة للقياس.",
        "تواصل معنا الآن واحصل على تحليل مجاني لموقعك.",
    ],
    "display_path": ["سيو", "خدمات-احترافية"]
}


def generate_ad_copy(service_name: str, usp: str, target_audience: str,
                     lang: str = "ar", api_keys: dict = None) -> dict:
    """
    Generate Responsive Search Ad (RSA) copy.
    Returns headlines, descriptions, and display paths.
    """
    if not api_keys:
        return _DEMO_AD_COPY

    lang_label = "Arabic" if lang == "ar" else "English"
    prompt = f"""
Generate Google Ads Responsive Search Ad (RSA) copy.
Service: {service_name}
USP: {usp}
Target audience: {target_audience}
Language: {lang_label}

Rules:
- Headlines: max 30 characters EACH (this is a hard limit)
- Descriptions: max 90 characters EACH (hard limit)
- Include CTA in at least 2 headlines
- Include the main keyword/service naturally
- Be compelling and specific — avoid generic phrases

Return ONLY valid JSON in this exact format:
{{
  "headlines": ["h1", "h2", ... up to 15],
  "descriptions": ["d1", "d2", "d3", "d4"],
  "display_path": ["path1", "path2"]
}}
"""
    res = _call_ai(prompt, api_keys)
    if res and res.get('result') and isinstance(res['result'], dict):
        return res['result']
    return _DEMO_AD_COPY


# ── 3. Negative Keyword Detector ──────────────────────────────────────────────
_DEMO_NEGATIVES = {
    "negatives_exact": ["SEO salary", "SEO jobs", "learn SEO free", "SEO course"],
    "negatives_phrase": ["how to SEO", "SEO tutorial", "SEO book"],
    "keep_monitoring": ["SEO agency review", "SEO comparison"],
    "estimated_savings": "$180/month"
}


def detect_negative_keywords(search_terms_data: dict, api_keys: dict = None,
                              business_context: str = "B2B SEO/digital marketing in Saudi Arabia") -> dict:
    """
    Analyze search terms report and identify negatives to add.
    Returns exact negatives, phrase negatives, and estimated savings.
    """
    if not api_keys:
        return _DEMO_NEGATIVES

    wasted = search_terms_data.get('wasted_spend', [])
    if not wasted:
        return {"negatives_exact": [], "negatives_phrase": [], "keep_monitoring": [], "estimated_savings": "$0"}

    wasted_terms = [t.get("term", "") for t in wasted]
    wasted_spend = sum(t.get("clicks", 0) * t.get("avg_cpc", 0) for t in wasted)

    prompt = f"""
Analyze these search terms that triggered ads but got ZERO conversions.
Identify which ones are definitely irrelevant and should be added as negative keywords.

Business context: {business_context}

Wasted search terms:
{json.dumps(wasted_terms, ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "negatives_exact": ["term1", ...],
  "negatives_phrase": ["phrase1", ...],
  "keep_monitoring": ["term_to_watch", ...],
  "estimated_savings": "$X/month"
}}
"""
    res = _call_ai(prompt, api_keys)
    if res and res.get('result') and isinstance(res['result'], dict):
        result = res['result']
        result['estimated_savings'] = f"${round(wasted_spend, 2)}/period"
        return result
    return _DEMO_NEGATIVES


# ── 4. Weekly AI Performance Report ──────────────────────────────────────────
def generate_weekly_report(campaigns: list, keywords: list, search_terms: dict,
                            api_keys: dict = None, lang: str = "ar") -> str:
    """
    Generate a comprehensive AI weekly performance report.
    Returns markdown-formatted analysis text.
    """
    if not api_keys:
        return """## تقرير الأداء الأسبوعي — نموذج توضيحي

### ملخص الأداء
- إجمالي النقرات: **1,555 نقرة** (+12% عن الأسبوع الماضي)  
- إجمالي التحويلات: **46 تحويل** بمتوسط تكلفة **$60.5/تحويل**
- إجمالي الإنفاق: **$2,799** خلال آخر 30 يوم

### أبرز الإنجازات
✅ حملة "SEO Services SA" حققت أعلى نسبة تحويل (2.73%)  
✅ كلمة "SEO services Saudi Arabia" بجودة إعلان 9 — الأفضل أداءً  
✅ انخفاض تكلفة التحويل بنسبة 8% مقارنة بالشهر الماضي  

### المشاكل والفرص
⚠️ كلمة "keyword ranking tool" تستهلك $104 بدون أي تحويل → يُوصى بالإيقاف  
⚠️ نسبة ظهور حملة "Brand Keywords" منخفضة (41%) → زيادة الميزانية  
🔥 فرصة: كلمات السيو العربية تُحقق CPA أقل 30% من الإنجليزية

### التوصيات للأسبوع القادم
1. رفع عرض "تحسين محركات البحث" من $2.10 إلى $2.50
2. إيقاف كلمة "keyword ranking tool" فوراً (توفير $104)
3. إضافة كلمات سلبية: "وظائف سيو"، "تعلم سيو"، "كورس سيو"
4. تفعيل حملة Brand Keywords بميزانية $3/يوم

### الكلمات السلبية المقترحة
`SEO jobs` · `SEO salary` · `learn SEO free` · `سيو مجاني` · `كورس سيو`"""

    top_camps = campaigns[:3]
    top_kws = keywords[:10]
    wasted = search_terms.get('wasted_spend', [])[:5]
    lang_label = "Arabic" if lang == "ar" else "English"

    prompt = f"""
You are a Google Ads expert. Write a clear, actionable weekly performance report.
Language: {lang_label}

Campaign Performance:
{json.dumps(top_camps, ensure_ascii=False, indent=2)}

Top Keywords:
{json.dumps(top_kws, ensure_ascii=False, indent=2)}

Wasted Spend Terms (no conversions):
{json.dumps(wasted, ensure_ascii=False, indent=2)}

Write a professional report with these sections (use markdown, be specific with numbers):
1. ملخص الأداء / Performance Summary
2. أبرز الإنجازات / Key Wins  
3. المشاكل والفرص / Issues & Opportunities
4. التوصيات / Recommendations
5. الكلمات السلبية المقترحة / Suggested Negatives

Be specific. Use actual numbers from the data above.
"""
    res = _call_ai(prompt, api_keys)
    if res and isinstance(res.get('result'), str):
        return res['result']
    elif res and res.get('raw'):
        return res['raw']
    return "Report generation failed — check your API key."
