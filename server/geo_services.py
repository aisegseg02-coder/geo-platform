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
        
        if r.status_code == 429:
            return "ERROR: OpenRouter rate limit exceeded (429)"
        
        r.raise_for_status()
        response_data = r.json()
        
        if "error" in response_data:
            error_msg = response_data["error"].get("message", "")
            if "credit" in error_msg.lower() or "rate" in error_msg.lower():
                return f"ERROR: OpenRouter quota - {error_msg}"
        
        return response_data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return "ERROR: OpenRouter rate limit (429)"
        return f"ERROR: OpenRouter HTTP {e.response.status_code}"
    except Exception as e:
        return f"ERROR: OpenRouter - {str(e)[:100]}"


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
        
        # Check for rate limit errors
        if r.status_code == 429:
            return "ERROR: OpenAI rate limit exceeded (429)"
        
        r.raise_for_status()
        response_data = r.json()
        
        # Check for quota errors in response
        if "error" in response_data:
            error_msg = response_data["error"].get("message", "")
            if "quota" in error_msg.lower() or "insufficient" in error_msg.lower():
                return f"ERROR: OpenAI quota exceeded - {error_msg}"
        
        return response_data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return "ERROR: OpenAI rate limit exceeded (429)"
        return f"ERROR: OpenAI HTTP {e.response.status_code}"
    except Exception as e:
        return f"ERROR: OpenAI - {str(e)[:100]}"


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
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "rate" in error_msg or "quota" in error_msg:
            return f"ERROR: Groq rate limit - {str(e)[:100]}"
        return f"ERROR: Groq - {str(e)[:100]}"


