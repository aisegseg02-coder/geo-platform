import json
from pathlib import Path
import threading

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_PATH = OUTPUT_DIR / 'cache.json'
_lock = threading.Lock()


def _load():
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d):
    try:
        with _lock:
            with CACHE_PATH.open('w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get(key, default=None):
    d = _load()
    return d.get(key, default)


def set(key, value):
    d = _load()
    d[key] = value
    _save(d)
