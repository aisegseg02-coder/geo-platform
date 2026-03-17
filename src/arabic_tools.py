import re
from typing import List, Dict

ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def is_arabic_text(text: str) -> bool:
    """Return True if text contains Arabic characters."""
    if not text:
        return False
    return bool(ARABIC_CHAR_RE.search(text))


def extract_entities_arabic(text: str) -> Dict:
    """Attempt to extract entities using CAMeL Tools if available; otherwise basic heuristics.

    Returns a dict similar to spaCy output: { 'entities': [ { 'text':..., 'label':... }, ... ], 'summary': {...} }
    """
    try:
        from camel_tools.ner import NERecognizer
        ner = NERecognizer.pretrained()
        tokens = text.split()
        tags = ner.predict_sentence(tokens)
        ents = []
        cur = None
        for tok, tag in zip(tokens, tags):
            if tag != 'O':
                if cur is None:
                    cur = {'text': tok, 'label': tag}
                else:
                    cur['text'] += ' ' + tok
            else:
                if cur:
                    ents.append(cur)
                    cur = None
        if cur:
            ents.append(cur)
        summary = {}
        for e in ents:
            summary[e['label']] = summary.get(e['label'], 0) + 1
        return {'entities': ents, 'summary': summary}
    except Exception:
        # fallback heuristics: phone numbers, percent, numbers, short location heuristics
        ents = []
        phones = re.findall(r"\+?\d[\d\s\-]{6,}\d", text)
        for p in phones:
            ents.append({'text': p, 'label': 'PHONE'})
        # crude location capture: look for 'Cairo' or Arabic equivalents
        if 'القاهرة' in text or 'Cairo' in text:
            ents.append({'text': 'Cairo', 'label': 'GPE'})
        summary = {}
        for e in ents:
            summary[e['label']] = summary.get(e['label'], 0) + 1
        return {'entities': ents, 'summary': summary}


def arabert_embedding_stub(text: str):
    """If `transformers` and AraBERT model available, return embedding vector; else None.
    This is a safe stub that will not fail if libraries are missing.
    """
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        model_name = 'aubmindlab/bert-base-arabertv02'
        tok = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        inputs = tok(text, return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            out = model(**inputs)
        # mean pooling
        vec = out.last_hidden_state.mean(dim=1).squeeze().tolist()
        return vec
    except Exception:
        return None
