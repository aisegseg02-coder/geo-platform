import requests
from bs4 import BeautifulSoup

def quick_crawl(url):
    try:
        url = url if url.startswith('http') else 'https://' + url
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else ""
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag:
            meta_desc = meta_tag.get('content', '').strip()
        return {"title": title, "desc": meta_desc[:200]}
    except Exception as e:
        return {"error": str(e)}

print(quick_crawl("https://rabhanagency.com/"))
