import sqlite3
import json
from pathlib import Path
import datetime

DB_PATH = Path(__file__).resolve().parent.parent / 'output' / 'jobs.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn():
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    c = _conn()
    cur = c.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        org_name TEXT,
        org_url TEXT,
        max_pages INTEGER,
        runs INTEGER,
        status TEXT,
        progress TEXT,
        result_path TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    ''')
    # add optional columns for user association if missing
    cur.execute("PRAGMA table_info(jobs)")
    cols = [r[1] for r in cur.fetchall()]
    if 'user_id' not in cols:
        try:
            cur.execute('ALTER TABLE jobs ADD COLUMN user_id INTEGER')
        except Exception:
            pass
    if 'company_id' not in cols:
        try:
            cur.execute('ALTER TABLE jobs ADD COLUMN company_id INTEGER')
        except Exception:
            pass
    c.commit()
    c.close()


def enqueue_job(url, org_name, org_url, max_pages=3, runs=1, user_id=None, company_id=None):
    init_db()
    now = datetime.datetime.utcnow()
    c = _conn()
    cur = c.cursor()
    cur.execute('''INSERT INTO jobs (url,org_name,org_url,max_pages,runs,status,progress,created_at,updated_at,user_id,company_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (url, org_name, org_url, max_pages, runs, 'pending', json.dumps({}), now, now, user_id, company_id))
    jid = cur.lastrowid
    c.commit()
    c.close()
    return jid


def list_jobs(limit=50):
    init_db()
    c = _conn()
    cur = c.cursor()
    cur.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


def get_job(job_id):
    init_db()
    c = _conn()
    cur = c.cursor()
    cur.execute('SELECT * FROM jobs WHERE id=?', (job_id,))
    row = cur.fetchone()
    c.close()
    return dict(row) if row else None


def update_job(job_id, status=None, progress=None, result_path=None):
    init_db()
    c = _conn()
    cur = c.cursor()
    updates = []
    params = []
    if status is not None:
        updates.append('status=?'); params.append(status)
    if progress is not None:
        updates.append('progress=?'); params.append(json.dumps(progress))
    if result_path is not None:
        updates.append('result_path=?'); params.append(result_path)
    params.append(datetime.datetime.utcnow())
    params.append(job_id)
    if updates:
        sql = f"UPDATE jobs SET {', '.join(updates)}, updated_at=? WHERE id=?"
        cur.execute(sql, params)
        c.commit()
    c.close()


def claim_next_job():
    """Atomically find a pending job and claim it by setting status to 'running'. Returns job id or None."""
    init_db()
    c = _conn()
    cur = c.cursor()
    try:
        # simple approach: select a pending job, then update status where id and status still pending
        cur.execute("SELECT id FROM jobs WHERE status='pending' ORDER BY created_at ASC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        jid = row['id']
        now = datetime.datetime.utcnow()
        cur.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=? AND status='pending'", ('running', now, jid))
        if cur.rowcount == 1:
            c.commit()
            cur.execute('SELECT * FROM jobs WHERE id=?', (jid,))
            job = cur.fetchone()
            return dict(job) if job else None
        c.commit()
        return None
    finally:
        c.close()


def claim_job(job_id):
    """Claim a specific job id if it's pending; returns True when claimed."""
    init_db()
    c = _conn()
    cur = c.cursor()
    try:
        now = datetime.datetime.utcnow()
        cur.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=? AND status='pending'", ('running', now, job_id))
        claimed = cur.rowcount == 1
        if claimed:
            c.commit()
            return True
        c.commit()
        return False
    finally:
        c.close()
