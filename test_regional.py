import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from server.geo_services import geo_regional_analysis

res = geo_regional_analysis("Rabhan Agency")
print(res)
