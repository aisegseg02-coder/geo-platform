"""
GEO Services — 6 AI Visibility services using free tools:
1. Visibility Score (Ollama + Perplexity + OpenRouter)
2. Brand Recognition (spaCy NER + difflib + Ollama)
3. Sentiment Analysis (Groq/Ollama LLM scoring)
4. Competitor Ranking (multi-model Ollama)
5. Geo-Regional Analysis (dialect-aware queries)
6. Fix Recommendations + Simulator (Ollama + BeautifulSoup)
"""
import os
import json
import requests
import datetime
import sqlite3
import re
import difflib
import statistics
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv() # Load from .env file

# ── Ollama helper ──────────────────────────────────────────────────────────────
def _ollama_chat(prompt: str, model: str = "llama3", json_mode: bool = False) -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"
    try:
        r = requests.post(f"{host}/api/chat", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        return ""


def _openrouter_chat(prompt: str, model: str = "openai/gpt-4o-mini", api_key: str = None) -> str:
    """OpenRouter free tier — GPT-4o-mini or google/gemini-flash-1.5."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://geo-platform.app",
                "X-Title": "GEO Platform",
            },
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return ""


def _openai_chat(prompt: str, model: str = "gpt-4o-mini", api_key: str = None) -> str:
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1024
            },
            timeout=30
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return ""


def _groq_chat(prompt: str, api_key: str = None) -> str:
    key = api_key or os.environ.get("GROQ_API_KEY", "")
    if not key:
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=1024
        )
        return resp.choices[0].message.content
    except Exception:
        return ""


# ── LLM Chain (Ollama -> OpenAI -> Groq -> OpenRouter) ──────────────────────────
def _llm(prompt: str, api_keys: dict = None, json_mode: bool = False) -> str:
    api_keys = api_keys or {}
    errors = []

    # 1. Local Ollama (Fastest, Free)
    try:
        res = _ollama_chat(prompt, model="qwen2", json_mode=json_mode)
        if res: return res
    except Exception as e:
        errors.append(f"Ollama Error: {e}")

    # 2. OpenAI Cloud Fallback
    openai_key = api_keys.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            res = _openai_chat(prompt, api_key=openai_key)
            if res: return res
            else: errors.append("OpenAI: Returned empty (Check Quota/429)")
        except Exception as e:
            errors.append(f"OpenAI Exception: {e}")
    else:
        errors.append("OpenAI: Key missing in .env")

    # 3. Groq Fallback
    groq_key = api_keys.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            res = _groq_chat(prompt, api_key=groq_key)
            if res: return res
        except Exception as e:
            errors.append(f"Groq Error: {e}")
    else:
        errors.append("Groq: Key missing in .env")

    # 4. OpenRouter Fallback
    router_key = api_keys.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if router_key:
        try:
            res = _openrouter_chat(prompt, api_key=router_key)
            if res: return res
        except Exception as e:
            errors.append(f"OpenRouter Error: {e}")
    else:
        errors.append("OpenRouter: Key missing in .env")

    # If all failed, return special error signal
    log_msg = " | ".join(errors)
    print(f"LLM FAILURE: {log_msg}") # Server-side visibility
    return f"ERROR: No LLM available. Details: {log_msg}"


def _serp_api_search(query: str, location: str = "Saudi Arabia", api_key: str = None) -> dict:
    """Fetches real search results via SerpApi."""
    key = api_key or os.environ.get("SERPAPI_KEY", "b31a84f7e45cc6c60f6de3627bf6650a81e0263fe67d939420308c4815b66cb7")
    if not key:
        return {}
    try:
        r = requests.get("https://serpapi.com/search", params={
            "q": query,
            "location": location,
            "hl": "ar",
            "gl": "sa",
            "google_domain": "google.com.sa",
            "api_key": key
        }, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"SerpApi Error: {e}")
        return {}


def _zenserp_search(query: str, location: str = "Saudi Arabia", api_key: str = None) -> dict:
    """Fetches real search results via ZenSerp."""
    key = api_key or os.environ.get("ZENSERP_KEY", "a50d7a20-2698-11f1-a47e-edf101aaf1cf")
    if not key:
        return {}
    try:
        r = requests.get("https://app.zenserp.com/api/v2/search", params={
            "q": query,
            "location": location,
            "hl": "ar",
            "gl": "sa",
            "apikey": key
        }, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"ZenSerp Error: {e}")
        return {}


def _parse_json(text: str) -> dict:
    import re
    text = text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 1 — Unified Visibility Score
# ══════════════════════════════════════════════════════════════════════════════
def visibility_score(brand: str, queries: List[str], api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    results = []

    for q in queries:
        prompt = q
        answer = _llm(prompt, api_keys)
        if not answer:
            continue
        mentioned = brand.lower() in answer.lower()
        results.append({"query": q, "mentioned": mentioned, "answer": answer[:200]})

    # Also try Perplexity if key available
    perp_key = api_keys.get("perplexity") or os.environ.get("PERPLEXITY_KEY", "")
    if perp_key:
        for q in queries[:3]:
            try:
                r = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={"Authorization": f"Bearer {perp_key}", "Content-Type": "application/json"},
                    json={"model": "sonar", "messages": [{"role": "user", "content": q}]},
                    timeout=20
                )
                answer = r.json()["choices"][0]["message"]["content"]
                mentioned = brand.lower() in answer.lower()
                results.append({"query": q, "mentioned": mentioned, "model": "perplexity-sonar", "answer": answer[:200]})
            except Exception:
                pass

    if not results:
        return {"brand": brand, "visibility_score": 0, "mentions": 0, "total_queries": 0, "grade": "F", "results": [], "error": "No LLM available"}

    total = len(results)
    mentions = sum(1 for r in results if r.get("mentioned"))
    score = round((mentions / total) * 100, 1)
    grade = "A" if score > 70 else "B" if score > 50 else "C" if score > 30 else "D"

    return {
        "brand": brand,
        "visibility_score": score,
        "mentions": mentions,
        "total_queries": total,
        "grade": grade,
        "results": results
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 2 — Brand Recognition
# ══════════════════════════════════════════════════════════════════════════════
def brand_recognition(brand: str, brand_variants: List[str], queries: List[str], api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    results = []

    # Try spaCy NER
    nlp = None
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            try:
                nlp = spacy.load("xx_ent_wiki_sm")
            except Exception:
                pass
    except Exception:
        pass

    for q in queries:
        answer = _llm(q, api_keys)
        if not answer:
            continue

        # 1. Exact match
        exact = any(v.lower() in answer.lower() for v in brand_variants)

        # 2. Fuzzy match
        words = answer.split()
        fuzzy_matches = []
        for word in words:
            for variant in brand_variants:
                ratio = difflib.SequenceMatcher(None, word.lower(), variant.lower()).ratio()
                if ratio > 0.8:
                    fuzzy_matches.append({"word": word, "variant": variant, "ratio": round(ratio, 2)})

        # 3. OpenRouter cross-check (GPT-4o-mini + Gemini Flash)
        or_key = (api_keys or {}).get("openrouter") or os.environ.get("OPENROUTER_API_KEY", "")
        openrouter_mentions = []
        if or_key:
            for or_model in ["openai/gpt-4o-mini", "google/gemini-flash-1.5"]:
                or_answer = _openrouter_chat(q, model=or_model, api_key=or_key)
                if or_answer:
                    openrouter_mentions.append({
                        "model": or_model,
                        "mentioned": any(v.lower() in or_answer.lower() for v in brand_variants),
                        "answer": or_answer[:150]
                    })

        # 4. NER
        brand_as_org = False
        if nlp:
            try:
                doc = nlp(answer[:500])
                org_entities = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                brand_as_org = any(
                    any(v.lower() in org.lower() for v in brand_variants)
                    for org in org_entities
                )
            except Exception:
                pass

        or_recognized = any(m["mentioned"] for m in openrouter_mentions) if openrouter_mentions else False
        consistency = sum([exact, brand_as_org, bool(fuzzy_matches), or_recognized]) / 4
        results.append({
            "query": q,
            "exact_match": exact,
            "fuzzy_matches": fuzzy_matches[:3],
            "recognized_as_org": brand_as_org,
            "openrouter_checks": openrouter_mentions,
            "consistency_score": round(consistency, 2)
        })

    if not results:
        return {"brand": brand, "avg_consistency": 0, "results": [], "error": "No LLM available"}

    avg = sum(r["consistency_score"] for r in results) / len(results)
    return {
        "brand": brand,
        "avg_consistency": round(avg * 100, 1),
        "results": results
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 3 — Sentiment Analysis
# ══════════════════════════════════════════════════════════════════════════════
def sentiment_analysis(brand: str, queries: List[str], api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    sentiment_results = []

    for q in queries:
        answer = _llm(q, api_keys)
        if not answer:
            continue

        sentences = [s.strip() for s in answer.split('.') if brand.lower() in s.lower()]
        if not sentences:
            continue

        prompt = f"""Analyze the sentiment toward the brand "{brand}" in this text:
"{' '.join(sentences[:3])}"

Return JSON only:
{{
  "polarity": "positive|neutral|negative",
  "score": 0.0,
  "trust_level": "high|medium|low",
  "tone": "authoritative|casual|skeptical|promotional",
  "key_phrases": [],
  "summary": "one sentence summary"
}}"""
        raw = _llm(prompt, api_keys, json_mode=True)
        analysis = _parse_json(raw) if raw else {"polarity": "neutral", "score": 0.5, "trust_level": "medium", "tone": "casual", "key_phrases": [], "summary": ""}

        sentiment_results.append({
            "query": q,
            "brand_sentences": sentences[:2],
            "analysis": analysis
        })

    if not sentiment_results:
        return {"brand": brand, "avg_sentiment_score": 0, "overall_tone": "Unknown", "details": [], "error": "No LLM available"}

    scores = [r["analysis"].get("score", 0.5) for r in sentiment_results]
    avg = sum(scores) / len(scores)

    return {
        "brand": brand,
        "avg_sentiment_score": round(avg * 100, 1),
        "overall_tone": "إيجابي" if avg > 0.6 else "محايد" if avg > 0.4 else "سلبي",
        "details": sentiment_results
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 4 — Competitor Ranking
# ══════════════════════════════════════════════════════════════════════════════
def competitor_ranking(brand: str, competitors: List[str], queries: List[str], api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    all_brands = [brand] + competitors
    scores = {b: 0 for b in all_brands}
    co_mentions = []

    for q in queries:
        answer = _llm(q, api_keys)
        if not answer:
            continue

        found = [b for b in all_brands if b.lower() in answer.lower()]
        for b in found:
            scores[b] += 1

        if brand in found and len(found) > 1:
            co_mentions.append({
                "query": q,
                "competitors_also_mentioned": [b for b in found if b != brand]
            })

    total = max(1, len(queries))
    ranking = sorted(
        [{"brand": b, "mentions": s, "visibility_pct": round(s / total * 100, 1), "is_you": b == brand}
         for b, s in scores.items()],
        key=lambda x: x["mentions"], reverse=True
    )
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    your_rank = next((r["rank"] for r in ranking if r["is_you"]), len(ranking))
    leader = ranking[0]

    return {
        "ranking": ranking,
        "co_mentions": co_mentions,
        "dominant_brand": leader["brand"],
        "your_rank": your_rank,
        "gap_to_leader": round(leader["visibility_pct"] - next(r["visibility_pct"] for r in ranking if r["is_you"]), 1)
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 5 — Geo-Regional Analysis
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 5 — Geo-Regional Analysis (Next-Gen Overhaul)
# ══════════════════════════════════════════════════════════════════════════════
def _generate_geo_queries(brand: str, industry: str, competitors: List[str], region: str) -> List[str]:
    """Generates 10-15 dialect-aware queries for a specific industry/region."""
    queries = []
    comps_str = ", ".join(competitors) if competitors else "المنافسين"
    
    # Core templates by region (as requested by user feedback)
    region_styles = {
        "gulf_arabic": {
            "keywords": ["متجر إلكتروني", "شركة", "خدمات", "بالسعودية", "بالخليج", "شسوي"],
            "phrases": [
                "وش أحسن {keyword} {industry} بالسعودية؟",
                "من يقدر يساعدني بخدمات {industry} بالخليج؟",
                "أفضل {keyword} {industry} في الرياض وجدة؟",
                "مقارنة بين {brand} و {comps} من أفضل؟",
                "تجاربكم مع {brand} في الإمارات والكويت؟",
                "ليش {brand} مشهور بالشرقية؟",
                "أبي أقوى {keyword} في دبي؟",
                "منصات مثل {comps} و {brand} وش تنصحوني؟"
            ]
        },
        "egyptian_arabic": {
            "keywords": ["موقع بيع أونلاين", "شركة", "خدمات", "في مصر", "قاهرة", "إسكندرية"],
            "phrases": [
                "إيه أحسن {keyword} {industry} في مصر؟",
                "مين أفضل شركة {industry} بتعاملوا معاها؟",
                "عايز أبدأ {industry} ومحتار بين {brand} و {comps}؟",
                "في حد جرب {brand} في مصر قبل كدة؟",
                "إيه رأيكم في {brand} كشركة {industry}؟",
                "أفضل {keyword} رخيص وكويس في القاهرة؟",
                "أنا بسمع عن {comps} و {brand} مين الأحسن؟",
                "مواقع زي {brand} في مصر بتعمل إيه؟"
            ]
        },
        "modern_standard_arabic": {
            "keywords": ["منصة تجارة", "مؤسسة", "حلول", "الوطن العربي", "الشرق الأوسط"],
            "phrases": [
                "ما هي أفضل {keyword} {industry} في الوطن العربي؟",
                "تطور قطاع {industry} في المنطقة وشركات مثل {brand}؟",
                "مقارنة تحليلية بين {brand} و {comps}؟",
                "من يتصدر سوق {industry} حالياً؟",
                "أفضل {keyword} {industry} احترافي للشركات؟",
                "خدمات {brand} مراجعة شاملة؟",
                "بدائل {comps} المتوفرة في الأردن وفلسطين؟",
                "حلول {industry} المبتكرة من {brand}؟"
            ]
        },
        "english_global": {
            "keywords": ["agency", "company", "services", "Middle East", "KSA", "UAE"],
            "phrases": [
                "Best {industry} {keyword} in Saudi Arabia?",
                "is {brand} better than {comps} for {industry}?",
                "top {industry} solutions for MENA region?",
                "recommendations for {brand} reviews?",
                "global leaders in {industry} similar to {brand}?",
                "leading {industry} {keyword} in Dubai and Riyadh?",
                "is {brand} a reliable {keyword}?",
                "compare {brand} vs {comps} features?"
            ]
        }
    }
    
    style = region_styles.get(region, region_styles["modern_standard_arabic"])
    for p in style["phrases"]:
        for kw in style["keywords"][:2]: # Mix first two keywords
            q = p.format(brand=brand, industry=industry, comps=comps_str, keyword=kw)
            queries.append(q)
            
    return queries[:15] # Return top 15

def _normalize_arabic(text: str) -> str:
    try:
        import pyarabic.araby as araby
        return araby.strip_tashkeel(text.strip().lower())
    except ImportError:
        return text.strip().lower()

def _is_arabic(text: str) -> bool:
    try:
        from langdetect import detect
        return detect(text) == 'ar'
    except Exception:
        return True

def _get_region_countries(region: str) -> List[dict]:
    mapping = {
        "gulf_arabic": ["SA", "AE", "KW", "QA", "OM", "BH"],
        "egyptian_arabic": ["EG", "SD"],
        "modern_standard_arabic": ["LB", "SY", "JO", "PS", "MA", "DZ", "TN", "IQ"],
        "english_global": ["US", "GB"]
    }
    codes = mapping.get(region, [])
    try:
        import pycountry
        return [{"code": c, "name": getattr(pycountry.countries.get(alpha_2=c), 'name', c)} for c in codes]
    except ImportError:
        return [{"code": c, "name": c} for c in codes]

def _quick_crawl(url: str) -> dict:
    import urllib.request
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            desc = desc_match.group(1).strip() if desc_match else ""
            return {"title": title, "desc": desc[:200]}
    except Exception:
        return {"title": "", "desc": ""}

def _extract_brand_from_url(text: str) -> str:
    text = text.strip()
    if text.startswith('http') or text.startswith('www.') or '.com' in text or '.net' in text:
        text = re.sub(r'^https?://', '', text)
        text = re.sub(r'^www\.', '', text)
        return text.split('.')[0]
    return text

def _get_heuristic_fallback(title: str, desc: str) -> dict:
    ctx = (title + " " + desc).lower()
    # E-commerce
    if any(k in ctx for k in ["متجر", "تجارة", "سلة", "زد", "shop", "ecommerce", "store"]):
        return {"industry": "التجارة الإلكترونية", "competitors": ["Salla (سلة)", "Zid (زد)", "Shopify"], "estimated_rank": 3}
    # Marketing
    if any(k in ctx for k in ["تسويق", "وكالة", "marketing", "agency", "ads", "إعلانات"]):
        return {"industry": "التسويق الرقمي", "competitors": ["2P (توبي)", "Perfect Presentation", "Socialize"], "estimated_rank": 2}
    # Tech/SaaS
    if any(k in ctx for k in ["تقنية", "برمجيات", "software", "saas", "tech", "كود"]):
        return {"industry": "التقنية والبرمجيات", "competitors": ["Microsoft", "Google Arab", "Oracle"], "estimated_rank": 4}
    return {"industry": "خدمات عامة", "competitors": ["منافس محلي 1", "منافس محلي 2"], "estimated_rank": "غير متوفر"}

# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 5 — Geo-Regional Analysis (Next-Gen Overhaul)
# ══════════════════════════════════════════════════════════════════════════════
def _generate_geo_queries(brand: str, industry: str, competitors: List[str], region: str) -> List[str]:
    """Generates 10-15 dialect-aware queries for a specific industry/region."""
    queries = []
    comps_str = ", ".join(competitors) if competitors else "المنافسين"
    
    region_styles = {
        "gulf_arabic": {
            "keywords": ["متجر إلكتروني", "شركة", "خدمات", "بالسعودية", "بالخليج", "أفضل"],
            "phrases": [
                "وش أحسن {keyword} {industry} بالسعودية؟",
                "من يقدر يساعدني بخدمات {industry} بالخليج؟",
                "أفضل {keyword} {industry} في الرياض وجدة؟",
                "مقارنة بين {brand} و {comps} من أفضل؟",
                "تجاربكم مع {brand} في الإمارات والكويت؟",
                "شسوي لو أبي أقوى {keyword} في دبي؟",
                "منصات مثل {comps} و {brand} وش تنصحوني؟"
            ]
        },
        "egyptian_arabic": {
            "keywords": ["موقع بيع أونلاين", "شركة", "خدمات", "في مصر", "قاهرة", "إسكندرية"],
            "phrases": [
                "إيه أحسن {keyword} {industry} في مصر؟",
                "مين أفضل شركة {industry} بتعاملوا معاها؟",
                "عايز أبدأ {industry} ومحتار بين {brand} و {comps}؟",
                "في حد جرب {brand} في مصر قبل كدة؟",
                "أنا بسمع عن {comps} و {brand} مين الأحسن؟",
                "أفضل {keyword} رخيص وكويس في القاهرة؟",
                "مواقع زي {brand} في مصر بتعمل إيه؟"
            ]
        },
        "modern_standard_arabic": {
            "keywords": ["منصة تجارة", "مؤسسة", "حلول", "الوطن العربي", "الشرق الأوسط"],
            "phrases": [
                "ما هي أفضل {keyword} {industry} في الوطن العربي؟",
                "تطور قطاع {industry} في المنطقة وشركات مثل {brand}؟",
                "مقارنة تحليلية بين {brand} و {comps}؟",
                "من يتصدر سوق {industry} حالياً؟",
                "أفضل {keyword} {industry} احترافي للشركات؟",
                "حلول {industry} المبتكرة من {brand}؟"
            ]
        },
        "english_global": {
            "keywords": ["agency", "company", "services", "Middle East", "KSA", "UAE"],
            "phrases": [
                "Best {industry} {keyword} in Saudi Arabia?",
                "is {brand} better than {comps} for {industry}?",
                "top {industry} solutions for MENA region?",
                "leading {industry} {keyword} in Dubai and Riyadh?",
                "compare {brand} vs {comps} features?",
                "is {brand} a reliable {keyword}?"
            ]
        }
    }
    
    style = region_styles.get(region, region_styles["modern_standard_arabic"])
    for p in style["phrases"]:
        for kw in style["keywords"][:2]:
            q = p.format(brand=brand, industry=industry, comps=comps_str, keyword=kw)
            queries.append(q)
            
    return queries[:15]

def geo_regional_analysis(brand: str, api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    geo_results = {}
    
    # 1. Smart URL Handler & Crawler Context
    is_url = brand.startswith('http') or brand.startswith('www.') or '.com' in brand
    clean_brand = _extract_brand_from_url(brand)
    
    site_data = {"title": "", "desc": ""}
    crawl_context = ""
    if is_url:
        site_data = _quick_crawl(brand)
        if site_data.get("title") or site_data.get("desc"):
            crawl_context = f"\nWebsite Context (For your reference to identify the industry): Title: {site_data['title']} | Description: {site_data['desc']}"
    
    # 2. Competitor Check
    comp_prompt = f"""Analyze the company/brand '{clean_brand}'.{crawl_context}
Identify its primary industry. 
List 3 top active competitors for it in the Middle East or Global market.
Estimate where '{clean_brand}' ranks among these 3 competitors based on AI visibility (1 being the highest visibility).
Return JSON ONLY:
{{"industry": "technology|finance|etc", "competitors": ["comp1", "comp2", "comp3"], "estimated_rank": 2}}"""
    comp_raw = _llm(comp_prompt, api_keys, json_mode=True)
    comp_data = _parse_json(comp_raw) if comp_raw else {}
    
    # 3. Fallback Heuristics if LLM is down/empty
    if not comp_data or not comp_data.get("competitors"):
        if is_url:
            comp_data = _get_heuristic_fallback(site_data.get("title", ""), site_data.get("desc", ""))
        else:
            comp_data = {"industry": "غير محدد", "competitors": ["Salla", "Zid", "Shopify"], "estimated_rank": "غير متوفر"}

    brand_aliases = [clean_brand.lower(), _normalize_arabic(clean_brand)]
    if is_url:
        
        brand_no_sym = re.sub(r'[^a-zA-Z0-9\u0621-\u064A]', '', clean_brand).lower()
        brand_space = re.sub(r'[^a-zA-Z0-9\u0621-\u064A]', ' ', clean_brand).lower()
        brand_aliases.extend([brand_no_sym, brand_space])
    
    # Try to find an Arabic name for the brand in the title/desc
    all_text = site_data.get("title", "") + " " + site_data.get("desc", "")
    arabic_names = re.findall(r'[\u0600-\u06FF\s]{4,}', all_text)
    for name in arabic_names:
        name_clean = name.strip()
        if len(name_clean) > 3:
            brand_aliases.append(name_clean.lower())
            brand_aliases.append(_normalize_arabic(name_clean))
    
    brand_aliases = list(set([a for a in brand_aliases if len(a) > 2]))

    for region in ["gulf_arabic", "egyptian_arabic", "modern_standard_arabic", "english_global"]:
        queries = _generate_geo_queries(clean_brand, comp_data.get("industry", "تجارة"), comp_data.get("competitors", []), region)
        region_scores = []
        evidence_queries = [] # Renamed from 'evidence'
        comp_list = comp_data.get("competitors", [])
        comp_mentions = {c: 0 for c in comp_list}
        
        # Pre-calculate normalized competitor parts to avoid redundant work
        comp_parts = {}
        for c in comp_list:
            parts = [c.lower(), _normalize_arabic(c)]
            # If "Salla (سلة)", add "salla" and "سلة"
            parts.extend(re.findall(r'[\w]+', c.lower()))
            parts.extend(re.findall(r'[\u0600-\u06FF]+', c))
            comp_parts[c] = list(set([p for p in parts if len(p) > 2]))

        success_count = 0
        # Track LLM errors for UI display
        llm_error = ""
        for q in queries:
            ans = _llm(q, api_keys)
            if not ans:
                continue
                
            if ans.startswith("ERROR:"):
                llm_error = ans
                continue

            success_count += 1
            # Check for brand mentions (English and discovery-based)
            norm_ans = _normalize_arabic(ans)
            answer_lower = ans.lower()
            answer_clean = re.sub(r'[^a-zA-Z0-9\s\u0621-\u064A]', ' ', answer_lower)
                
            # Flexible Brand Mention Check
            mentioned = any(alias in norm_ans or alias in answer_lower or alias in answer_clean for alias in brand_aliases)
            
            region_scores.append(mentioned)
                
            # Competitor Mention Check
            for c in comp_list:
                if any(p in norm_ans or p in answer_lower or p in answer_clean for p in comp_parts[c]):
                    comp_mentions[c] += 1
                
            if mentioned and len(evidence_queries) < 3:
                evidence_queries.append({"query": q, "snippet": ans[:150] + "..."})
            elif not mentioned and len(evidence_queries) < 1:
                evidence_queries.append({"query": q, "snippet": "لم يتم العثور على العلامة التجارية في الإجابة."})

        mentions = sum(region_scores) if region_scores else 0
        visibility_pct = float(round(mentions / len(queries) * 100, 1)) if queries else 0.0
        geo_results[region] = {
            "visibility_pct": visibility_pct,
            "mentions": mentions,
            "queries_tested": len(queries),
            "success_rate": round((success_count / max(1, len(queries))) * 100),
            "status": "Good" if visibility_pct > 30 else ("Needs Work" if visibility_pct > 0 else "Weak"),
            "competitor_mentions": comp_mentions,
            "evidence": evidence_queries,
            "llm_diagnostics": llm_error
        }

    arabic_regions = ["gulf_arabic", "egyptian_arabic", "modern_standard_arabic"]
    english_regions = ["english_global"]
    arabic_avg = float(round(sum(geo_results[r]["visibility_pct"] for r in arabic_regions) / 3, 1))
    global_avg = float(round(sum(geo_results[r]["visibility_pct"] for r in english_regions), 1))

    sorted_regions = sorted(geo_results.items(), key=lambda x: x[1]["visibility_pct"], reverse=True)

    return {
        "brand_analyzed": clean_brand,
        "industry": comp_data.get("industry", "غير محدد"),
        "competitors": comp_data.get("competitors", []),
        "estimated_rank": comp_data.get("estimated_rank", "غير متوفر"),
        "by_region": geo_results,
        "strongest": sorted_regions[0][0] if sorted_regions else "",
        "weakest": sorted_regions[-1][0] if sorted_regions else "",
        "arabic_avg": arabic_avg,
        "global_avg": global_avg
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 6 — Fix Recommendations + Simulator
# ══════════════════════════════════════════════════════════════════════════════
def fix_recommendations(url: str, brand: str, visibility_data: dict, api_keys: dict = None) -> dict:
    api_keys = api_keys or {}

    # Crawl page
    page_data = {"url": url, "title": "", "h1": [], "h2": [], "paragraphs": [],
                 "has_schema": False, "has_faq": False, "word_count": 0, "lang": "unknown"}
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        page_data["title"] = soup.title.string.strip() if soup.title else ""
        page_data["h1"] = [h.get_text().strip() for h in soup.find_all("h1")][:3]
        page_data["h2"] = [h.get_text().strip() for h in soup.find_all("h2")][:8]
        page_data["paragraphs"] = [p.get_text().strip()[:120] for p in soup.find_all("p") if len(p.get_text()) > 30][:8]
        page_data["has_schema"] = bool(soup.find_all("script", type="application/ld+json"))
        page_data["has_faq"] = bool(soup.find("details") or "FAQ" in soup.get_text() or "الأسئلة" in soup.get_text())
        page_data["word_count"] = len(soup.get_text().split())
        page_data["lang"] = soup.html.get("lang", "unknown") if soup.html else "unknown"
    except Exception as e:
        page_data["crawl_error"] = str(e)

    prompt = f"""You are a GEO (Generative Engine Optimization) expert for Arabic and English markets.

Brand: {brand}
Current AI Visibility Score: {visibility_data.get('visibility_score', 'unknown')}%
Page: {json.dumps(page_data, ensure_ascii=False)}

Generate actionable recommendations as JSON:
{{
  "critical_fixes": [{{"issue": "", "fix": "", "impact": "high|medium|low", "effort": "easy|medium|hard"}}],
  "schema_to_add": [],
  "content_gaps": [],
  "off_page_actions": [],
  "arabic_improvements": [],
  "quick_wins": []
}}"""

    raw = _llm(prompt, api_keys, json_mode=True)
    recs = _parse_json(raw) if raw else {}

    # Auto-generate missing schema
    if not page_data["has_schema"]:
        recs["auto_schema"] = {
            "@context": "https://schema.org", "@type": "Organization",
            "name": brand, "url": url, "inLanguage": ["ar", "en"]
        }
    if not page_data["has_faq"] and page_data["h2"]:
        recs["auto_faq_schema"] = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": h,
                 "acceptedAnswer": {"@type": "Answer", "text": "..."}}
                for h in page_data["h2"][:4]
            ]
        }

    recs["page_data"] = page_data
    return recs


def visibility_simulator(original_content: str, improved_content: str,
                          test_queries: List[str], brand: str, api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    results = []

    for q in test_queries:
        orig_prompt = f"Context:\n{original_content[:500]}\n\nQuestion: {q}\nAnswer based only on the context:"
        new_prompt = f"Context:\n{improved_content[:500]}\n\nQuestion: {q}\nAnswer based only on the context:"

        orig_answer = _llm(orig_prompt, api_keys)
        new_answer = _llm(new_prompt, api_keys)

        orig_mentioned = brand.lower() in orig_answer.lower() if orig_answer else False
        new_mentioned = brand.lower() in new_answer.lower() if new_answer else False

        results.append({
            "query": q,
            "before": {"mentioned": orig_mentioned, "answer": orig_answer[:150] if orig_answer else ""},
            "after": {"mentioned": new_mentioned, "answer": new_answer[:150] if new_answer else ""},
            "improvement": new_mentioned and not orig_mentioned
        })

    total = max(1, len(results))
    before_score = sum(1 for r in results if r["before"]["mentioned"])
    after_score = sum(1 for r in results if r["after"]["mentioned"])

    return {
        "before_visibility": round(before_score / total * 100, 1),
        "after_visibility": round(after_score / total * 100, 1),
        "expected_lift": round((after_score - before_score) / total * 100, 1),
        "queries_improved": sum(1 for r in results if r["improvement"]),
        "details": results
    }


# ══════════════════════════════════════════════════════════════════════════════
# Full Suite Runner — runs all 6 services for a brand
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_QUERIES = [
    "ما هي أفضل شركات السيو في السعودية؟",
    "من يقدم خدمات تحسين محركات البحث بالذكاء الاصطناعي؟",
    "best SEO companies in Saudi Arabia",
    "GEO optimization services Middle East",
    "شركة سيو موثوقة في الوطن العربي",
]

def run_full_suite(brand: str, url: str = None, competitors: List[str] = None,
                   api_keys: dict = None) -> dict:
    api_keys = api_keys or {}
    competitors = competitors or ["SEMrush", "Ahrefs", "Moz"]
    queries = DEFAULT_QUERIES

    vis = visibility_score(brand, queries, api_keys)
    rec = brand_recognition(brand, [brand], queries, api_keys)
    sent = sentiment_analysis(brand, queries[:3], api_keys)
    comp = competitor_ranking(brand, competitors, queries[:4], api_keys)
    geo = geo_regional_analysis(brand, api_keys)

    result = {
        "brand": brand,
        "visibility": vis,
        "recognition": rec,
        "sentiment": sent,
        "competitors": comp,
        "geo_regional": geo,
    }

    if url:
        result["fix_recommendations"] = fix_recommendations(
            url, brand,
            {"visibility_score": vis.get("visibility_score", 0)},
            api_keys
        )

    return result


def calculate_visibility_score_v2(brand: str, searches: List[dict], ai_mentions: int, total_queries: int, traffic_estimate: str = "unknown") -> dict:
    """
    Visibility Score Engine v2
    Score = (SEO rank weight * 40%) + (AI mentions * 40%) + (traffic * 20%)
    """
    # 1. SEO Rank (40%)
    ranks = []
    for s in searches:
        found_at = 101
        # SerpApi organic results
        results = s.get("organic_results", [])
        if not results and "organic" in s: # ZenSerp style
            results = s["organic"]
            
        for i, res in enumerate(results):
            link = res.get("link", "").lower()
            title = res.get("title", "").lower()
            snippet = res.get("snippet", "").lower()
            if brand.lower() in link or brand.lower() in title or brand.lower() in snippet:
                found_at = i + 1
                break
        ranks.append(found_at)
    
    avg_rank = sum(ranks) / len(ranks) if ranks else 101
    # 1st = 100pts, 10th = 50pts, 20th = 0pts
    rank_score = max(0, 100 - (avg_rank - 1) * 5.2) if avg_rank <= 20 else 0
    
    # 2. AI Mentions (40%)
    ai_score = (ai_mentions / total_queries * 100) if total_queries > 0 else 0
    
    # 3. Traffic (20%)
    try:
        # Extract number from "50K - 100K"
        match = re.search(r'(\d+)\s*(K|M)', str(traffic_estimate), re.I)
        if match:
            num = int(match.group(1))
            unit = match.group(2).upper()
            if unit == 'K': num *= 1000
            if unit == 'M': num *= 1000000
        else:
            num = int(re.sub(r'[^0-9]', '', str(traffic_estimate)))
            
        # Benchmark: 100K+ is 100%, 10K is 50%
        traffic_score = min(100, (num / 100000 * 100)) if num > 0 else 10
    except:
        traffic_score = 50 # Neutral average
        
    final_score = (rank_score * 0.4) + (ai_score * 0.4) + (traffic_score * 0.2)
    
    return {
        "score": round(final_score, 1),
        "breakdown": {
            "seo_rank": round(rank_score, 1),
            "ai_visibility": round(ai_score, 1),
            "traffic": round(traffic_score, 1)
        },
        "avg_rank": round(avg_rank, 1) if avg_rank <= 100 else ">100"
    }


def get_competitor_insights(brand: str, url: str = None, api_keys: dict = None) -> dict:
    """
    Enhanced Competitor Insights using Search APIs (SerpApi/ZenSerp).
    """
    api_keys = api_keys or {}
    clean_brand = brand
    if brand.startswith('http') or '.com' in brand:
        clean_brand = _extract_brand_from_url(brand)
    
    # 1. Fetch real rankings for core queries
    test_queries = [f"أفضل منافسين {clean_brand}", f"best {clean_brand} competitors in Egypt Saudi Arabia"]
    search_data = []
    
    serp_key = api_keys.get("SERPAPI_KEY")
    zen_key = api_keys.get("ZENSERP_KEY")
    
    for q in test_queries:
        res = _serp_api_search(q, api_key=serp_key)
        if not res:
            res = _zenserp_search(q, api_key=zen_key)
        if res:
            search_data.append(res)

    # 2. Extract competitor names from search results
    found_comps = []
    for s in search_data:
        items = s.get("organic_results", s.get("organic", []))
        for it in items[:5]:
            found_comps.append(it.get("title", ""))

    # 3. LLM Refinement & Similarweb-style metrics
    prompt = f"""Analyze the brand '{clean_brand}'.
    We found these potential competitors via search: {", ".join(found_comps[:8])}
    
    Provide a realistic market analysis for the MENA region.
    Return JSON only:
    {{
      "monthly_visits": "75K",
      "traffic_sources": {{"search": 45, "direct": 25, "social": 20, "referral": 10}},
      "top_competitors": [
        {{"name": "Comp Name", "domain": "comp.com", "overlap_score": 95, "region": "SA"}},
        {{"name": "Comp 2", "domain": "comp2.com", "overlap_score": 88, "region": "Global"}}
      ],
      "regional_split": [
        {{"country": "Saudi Arabia", "share": 60}},
        {{"country": "UAE", "share": 20}}
      ],
      "industry": "...",
      "seo_rankings": [
        {{"query": "...", "rank": 1, "link": "..."}}
      ]
    }}
    """
    
    try:
        raw = _llm(prompt, api_keys, json_mode=True)
        data = _parse_json(raw)
        if data:
            # If search data is rich, use it to populate seo_rankings if LLM didn't
            if (not data.get("seo_rankings") or len(data.get("seo_rankings")) == 0) and search_data:
                data["seo_rankings"] = []
                for s in search_data[:1]:
                    for it in s.get("organic_results", s.get("organic", []))[:3]:
                        data["seo_rankings"].append({
                            "query": s.get("search_parameters", {}).get("q", ""), 
                            "rank": it.get("position"), 
                            "link": it.get("link")
                        })
            return data
    except Exception:
        pass

    # Fallback
    return {
        "monthly_visits": "10K - 50K",
        "traffic_sources": { "search": 40, "direct": 30, "social": 20, "referral": 10 },
        "top_competitors": [
            { "name": "منافس 1", "domain": "comp1.com", "overlap_score": 90, "region": "SA" },
            { "name": "منافس 2", "domain": "comp2.com", "overlap_score": 85, "region": "UAE" }
        ],
        "industry": "خدمات رقمية",
        "seo_rankings": []
    }
