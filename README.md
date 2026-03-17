GEO Platform — Minimal Pipeline

This repository contains a minimal, runnable pipeline that implements the Zaher GEO toolkit workflow from the provided HTML. It crawls a real website (no mock data), runs content audits (headings, density, NER), and generates JSON-LD schema.

Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Run the pipeline against a real site:

```bash
python -m src.main --url https://example.com --org-name "My Org" --org-url https://example.com
```

Outputs are written to `output/` including `audit.json` and `schema.jsonld`.

Notes
- If you have `PERPLEXITY_KEY` in your environment the pipeline will attempt to query Perplexity API for AI visibility checks.
- For local LLM testing, configure Ollama per its docs; this scaffold will not install Ollama automatically.
