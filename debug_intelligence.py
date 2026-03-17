import requests
import json

def test_intelligence():
    url = "http://localhost:8000/api/search/intelligence"
    payload = {
        "url": "https://mohrek.com/",
        "max_pages": 1,
        "api_keys": {
            "groq": "test_key",
            "openai": "test_key"
        }
    }
    
    print(f"Testing Intelligence Engine for: {payload['url']}")
    try:
        r = requests.post(url, json=payload)
        res = r.json()
        
        if not res.get('ok'):
            print(f"❌ Error: {res.get('error')}")
            return
            
        report = res['report']
        print(f"✅ Report Synchronized")
        print(f"Intent Top: {report['intent_analysis']['top_intent']}")
        print(f"Entities: {json.dumps(report['entities'], indent=2)}")
        print(f"Gaps: {report['content_gaps']}")
        
        # Check if AbayaNoir is still hardcoded
        if "Abaya" in str(report['entities']) or "Abaya" in str(report['content_gaps']):
            print("⚠️ WARNING: Hardcoded 'AbayaNoir' values still present!")
        else:
            print("✨ Success: AI/Dynamic content detected.")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_intelligence()
