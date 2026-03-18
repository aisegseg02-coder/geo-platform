import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from server.geo_services import geo_regional_analysis

res = geo_regional_analysis("https://rabhanagency.com/")
print(json.dumps(res, indent=2, ensure_ascii=False))