# ── Smart LLM Router with Quota Detection ────────────────────────────────────
def _llm(prompt: str, api_keys: dict = None, json_mode: bool = False) -> str:
    """
    Intelligent LLM router with automatic failover on rate limits.
    Priority: Ollama (free) → OpenAI → Groq → OpenRouter
    Detects 429 errors and quota exhaustion, switches providers automatically.
    """
    api_keys = api_keys or {}
    errors = []
    
    # Provider configurations with quota detection
    providers = [
        {
            "name": "Ollama",
            "func": lambda: _ollama_chat(prompt, model="qwen2", json_mode=json_mode),
            "enabled": True,  # Always try local first
            "quota_errors": ["connection refused", "timeout", "not found"]
        },
        {
            "name": "OpenAI",
            "func": lambda: _openai_chat(prompt, api_key=api_keys.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")),
            "enabled": bool(api_keys.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")),
            "quota_errors": ["429", "rate_limit_exceeded", "insufficient_quota", "quota exceeded"]
        },
        {
            "name": "Groq",
            "func": lambda: _groq_chat(prompt, api_key=api_keys.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")),
            "enabled": bool(api_keys.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")),
            "quota_errors": ["429", "rate_limit", "quota", "too many requests"]
        },
        {
            "name": "OpenRouter",
            "func": lambda: _openrouter_chat(prompt, api_key=api_keys.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
            "enabled": bool(api_keys.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
            "quota_errors": ["429", "rate limit", "credits"]
        }
    ]
    
    for provider in providers:
        if not provider["enabled"]:
            errors.append(f"{provider['name']}: Key missing")
            continue
            
        try:
            res = provider["func"]()
            if res and not res.startswith("ERROR:"):
                print(f"✓ {provider['name']} succeeded")
                return res
            elif res:
                # Check if it's a quota error
                is_quota_error = any(err_keyword in res.lower() for err_keyword in provider["quota_errors"])
                if is_quota_error:
                    errors.append(f"{provider['name']}: Quota exceeded, switching provider...")
                    print(f"⚠ {provider['name']} quota exceeded, trying next provider")
                else:
                    errors.append(f"{provider['name']}: {res[:100]}")
            else:
                errors.append(f"{provider['name']}: Empty response")
        except Exception as e:
            error_msg = str(e).lower()
            is_quota_error = any(err_keyword in error_msg for err_keyword in provider["quota_errors"])
            
            if is_quota_error:
                errors.append(f"{provider['name']}: Rate limit hit - {str(e)[:80]}")
                print(f"⚠ {provider['name']} rate limited: {str(e)[:80]}")
            else:
                errors.append(f"{provider['name']}: {str(e)[:80]}")
    
    # All providers failed
    log_msg = " | ".join(errors)
    print(f"❌ LLM FAILURE: {log_msg}")
    return f"ERROR: All LLM providers exhausted. {log_msg}"


def _serp_api_search(query: str, location: str = "Saudi Arabia", api_key: str = None) -> dict:
    """Fetches real search results via SerpApi with quota detection."""
    keys = [api_key] if api_key else []
    for suffix in ['', '_2', '_3', '_4', '_5']:
        k = os.environ.get(f'SERPAPI_KEY{suffix}')
        if k and k not in keys:
            keys.append(k)
            
    if not keys:
        return {}
        
    for i, key in enumerate(keys):
        try:
            r = requests.get("https://serpapi.com/search", params={
                "q": query,
                "location": location,
                "hl": "ar",
                "gl": "sa",
                "google_domain": "google.com.sa",
                "api_key": key
            }, timeout=15)
            
            if r.status_code == 429:
                print(f"⚠ SerpApi rate limit exceeded (429) for key ending in ...{key[-4:]}")
                if i < len(keys) - 1:
                    continue
                return {"error": "rate_limit"}
                
            r.raise_for_status()
            data = r.json()
            
            # Check for quota errors in response
            if "error" in data:
                print(f"⚠ SerpApi error: {data['error']}")
                # If error is quota or credentials, try next key
                if "quota" in data["error"].lower() or "unauthorized" in data["error"].lower():
                    if i < len(keys) - 1:
                        continue
                return {"error": "api_error", "message": data["error"]}
            
            return data
        except requests.exceptions.HTTPError as e:
            if i < len(keys) - 1: # If not last key, try next
                print(f"⚠ SerpApi HTTP Error {e.response.status_code} - trying next key")
                continue
            if e.response.status_code == 429:
                print("⚠ SerpApi rate limit (429)")
                return {"error": "rate_limit"}
            print(f"❌ SerpApi HTTP Error: {e}")
            return {}
        except Exception as e:
            print(f"❌ SerpApi Error: {e}")
            if i < len(keys) - 1:
                continue
            return {}
    return {}


def _zenserp_search(query: str, location: str = "Saudi Arabia", api_key: str = None) -> dict:
    """Fetches real search results via ZenSerp with quota detection."""
    key = api_key or os.environ.get("ZENSERP_KEY")
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
        
        if r.status_code == 429:
            print("⚠ ZenSerp rate limit exceeded (429)")
            return {"error": "rate_limit", "message": "ZenSerp quota exceeded"}
        
        r.raise_for_status()
        data = r.json()
        
        if "error" in data:
            print(f"⚠ ZenSerp error: {data['error']}")
            return {"error": "api_error", "message": data["error"]}
        
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("⚠ ZenSerp rate limit (429)")
            return {"error": "rate_limit"}
        print(f"❌ ZenSerp HTTP Error: {e}")
        return {}
    except Exception as e:
        print(f"❌ ZenSerp Error: {e}")
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
  "shopping_visibility": {{
    "price_mentioned": true/false,
    "review_count_mentioned": true/false,
    "rating_score_mentioned": true/false,
    "buying_advice": "brief string"
  }},
  "context": {{
    "scenario": "storyline (e.g. buying advice, complaint, comparison)",
    "trigger": "what led to the brand mention",
    "is_solo_mention": true/false (true if {brand} is the only brand mentioned in snippet)
  }},
  "key_phrases": [],
  "summary": "one sentence summary"
}}"""
        raw = _llm(prompt, api_keys, json_mode=True)
        analysis = _parse_json(raw) if raw else {}
        
        # Merge defaults if AI fails
        if not analysis or not isinstance(analysis, dict):
            analysis = {
                "polarity": "neutral", "score": 0.5, "trust_level": "medium", 
                "tone": "casual", "shopping_visibility": {}, "context": {}, 
                "key_phrases": [], "summary": ""
            }

        sentiment_results.append({
            "query": q,
            "brand_sentences": sentences[:2],
            "analysis": analysis
        })

    if not sentiment_results:
        return {"brand": brand, "avg_sentiment_score": 0, "overall_tone": "Unknown", "details": [], "error": "No LLM available"}

    def _get_score(res):
        analysis = res.get("analysis", {})
        if isinstance(analysis, str): return 0.5
        return float(analysis.get("score", 0.5)) if isinstance(analysis, dict) else 0.5

    scores = [_get_score(r) for r in sentiment_results]
    avg = sum(scores) / len(scores) if scores else 0.5

    # Aggregates for report
    shopping_stats = {
        "price_mentions": sum(1 for r in sentiment_results if r.get("analysis", {}).get("shopping_visibility", {}).get("price_mentioned")),
        "review_mentions": sum(1 for r in sentiment_results if r.get("analysis", {}).get("shopping_visibility", {}).get("review_count_mentioned")),
        "avg_rating_mentions": sum(1 for r in sentiment_results if r.get("analysis", {}).get("shopping_visibility", {}).get("rating_score_mentioned"))
    }
    
    context_stats = {
        "solo_mentions": sum(1 for r in sentiment_results if r.get("analysis", {}).get("context", {}).get("is_solo_mention")),
        "common_scenarios": list(set([r.get("analysis", {}).get("context", {}).get("scenario") for r in sentiment_results if r.get("analysis", {}).get("context", {}).get("scenario")]))
    }

    return {
        "brand": brand,
        "avg_sentiment_score": round(avg * 100, 1),
        "overall_tone": "إيجابي" if avg > 0.6 else "محايد" if avg > 0.4 else "سلبي",
        "shopping_visibility": shopping_stats,
        "context_analysis": context_stats,
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
            
            # Extract first 3 paragraphs for content count
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            paras = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
            return {"title": title, "desc": desc[:200], "paragraphs": paras[:5], "content": ' '.join(paras[:3])[:500]}
    except Exception:
        return {"title": "", "desc": ""}

def _extract_brand_from_url(text: str) -> str:
    text = text.strip()
    if text.startswith('http') or text.startswith('www.') or '.com' in text or '.net' in text:
        text = re.sub(r'^https?://', '', text)
        text = re.sub(r'^www\.', '', text)
        return text.split('.')[0]
    return text

def _get_heuristic_fallback(title: str, desc: str, url: str = "") -> dict:
    """Enhanced heuristic with URL analysis and better keyword matching."""
    ctx = (title + " " + desc + " " + url).lower()
    
    # Marketing & Advertising (PRIORITY - most common misclassification)
    marketing_keywords = ["تسويق", "وكالة", "marketing", "agency", "إعلان", "ads", "دعاية", 
                          "برومو", "حملات", "سوشيال", "social", "digital", "رقمي", "ربحان", 
                          "أرباح", "profit", "campaign", "brand", "علامة تجارية"]
    if any(k in ctx for k in marketing_keywords):
        return {
            "industry": "التسويق الرقمي والإعلانات",
            "competitors": ["2P (توبي)", "Perfect Presentation", "Socialize Agency", "Thameen"],
            "estimated_rank": "غير محدد"
        }
    
    # E-commerce
    ecommerce_keywords = ["متجر", "تجارة", "سلة", "زد", "shop", "ecommerce", "store", "بيع", "شراء", "منتج"]
    if any(k in ctx for k in ecommerce_keywords):
        return {
            "industry": "التجارة الإلكترونية",
            "competitors": ["Salla (سلة)", "Zid (زد)", "Shopify", "Noon"],
            "estimated_rank": "غير محدد"
        }
    
    # Tech/SaaS (EXCLUDE testing keywords to avoid confusion)
    tech_keywords = ["تطبيق", "برمجة", "software", "saas", "tech", "كود", "app", "platform", "منصة"]
    testing_keywords = ["test", "testing", "qa", "quality assurance", "اختبار"]
    has_tech = any(k in ctx for k in tech_keywords)
    has_testing = any(k in ctx for k in testing_keywords)
    
    if has_tech and not has_testing:
        return {
            "industry": "التقنية والبرمجيات",
            "competitors": ["Microsoft", "Google", "Oracle", "SAP"],
            "estimated_rank": "غير محدد"
        }
    
    # Consulting & Services
    consulting_keywords = ["استشارات", "خدمات", "consulting", "services", "حلول", "solutions"]
    if any(k in ctx for k in consulting_keywords):
        return {
            "industry": "الاستشارات والخدمات المهنية",
            "competitors": ["Deloitte", "PwC", "McKinsey", "EY"],
            "estimated_rank": "غير محدد"
        }
    
    # Default fallback
    return {
        "industry": "خدمات عامة (يُنصح بتحديد الصناعة يدوياً)",
        "competitors": ["منافس محلي 1", "منافس محلي 2", "منافس محلي 3"],
        "estimated_rank": "غير متوفر"
    }

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
    
    # 2. Enhanced Competitor Check with Validation
    comp_prompt = f"""Analyze the company/brand '{clean_brand}'.{crawl_context}

IMPORTANT RULES:
1. If the website title contains generic words like 'test', 'demo', 'example' - IGNORE them and focus on the description and site name
2. Look for Arabic keywords in the description to identify the industry
3. If you see words like 'ربحان', 'أرباح', 'تسويق', 'إعلانات' - this is likely a MARKETING/ADVERTISING agency
4. DO NOT classify as 'software testing' unless explicitly stated
5. List REAL competitors that operate in the same industry in the Middle East

Identify its primary industry and list 3-4 real competitors.
Return JSON ONLY:
{{"industry": "التسويق الرقمي|التجارة الإلكترونية|etc", "competitors": ["comp1", "comp2", "comp3"], "estimated_rank": "غير محدد", "confidence": "high|medium|low"}}"""
    
    comp_raw = _llm(comp_prompt, api_keys, json_mode=True)
    comp_data = _parse_json(comp_raw) if comp_raw else {}
    
    # 3. Validation Layer - Check if LLM output makes sense
    if comp_data and comp_data.get("competitors"):
        # Validate: If classified as 'testing' but no testing keywords in content, reject it
        industry_lower = comp_data.get("industry", "").lower()
        testing_indicators = ["test", "qa", "quality", "اختبار", "جودة"]
        content_lower = (site_data.get("title", "") + " " + site_data.get("desc", "")).lower()
        
        has_testing_industry = any(t in industry_lower for t in testing_indicators)
        has_testing_content = any(t in content_lower for t in testing_indicators if t != "test")  # Exclude generic 'test'
        
        # If LLM says testing but content doesn't support it, use heuristic fallback
        if has_testing_industry and not has_testing_content:
            print(f" LLM misclassified as testing - using heuristic fallback")
            comp_data = _get_heuristic_fallback(site_data.get("title", ""), site_data.get("desc", ""), brand)
            comp_data["validation_note"] = "تم تصحيح التصنيف تلقائياً (LLM output rejected)"
    
    # 4. Fallback Heuristics if LLM is down/empty or low confidence
    if not comp_data or not comp_data.get("competitors") or comp_data.get("confidence") == "low":
        if is_url:
            comp_data = _get_heuristic_fallback(site_data.get("title", ""), site_data.get("desc", ""), brand)
        else:
            comp_data = {"industry": "غير محدد", "competitors": ["منافس 1", "منافس 2", "منافس 3"], "estimated_rank": "غير متوفر"}
        comp_data["fallback_used"] = True

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

        success_count: int = 0
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
    # Lenient Scoring: 1st = 100pts, 30th = 50pts, 60th = 0pts
    if avg_rank <= 60:
        rank_score = max(0, 100 - (avg_rank - 1) * (100 / 59))
    else:
        rank_score = 0
    
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
        # If no numeric estimation, use Rank as a proxy (Better rank = slightly better presumed traffic)
        traffic_score = max(5, int(rank_score * 0.4))
        
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


def get_competitor_insights(brand: str, url: str = None, api_keys: dict = None, industry_override: str = None) -> dict:
    """
    Enhanced Competitor Insights with better industry detection and real search data.
    """
    api_keys = api_keys or {}
    clean_brand = brand
    if brand.startswith('http') or '.com' in brand:
        clean_brand = _extract_brand_from_url(brand)
    
    # 1. Crawl the website for better context
    site_context = {"title": "", "desc": "", "content": ""}
    if url or brand.startswith('http'):
        target_url = url or brand
        site_context = _quick_crawl(target_url)
        # Extract more content for better classification
        try:
            import urllib.request
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                # Extract first 500 chars of visible text
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                site_context["content"] = ' '.join(chunk for chunk in chunks if chunk)[:500]
        except Exception:
            pass
    
    # 2. Determine industry - prioritize user override
    if industry_override:
        detected_industry = industry_override
        # Get matching competitors for the override industry
        industry_map = {
            "التسويق الرقمي والإعلانات": ["2P (توبي)", "Perfect Presentation", "Socialize Agency", "Thameen"],
            "التجارة الإلكترونية": ["Salla (سلة)", "Zid (زد)", "Shopify", "Noon"],
            "التقنية والبرمجيات": ["Microsoft", "Google", "Oracle", "SAP"],
            "الاستشارات والخدمات المهنية": ["Deloitte", "PwC", "McKinsey", "EY"],
            "التعليم والتدريب": ["Coursera", "Udemy", "LinkedIn Learning", "Edraak"],
            "الصحة والطب": ["Vezeeta", "Altibbi", "Shezlong", "Sehhaty"],
            "العقارات": ["Bayut", "Property Finder", "Aqar", "Dubizzle"],
            "المطاعم والضيافة": ["Talabat", "Jahez", "HungerStation", "Careem Food"]
        }
        suggested_competitors = industry_map.get(detected_industry, ["منافس 1", "منافس 2", "منافس 3"])
    else:
        # Use enhanced heuristics
        full_context = f"{site_context.get('title', '')} {site_context.get('desc', '')} {site_context.get('content', '')}"
        heuristic_result = _get_heuristic_fallback(site_context.get('title', ''), site_context.get('desc', ''), brand)
        detected_industry = heuristic_result["industry"]
        suggested_competitors = heuristic_result["competitors"]
    
    # 3. Fetch real rankings with smart API switching
    test_queries = [
        f"{clean_brand} شركة",
        f"{clean_brand} خدمات",
        f"{detected_industry} السعودية"
    ]
    search_data = []
    seo_rankings = []
    
    serp_key = api_keys.get("SERPAPI_KEY") or os.environ.get("SERPAPI_KEY")
    zen_key = api_keys.get("ZENSERP_KEY") or os.environ.get("ZENSERP_KEY")
    
    # Track which API is working
    serp_exhausted = False
    zen_exhausted = False
    
    for q in test_queries:
        res = None
        
        # Try SerpAPI first (if not exhausted)
        if not serp_exhausted and serp_key:
            res = _serp_api_search(q, api_key=serp_key)
            if res.get("error") == "rate_limit":
                print(f"⚠ SerpAPI quota exhausted, switching to ZenSerp")
                serp_exhausted = True
                res = None
        
        # Fallback to ZenSerp (if SerpAPI failed or exhausted)
        if not res and not zen_exhausted and zen_key:
            res = _zenserp_search(q, api_key=zen_key)
            if res.get("error") == "rate_limit":
                print(f"⚠ ZenSerp quota exhausted")
                zen_exhausted = True
                res = None
        
        if res and "error" not in res:
            search_data.append(res)
            # Extract rankings where brand appears
            items = res.get("organic_results", res.get("organic", []))
            for idx, it in enumerate(items[:10]):
                link = it.get("link", "").lower()
                title = it.get("title", "").lower()
                if clean_brand.lower() in link or clean_brand.lower() in title:
                    seo_rankings.append({
                        "query": q,
                        "rank": idx + 1,
                        "link": it.get("link", "")
                    })
                    break

    # 4. Extract real competitor domains from search results
    found_domains = []
    for s in search_data:
        items = s.get("organic_results", s.get("organic", []))
        for it in items[:5]:
            domain = it.get("link", "")
            if domain and clean_brand.lower() not in domain.lower():
                # Extract clean domain
                domain = re.sub(r'^https?://', '', domain)
                domain = re.sub(r'^www\.', '', domain)
                domain = domain.split('/')[0]
                if domain and domain not in found_domains:
                    found_domains.append(domain)

    # 5. Build competitor list - ONLY from real search results
    top_competitors = []
    for idx, domain in enumerate(found_domains[:4]):
        top_competitors.append({
            "name": domain.split('.')[0].title(),
            "domain": domain,
            "overlap_score": 0,  # Real calculation needed
            "region": "MENA",
            "similarity": 0  # Real calculation needed
        })
    
    # 6. Traffic - NO ESTIMATES, only real data or "unknown"
    traffic_estimate = "غير متوفر"
    
    return {
        "monthly_visits": traffic_estimate,
        "traffic_sources": {} if not seo_rankings else {"search": 100},  # Only show if we have real data
        "top_competitors": top_competitors if top_competitors else [],
        "regional_split": [],  # Remove mock regional data
        "industry": detected_industry,
        "seo_rankings": seo_rankings[:5],
        "data_quality": "real" if len(seo_rankings) > 0 else "no_data",
        "note": "بيانات حقيقية من محركات البحث" if len(seo_rankings) > 0 else "لا توجد بيانات كافية - يرجى التحقق من مفاتيح API"
    }
