import os, sys
sys.path.append('.')
from server.content_engine import _call_groq
from dotenv import load_dotenv

load_dotenv()
try:
    print('Testing groq call...')
    print(repr(_call_groq('Say hello world')))
except Exception as e:
    import traceback
    traceback.print_exc()
