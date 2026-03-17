import os
import requests
import time
import hashlib
from typing import List

from server import cache
from server import utils

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


def _key_for(query: str, prefix: str = 'perplexity') -> str:
    h = hashlib.sha256(query.encode('utf-8')).hexdigest()
    return f"{prefix}:{h}"


def check_perplexity(brand: str, queries: List[str], api_key: str = None):
    key = api_key or os.getenv('PERPLEXITY_KEY')
    results = []

    if not key:
        return { 'enabled': False, 'reason': 'PERPLEXITY_KEY not set', 'results': [] }

    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }

    for q in queries:
        cache_key = _key_for(q, 'perplexity')
        cached = cache.get(cache_key)
        if cached is not None:
            results.append(cached)
            continue

        payload = {
            'model': 'sonar',
            'messages': [{'role':'user','content': q}]
        }
        try:
            @utils.retry(attempts=3, backoff_base=1.0, exceptions=(Exception,))
            def call_perplexity():
                r = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=20)
                r.raise_for_status()
                return r.json()

            data = call_perplexity()
            ans = None
            try:
                ans = data['choices'][0]['message']['content']
            except Exception:
                ans = str(data)
            mentioned = brand.lower() in (ans or '').lower()
            out = { 'query': q, 'mentioned': mentioned, 'answer': ans }
            results.append(out)
            try:
                cache.set(cache_key, out)
            except Exception:
                pass
        except Exception as e:
            results.append({ 'query': q, 'error': str(e) })
        time.sleep(1)

    return { 'enabled': True, 'results': results }


def check_openai_visibility(brand: str, queries: List[str], api_key: str = None):
    """Fallback visibility check using OpenAI if Perplexity missing."""
    try:
        import openai
    except Exception:
        return { 'enabled': False, 'reason': 'openai library not available', 'results': [] }

    key = api_key or os.getenv('OPENAI_API_KEY')
    if not key:
        return { 'enabled': False, 'reason': 'OPENAI_API_KEY not set', 'results': [] }
    openai.api_key = key
    results = []
    for q in queries:
        cache_key = _key_for(q, 'openai_vis')
        cached = cache.get(cache_key)
        if cached is not None:
            results.append(cached)
            continue
        try:
            @utils.retry(attempts=3, backoff_base=1.0, exceptions=(Exception,))
            def call_openai():
                return openai.ChatCompletion.create(model=os.getenv('OPENAI_MODEL','gpt-3.5-turbo'), messages=[{'role':'user','content':q}], temperature=0.0)

            resp = call_openai()
            text = resp['choices'][0]['message']['content']
            mentioned = brand.lower() in (text or '').lower()
            out = { 'query': q, 'mentioned': mentioned, 'answer': text }
            results.append(out)
            try:
                cache.set(cache_key, out)
            except Exception:
                pass
        except Exception as e:
            results.append({ 'query': q, 'error': str(e) })
    return { 'enabled': True, 'results': results }


def check_ollama(content_chunk, test_query):
    # If OLLAMA_HOST env var is set, call local Ollama
    host = os.getenv('OLLAMA_HOST')
    if not host:
        return { 'enabled': False, 'reason': 'OLLAMA_HOST not set' }
    try:
        resp = requests.post(f"{host}/chat", json={
            'model': 'llama3',
            'messages': [{ 'role':'user','content': f"User asks: {test_query}\nContent:\n{content_chunk}" }]
        }, timeout=20)
        resp.raise_for_status()
        return { 'enabled': True, 'response': resp.json() }
    except Exception as e:
        return { 'enabled': True, 'error': str(e) }
