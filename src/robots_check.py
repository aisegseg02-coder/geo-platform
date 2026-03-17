import requests
from urllib.parse import urljoin

AI_USER_AGENTS = ['GPTBot', 'Google-Extended', 'PerplexityBot', 'ClaudeBot', 'CCBot']


def is_ai_allowed(base_url: str) -> dict:
    """Fetch robots.txt and report whether common AI crawlers are allowed or disallowed.

    Returns a dict { 'robots_url': ..., 'allowed': {agent: True/False/None}, 'raw': '...' }
    """
    robots_url = urljoin(base_url, '/robots.txt')
    try:
        r = requests.get(robots_url, timeout=8)
        if r.status_code != 200:
            return {'robots_url': robots_url, 'allowed': {}, 'raw': None, 'reason': f'status {r.status_code}'}
        txt = r.text
        allowed = {}
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith('#')]
        # simple parse: track last user-agent block
        ua = None
        rules = {}
        for ln in lines:
            if ln.lower().startswith('user-agent:'):
                ua = ln.split(':',1)[1].strip()
                rules.setdefault(ua, [])
            elif ua and (ln.lower().startswith('disallow:') or ln.lower().startswith('allow:')):
                rules[ua].append(ln)

        for a in AI_USER_AGENTS:
            # check exact agent then wildcard
            val = None
            if a in rules:
                # if any Disallow: / present -> blocked
                dis = any('disallow: /' in r.lower() for r in rules[a])
                val = not dis
            elif '*' in rules:
                dis = any('disallow: /' in r.lower() for r in rules['*'])
                val = not dis
            allowed[a] = val

        return {'robots_url': robots_url, 'allowed': allowed, 'raw': txt}
    except Exception as e:
        return {'robots_url': robots_url, 'allowed': {}, 'raw': None, 'reason': str(e)}
