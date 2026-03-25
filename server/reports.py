"""Professional GEO Report Generator — client-ready HTML + PDF."""
import json
from pathlib import Path
from datetime import datetime


def build_html_report(job_dir: str) -> str:
    p = Path(job_dir)
    audit = {}
    analysis = {}
    recs = {}

    for fname, target in [('audit.json', 'audit'), ('analysis.json', 'analysis'), ('recommendations.json', 'recs')]:
        path = p / fname
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if target == 'audit':    audit = data
                elif target == 'analysis': analysis = data
                elif target == 'recs':   recs = data
            except Exception:
                pass

    pages   = audit.get('pages', [])
    org     = audit.get('org_name') or (pages[0].get('title') if pages else 'Website')
    url     = audit.get('url') or (pages[0].get('url') if pages else '')
    geo     = analysis.get('geo_score') or {}
    score   = geo.get('score', 0)
    status  = geo.get('status', 'N/A')
    breakdown = geo.get('breakdown', {})
    actions = recs.get('actions', []) if isinstance(recs, dict) else []
    per_page = recs.get('per_page', []) if isinstance(recs, dict) else []
    date_str = datetime.utcnow().strftime('%Y-%m-%d')

    score_color = '#10b981' if score >= 75 else '#f59e0b' if score >= 40 else '#ef4444'

    def bar(val, max_val=20, color='#00f2ff'):
        pct = min(100, int((val / max_val) * 100))
        return f'<div style="background:#e5e7eb;border-radius:4px;height:8px;width:100%"><div style="background:{color};height:8px;border-radius:4px;width:{pct}%"></div></div>'

    # Issues summary
    total_issues = sum(len(p.get('issues', [])) for p in per_page)
    total_pages  = len(pages)

    # Per-page rows
    page_rows = ''
    for pg in per_page[:20]:
        issues = pg.get('issues', [])
        color = '#ef4444' if len(issues) > 1 else '#f59e0b' if issues else '#10b981'
        icon  = '🔴' if len(issues) > 1 else '🟡' if issues else '🟢'
        page_rows += f'''
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;max-width:300px;word-break:break-all">
            <div style="font-weight:600;font-size:13px">{pg.get("title") or pg.get("url","")}</div>
            <div style="color:#6b7280;font-size:11px">{pg.get("url","")}</div>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;text-align:center">{icon}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:12px;color:{color}">
            {"، ".join(issues) if issues else "✅ لا مشاكل"}
          </td>
        </tr>'''

    # Action items
    action_rows = ''
    for i, a in enumerate(actions[:10], 1):
        text = a.get('text', a) if isinstance(a, dict) else a
        priority = a.get('priority', 'MEDIUM') if isinstance(a, dict) else 'MEDIUM'
        p_color = '#ef4444' if priority == 'HIGH' else '#f59e0b' if priority == 'MEDIUM' else '#10b981'
        action_rows += f'''
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;text-align:center;font-weight:700;color:#6b7280">{i}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6">
            <span style="background:{p_color}20;color:{p_color};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700">{priority}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px">{text}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير GEO — {org}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9fafb; color: #111827; direction: rtl; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 40px 24px; }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 32px; }}
  .header h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
  .header p {{ color: #94a3b8; font-size: 14px; }}
  .score-circle {{ display: inline-flex; align-items: center; justify-content: center; width: 100px; height: 100px; border-radius: 50%; border: 6px solid {score_color}; font-size: 28px; font-weight: 900; color: {score_color}; float: left; margin-right: 24px; }}
  .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .card h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; color: #1e293b; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px; }}
  .metric {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .metric-label {{ font-size: 13px; color: #6b7280; }}
  .metric-val {{ font-size: 13px; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #f8fafc; padding: 10px 12px; text-align: right; font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e5e7eb; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
  @media print {{ body {{ background: white; }} .page {{ padding: 20px; }} }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <div style="display:flex;align-items:center;gap:24px">
      <div class="score-circle">{score}%</div>
      <div>
        <h1>تقرير GEO — {org}</h1>
        <p>{url}</p>
        <p style="margin-top:8px">تاريخ التقرير: {date_str} &nbsp;·&nbsp; الحالة: <span style="color:{score_color};font-weight:700">{status}</span></p>
        <p style="margin-top:4px">الصفحات المحللة: {total_pages} &nbsp;·&nbsp; المشاكل المكتشفة: {total_issues}</p>
      </div>
    </div>
  </div>

  <!-- GEO Score Breakdown -->
  <div class="card">
    <h2>📊 تفصيل درجة GEO</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      {''.join(f"""
      <div>
        <div class="metric">
          <span class="metric-label">{label}</span>
          <span class="metric-val" style="color:{'#10b981' if val>=15 else '#f59e0b' if val>=8 else '#ef4444'}">{val}/20</span>
        </div>
        {bar(val)}
      </div>""" for label, val in [
          ('جودة العناوين', breakdown.get('headings', 0)),
          ('كثافة المحتوى', breakdown.get('density', 0)),
          ('الكيانات الدلالية', breakdown.get('entities', 0)),
          ('أسئلة FAQ', breakdown.get('faq', 0)),
          ('الظهور في الذكاء الاصطناعي', breakdown.get('ai_visibility', 0)),
      ])}
    </div>
  </div>

  <!-- Action Plan -->
  <div class="card">
    <h2>💡 خطة العمل ({len(actions)} توصية)</h2>
    {'<p style="color:#6b7280;font-size:13px">لا توجد توصيات — شغّل تحليل الذكاء الاصطناعي أولاً.</p>' if not actions else f'''
    <table>
      <thead><tr><th>#</th><th>الأولوية</th><th>الإجراء المطلوب</th></tr></thead>
      <tbody>{action_rows}</tbody>
    </table>'''}
  </div>

  <!-- Per-page Analysis -->
  <div class="card">
    <h2>🔍 تحليل الصفحات ({total_pages} صفحة)</h2>
    {'<p style="color:#6b7280;font-size:13px">لا توجد بيانات صفحات.</p>' if not per_page else f'''
    <table>
      <thead><tr><th>الصفحة</th><th>الحالة</th><th>المشاكل</th></tr></thead>
      <tbody>{page_rows}</tbody>
    </table>'''}
  </div>

  <!-- AI Visibility -->
  {'<div class="card"><h2>🤖 الظهور في الذكاء الاصطناعي</h2>' + _render_ai_vis(audit.get('ai_visibility', {})) + '</div>' if audit.get('ai_visibility') else ''}

  <div class="footer">
    <p>تم إنشاء هذا التقرير بواسطة <strong>GEO Platform</strong> — منصة تحسين الظهور في محركات البحث الذكية</p>
    <p style="margin-top:4px">{date_str}</p>
  </div>

</div>
</body>
</html>'''
    return html


def _render_ai_vis(ai_vis: dict) -> str:
    if not ai_vis or not ai_vis.get('enabled'):
        reason = ai_vis.get('reason', 'بيانات الظهور غير متاحة — أضف مفتاح Perplexity أو OpenAI') if ai_vis else 'غير مفعّل'
        return f'<p style="color:#6b7280;font-size:13px">{reason}</p>'
    results = ai_vis.get('results', [])
    rows = ''.join(f'''
    <tr>
      <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;font-size:13px">{r.get("query","")}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;text-align:center">
        <span style="color:{'#10b981' if r.get('mentioned') else '#ef4444'};font-weight:700">
          {'✅ موجود' if r.get('mentioned') else '❌ غائب'}
        </span>
      </td>
    </tr>''' for r in results)
    return f'<table><thead><tr><th>الاستعلام</th><th>النتيجة</th></tr></thead><tbody>{rows}</tbody></table>'


def try_render_pdf(html: str, out_path: Path) -> bool:
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(out_path))
        return True
    except Exception:
        return False
