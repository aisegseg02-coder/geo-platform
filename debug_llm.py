import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from server.geo_services import _llm

ans = _llm("Return JSON with key 'test' and value 'hello'", {}, json_mode=True)
print("LLM RESPONSE:", repr(ans))
