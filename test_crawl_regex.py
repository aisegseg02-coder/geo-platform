import re
import urllib.request
def quick_crawl(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
            
            title = title_match.group(1).strip() if title_match else ""
            desc = desc_match.group(1).strip() if desc_match else ""
            return {"title": title, "desc": desc[:200]}
    except Exception as e:
        return {"error": str(e)}

print(quick_crawl("https://rabhanagency.com/"))
