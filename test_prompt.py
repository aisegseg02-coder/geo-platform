import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from server.geo_services import _llm, _quick_crawl

site_data = _quick_crawl("https://rabhanagency.com/")
crawl_context = f"\nWebsite Context (For your reference to identify the industry): Title: {site_data['title']} | Description: {site_data['desc']}"
comp_prompt = f"""Analyze the company/brand 'rabhanagency'.{crawl_context}
Identify its primary industry. 
List 3 top active competitors for it in the Middle East or Global market.
Estimate where 'rabhanagency' ranks among these 3 competitors based on AI visibility (1 being the highest visibility).
Return JSON ONLY:
{{"industry": "technology|finance|etc", "competitors": ["comp1", "comp2", "comp3"], "estimated_rank": 2}}"""

print("PROMPT:", comp_prompt)
ans = _llm(comp_prompt, {}, json_mode=True)
print("ANSWER:", ans)
