import json
from pathlib import Path


def build_html_report(job_dir: str) -> str:
    """Create a simple HTML report combining audit and analysis JSON files located in job_dir."""
    p = Path(job_dir)
    audit_path = p / 'audit.json'
    analysis_path = p / 'analysis.json'
    audit = {}
    analysis = {}
    if audit_path.exists():
        try:
            audit = json.loads(audit_path.read_text(encoding='utf-8'))
        except Exception:
            audit = {}
    if analysis_path.exists():
        try:
            analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
        except Exception:
            analysis = {}

    title = (audit.get('pages', [{}])[0].get('title') if audit.get('pages') else 'GEO Report') or 'GEO Report'
    html = [f"<html><head><meta charset=\"utf-8\"><title>{title}</title></head><body style='font-family:Arial;color:#111;background:#fff;padding:18px'>"]
    html.append(f"<h1>{title}</h1>")
    html.append('<h2>Summary</h2>')
    geo = analysis.get('geo_score') if isinstance(analysis, dict) else None
    if geo:
        html.append(f"<p>GEO Score: <strong>{geo.get('score')}%</strong> — {geo.get('status')}</p>")
    html.append('<h2>Audit</h2>')
    html.append('<pre>'+json.dumps(audit, ensure_ascii=False, indent=2)+'</pre>')
    html.append('<h2>Analysis</h2>')
    html.append('<pre>'+json.dumps(analysis, ensure_ascii=False, indent=2)+'</pre>')
    html.append('</body></html>')
    return '\n'.join(html)


def try_render_pdf(html: str, out_path: Path) -> bool:
    try:
        # optional dependency: weasyprint
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(out_path))
        return True
    except Exception:
        return False
