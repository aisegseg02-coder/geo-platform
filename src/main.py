import argparse
import os
import json
from pathlib import Path

from src import crawler, audit, schema_gen

OUTPUT_DIR = Path.cwd() / "output"


def run_pipeline(url, org_name, org_url, max_pages=5, output_dir: Path = None):
    """
    Run a single crawl+audit+schema generation and write outputs to `output_dir` if provided.
    Returns a dict with keys: pages, audits, audit_path, schema_path
    """
    out_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[main] crawling {url} (max {max_pages}) -> {out_dir}")
    pages = crawler.crawl_seed(url, max_pages=max_pages)
    print(f"[main] crawled {len(pages)} pages")

    audits = []
    faqs = []
    for p in pages:
        a = audit.audit_page(p)
        audits.append(a)
        for h in [h for h in p.get('headings', []) if h['tag'] == 'h3']:
            for para in p.get('paragraphs', [])[:3]:
                if len(para.split()) > 20:
                    faqs.append(schema_gen.make_question_answer(h['text'], para[:500]))
                    break

    # write audit
    audit_obj = {'pages': pages, 'audits': audits}
    audit_path = out_dir / 'audit.json'
    with open(audit_path, 'w', encoding='utf-8') as f:
        json.dump(audit_obj, f, ensure_ascii=False, indent=2)

    # generate schema
    schema = schema_gen.generate_org_and_faq(org_name, org_url, faqs=faqs)
    schema_path = out_dir / 'schema.jsonld'
    with open(schema_path, 'w', encoding='utf-8') as f:
        f.write(schema)

    print(f"[main] outputs written to {out_dir}")
    return { 'pages': pages, 'audits': audits, 'audit_path': str(audit_path), 'schema_path': str(schema_path) }


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--url', required=True, help='Seed URL to crawl')
    p.add_argument('--org-name', required=True, help='Organization name for schema')
    p.add_argument('--org-url', required=True, help='Organization canonical URL for schema')
    p.add_argument('--max-pages', type=int, default=5)
    return p.parse_args()


def main():
    args = parse_args()
    run_pipeline(args.url, args.org_name, args.org_url, max_pages=args.max_pages)


if __name__ == '__main__':
    main()
