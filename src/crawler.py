import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def fetch_html(url, timeout=15):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent":"geo-pipeline/1.0"})
    resp.raise_for_status()
    return resp.text


def fetch_html_playwright(url, timeout=30):
    """Attempt to fetch page HTML using Playwright (optional dependency).

    Returns page content string or raises if Playwright not available or fails.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError('playwright not installed') from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)
        content = page.content()
        browser.close()
        return content

def extract_page(url, html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    headings = []
    for h in soup.find_all(['h1','h2','h3','h4','h5','h6']):
        headings.append({
            'tag': h.name,
            'text': h.get_text(strip=True)
        })
    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

    # collect internal links (same domain)
    parsed = urlparse(url)
    domain = parsed.netloc
    links = set()
    for a in soup.find_all('a', href=True):
        href = urljoin(url, a['href'])
        if urlparse(href).netloc == domain:
            links.add(href)

    return {
        'url': url,
        'title': title,
        'headings': headings,
        'paragraphs': paragraphs,
        'links': list(links)
    }

def crawl_seed(seed_url, max_pages=5):
    seen = set()
    to_visit = [seed_url]
    pages = []
    while to_visit and len(pages) < max_pages:
        u = to_visit.pop(0)
        if u in seen:
            continue
        try:
            html = fetch_html(u)
            page = extract_page(u, html)
            # if page looks empty (no paragraphs) try Playwright rendering
            if not page.get('paragraphs'):
                try:
                    html2 = fetch_html_playwright(u)
                    page2 = extract_page(u, html2)
                    if page2.get('paragraphs'):
                        page = page2
                except Exception:
                    pass
            pages.append(page)
            seen.add(u)
            for l in page['links']:
                if l not in seen and l not in to_visit:
                    to_visit.append(l)
        except Exception as e:
            # skip pages that fail
            print(f"[crawl] failed {u}: {e}")
    return pages
