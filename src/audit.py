import spacy
from collections import Counter

_nlp = None

def load_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            # fall back: prompt user to download model
            raise RuntimeError("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
    return _nlp

def heading_hierarchy_ok(headings):
    # Check for skipped heading levels (simple heuristic)
    levels = [int(h['tag'][1]) for h in headings if h['tag'].startswith('h')]
    if not levels:
        return False
    prev = levels[0]
    for lv in levels[1:]:
        if lv - prev > 1:
            return False
        prev = lv
    return True

def paragraph_density(paragraphs):
    # words per paragraph and average
    counts = [len(p.split()) for p in paragraphs]
    if not counts:
        return { 'avg_words': 0, 'paras': 0 }
    return { 'avg_words': sum(counts)/len(counts), 'paras': len(counts) }

def extract_entities(text):
    nlp = load_nlp()
    doc = nlp(text)
    ents = [ { 'text': e.text, 'label': e.label_ } for e in doc.ents ]
    freq = Counter([e['label'] for e in ents])
    return { 'entities': ents, 'summary': dict(freq) }

def audit_page(page):
    headings_ok = heading_hierarchy_ok(page.get('headings', []))
    density = paragraph_density(page.get('paragraphs', []))
    text_blob = "\n\n".join(page.get('paragraphs', []))[:20000]
    entities = extract_entities(text_blob) if text_blob else { 'entities': [], 'summary': {} }
    return {
        'url': page['url'],
        'title': page.get('title',''),
        'headings_ok': headings_ok,
        'density': density,
        'entities': entities
    }
