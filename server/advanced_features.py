"""
GEO Platform — Advanced Features Module
Covers: keyword tracking, scheduled crawls, smart alerts, email reports,
        competitor gap analysis, bulk URL analysis.
"""
import os
import json
import sqlite3
import smtplib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional

_OUTPUT = Path(os.environ.get('OUTPUT_DIR', Path(__file__).resolve().parent.parent / 'output'))
_OUTPUT.mkdir(parents=True, exist_ok=True)
DB_PATH = _OUTPUT / 'jobs.db'


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn():
    c = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    return c


def init_advanced_tables():
    """Create tables for keyword tracking, alerts, and scheduled jobs."""
    c = _conn()
    cur = c.cursor()

    # Keyword history
    cur.execute('''CREATE TABLE IF NOT EXISTS keyword_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        url TEXT,
        keyword TEXT,
        count INTEGER,
        volume INTEGER,
        cpc REAL,
        competition TEXT,
        opportunity_score INTEGER,
        tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # GEO score history
    cur.execute('''CREATE TABLE IF NOT EXISTS geo_score_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        url TEXT,
        score INTEGER,
        status TEXT,
        breakdown TEXT,
        tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Smart alerts
    cur.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        alert_type TEXT,
        message TEXT,
        severity TEXT,
        seen INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Scheduled crawls
    cur.execute('''CREATE TABLE IF NOT EXISTS scheduled_crawls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        org_name TEXT,
        org_url TEXT,
        max_pages INTEGER DEFAULT 3,
        frequency TEXT DEFAULT 'weekly',
        next_run TIMESTAMP,
        last_run TIMESTAMP,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.commit()
    c.close()


# ── Keyword Tracking ──────────────────────────────────────────────────────────

def save_keyword_snapshot(job_id: int, url: str, keywords: List[Dict]):
    """Save keyword data snapshot for trend tracking."""
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    now = datetime.utcnow()
    for kw in keywords[:50]:
        cur.execute('''INSERT INTO keyword_history
            (job_id, url, keyword, count, volume, cpc, competition, opportunity_score, tracked_at)
            VALUES (?,?,?,?,?,?,?,?,?)''', (
            job_id, url,
            kw.get('kw', ''),
            kw.get('count', 0),
            kw.get('volume'),
            kw.get('cpc'),
            kw.get('competition'),
            kw.get('opportunity_score', 0),
            now
        ))
    c.commit()
    c.close()


def save_geo_score_snapshot(job_id: int, url: str, geo_score: Dict):
    """Save GEO score for trend tracking."""
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    cur.execute('''INSERT INTO geo_score_history
        (job_id, url, score, status, breakdown, tracked_at)
        VALUES (?,?,?,?,?,?)''', (
        job_id, url,
        geo_score.get('score', 0),
        geo_score.get('status', ''),
        json.dumps(geo_score.get('breakdown', {})),
        datetime.utcnow()
    ))
    c.commit()
    c.close()


def get_keyword_trends(url: str, keyword: str = None, days: int = 30) -> List[Dict]:
    """Get keyword history for a URL over time."""
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    since = datetime.utcnow() - timedelta(days=days)
    if keyword:
        cur.execute('''SELECT * FROM keyword_history
            WHERE url=? AND keyword=? AND tracked_at > ?
            ORDER BY tracked_at ASC''', (url, keyword, since))
    else:
        cur.execute('''SELECT keyword, MAX(volume) as volume, MAX(opportunity_score) as opp,
            COUNT(*) as snapshots, MAX(tracked_at) as last_seen
            FROM keyword_history WHERE url=? AND tracked_at > ?
            GROUP BY keyword ORDER BY opp DESC LIMIT 30''', (url, since))
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


def get_geo_score_trends(url: str, days: int = 90) -> List[Dict]:
    """Get GEO score history for trend chart."""
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    since = datetime.utcnow() - timedelta(days=days)
    cur.execute('''SELECT score, status, breakdown, tracked_at FROM geo_score_history
        WHERE url=? AND tracked_at > ? ORDER BY tracked_at ASC''', (url, since))
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


# ── Smart Alerts ──────────────────────────────────────────────────────────────

def check_and_create_alerts(job_id: int, url: str, geo_score: Dict, prev_score: Optional[int] = None):
    """Automatically create alerts based on GEO score changes."""
    init_advanced_tables()
    alerts = []
    score = geo_score.get('score', 0)

    # Score drop alert
    if prev_score is not None and score < prev_score - 10:
        alerts.append({
            'url': url, 'alert_type': 'score_drop',
            'message': f'انخفضت درجة GEO من {prev_score}% إلى {score}% — تراجع {prev_score - score} نقطة',
            'severity': 'high'
        })

    # Critical score alert
    if score < 30:
        alerts.append({
            'url': url, 'alert_type': 'critical_score',
            'message': f'درجة GEO حرجة: {score}% — الموقع غير مرئي لمحركات الذكاء الاصطناعي',
            'severity': 'critical'
        })

    # Missing H1 alert
    breakdown = geo_score.get('breakdown', {})
    if breakdown.get('headings', 20) < 5:
        alerts.append({
            'url': url, 'alert_type': 'missing_h1',
            'message': 'عناوين H1 مفقودة أو ضعيفة — يؤثر على الفهرسة',
            'severity': 'medium'
        })

    # No AI visibility
    if breakdown.get('ai_visibility', 20) < 5:
        alerts.append({
            'url': url, 'alert_type': 'no_ai_visibility',
            'message': 'لا يوجد ظهور في محركات الذكاء الاصطناعي — العلامة التجارية غير معروفة',
            'severity': 'high'
        })

    if alerts:
        c = _conn()
        cur = c.cursor()
        for a in alerts:
            cur.execute('''INSERT INTO alerts (url, alert_type, message, severity)
                VALUES (?,?,?,?)''', (a['url'], a['alert_type'], a['message'], a['severity']))
        c.commit()
        c.close()

    return alerts


def get_alerts(url: str = None, unseen_only: bool = False) -> List[Dict]:
    """Get alerts, optionally filtered by URL or unseen status."""
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    query = 'SELECT * FROM alerts WHERE 1=1'
    params = []
    if url:
        query += ' AND url=?'; params.append(url)
    if unseen_only:
        query += ' AND seen=0'
    query += ' ORDER BY created_at DESC LIMIT 50'
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


def mark_alerts_seen(alert_ids: List[int]):
    c = _conn()
    c.execute(f'UPDATE alerts SET seen=1 WHERE id IN ({",".join("?" * len(alert_ids))})', alert_ids)
    c.commit()
    c.close()


# ── Scheduled Crawls ──────────────────────────────────────────────────────────

def add_scheduled_crawl(url: str, org_name: str, org_url: str,
                         max_pages: int = 3, frequency: str = 'weekly') -> int:
    """Schedule a recurring crawl. frequency: daily | weekly | monthly"""
    init_advanced_tables()
    freq_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
    days = freq_map.get(frequency, 7)
    next_run = datetime.utcnow() + timedelta(days=days)
    c = _conn()
    cur = c.cursor()
    cur.execute('''INSERT INTO scheduled_crawls
        (url, org_name, org_url, max_pages, frequency, next_run, active)
        VALUES (?,?,?,?,?,?,1)''', (url, org_name, org_url, max_pages, frequency, next_run))
    sid = cur.lastrowid
    c.commit()
    c.close()
    return sid


def list_scheduled_crawls() -> List[Dict]:
    init_advanced_tables()
    c = _conn()
    cur = c.cursor()
    cur.execute('SELECT * FROM scheduled_crawls ORDER BY next_run ASC')
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


def delete_scheduled_crawl(schedule_id: int):
    c = _conn()
    c.execute('DELETE FROM scheduled_crawls WHERE id=?', (schedule_id,))
    c.commit()
    c.close()


def run_due_scheduled_crawls():
    """Called by scheduler — enqueues jobs for due scheduled crawls."""
    try:
        from server import job_queue
        init_advanced_tables()
        c = _conn()
        cur = c.cursor()
        now = datetime.utcnow()
        cur.execute('SELECT * FROM scheduled_crawls WHERE active=1 AND next_run <= ?', (now,))
        due = [dict(r) for r in cur.fetchall()]

        for s in due:
            # Enqueue the job
            job_queue.enqueue_job(s['url'], s['org_name'], s['org_url'], s['max_pages'])
            # Update next_run
            freq_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
            days = freq_map.get(s['frequency'], 7)
            next_run = now + timedelta(days=days)
            cur.execute('UPDATE scheduled_crawls SET last_run=?, next_run=? WHERE id=?',
                        (now, next_run, s['id']))

        c.commit()
        c.close()
    except Exception as e:
        print(f'Scheduler error: {e}')


def start_scheduler():
    """Start background scheduler thread."""
    def _loop():
        import time
        while True:
            run_due_scheduled_crawls()
            time.sleep(3600)  # check every hour
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


# ── Competitor Gap Analysis ───────────────────────────────────────────────────

def competitor_keyword_gap(your_keywords: List[str], competitor_url: str,
                            max_pages: int = 3) -> Dict:
    """Find keywords competitor has that you don't."""
    try:
        from src.crawler import crawl_seed
        from server.keyword_engine import extract_keywords_from_audit

        pages = crawl_seed(competitor_url, max_pages=max_pages)
        audit = {'pages': pages}
        comp_kws = extract_keywords_from_audit(audit, top_n=50, enrich=False)
        comp_set = {k.get('kw', '').lower() for k in comp_kws}
        your_set  = {k.lower() for k in your_keywords}

        gaps     = comp_set - your_set
        overlaps = comp_set & your_set

        return {
            'competitor_url': competitor_url,
            'competitor_keywords': len(comp_set),
            'your_keywords': len(your_set),
            'gaps': sorted(list(gaps))[:30],
            'overlaps': sorted(list(overlaps))[:20],
            'gap_count': len(gaps),
            'opportunity_score': min(100, int((len(gaps) / max(len(comp_set), 1)) * 100))
        }
    except Exception as e:
        return {'error': str(e), 'gaps': [], 'gap_count': 0}


# ── Bulk URL Analysis ─────────────────────────────────────────────────────────

def bulk_enqueue(urls: List[str], org_name: str = '', max_pages: int = 2) -> List[int]:
    """Enqueue multiple URLs as separate jobs."""
    from server import job_queue
    job_ids = []
    for url in urls[:10]:  # max 10 at once
        url = url.strip()
        if not url:
            continue
        jid = job_queue.enqueue_job(url, org_name or url, url, max_pages)
        job_ids.append(jid)
    return job_ids


# ── Email Reports ─────────────────────────────────────────────────────────────

def send_email_report(to_email: str, subject: str, html_body: str,
                       smtp_host: str = None, smtp_port: int = 587,
                       smtp_user: str = None, smtp_pass: str = None) -> bool:
    """Send HTML email report via SMTP."""
    smtp_host = smtp_host or os.getenv('SMTP_HOST', '')
    smtp_user = smtp_user or os.getenv('SMTP_USER', '')
    smtp_pass = smtp_pass or os.getenv('SMTP_PASS', '')

    if not smtp_host or not smtp_user:
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = smtp_user
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False


def send_weekly_report(to_email: str, url: str):
    """Build and send a weekly GEO report for a URL."""
    from server.reports import build_html_report
    from server import job_queue

    # Find latest completed job for this URL
    jobs = job_queue.list_jobs(limit=100)
    job = next((j for j in jobs if j.get('url') == url and j.get('status') == 'completed'), None)
    if not job or not job.get('result_path'):
        return False

    html = build_html_report(job['result_path'])
    subject = f'تقرير GEO الأسبوعي — {url}'
    return send_email_report(to_email, subject, html)
