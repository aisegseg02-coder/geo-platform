import os
import sqlite3
import json
import hmac
import hashlib
import binascii
import time
from pathlib import Path

OUTPUT = Path(os.environ.get('OUTPUT_DIR', str(Path(__file__).resolve().parent.parent / 'output')))
OUTPUT.mkdir(parents=True, exist_ok=True)
DB_PATH = OUTPUT / 'users.db'

def get_conn():
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if DB_PATH.exists():
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE companies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      domain TEXT,
      created_at INTEGER
    )
    ''')
    cur.execute('''
    CREATE TABLE users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'user',
      company_id INTEGER,
      created_at INTEGER
    )
    ''')
    cur.execute('''
    CREATE TABLE teams (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      company_id INTEGER,
      created_at INTEGER
    )
    ''')
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return binascii.hexlify(salt).decode() + '$' + binascii.hexlify(dk).decode()


def _verify_password(stored: str, password: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split('$')
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(dk_hex)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def create_company(name: str, domain: str = None):
    conn = get_conn()
    cur = conn.cursor()
    ts = int(time.time())
    cur.execute('INSERT INTO companies (name, domain, created_at) VALUES (?,?,?)', (name, domain, ts))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def create_user(email: str, password: str, role: str = 'user', company_id: int = None):
    conn = get_conn()
    cur = conn.cursor()
    ph = _hash_password(password)
    ts = int(time.time())
    try:
        cur.execute('INSERT INTO users (email, password_hash, role, company_id, created_at) VALUES (?,?,?,?,?)', (email, ph, role, company_id, ts))
        conn.commit()
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise
    conn.close()
    return uid


def authenticate_user(email: str, password: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE email=?', (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if not _verify_password(row['password_hash'], password):
        return None
    return dict(row)


def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id,email,role,company_id,created_at FROM users ORDER BY id DESC')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# Simple token generation using HMAC-SHA256. Not a full JWT but sufficient for local dev.
_SECRET = os.environ.get('USERS_SECRET', 'dev-secret-please-change')

def make_token(user_id: int, expires_in: int = 3600):
    payload = json.dumps({'uid': user_id, 'exp': int(time.time()) + expires_in}, separators=(',',':')).encode('utf-8')
    sig = hmac.new(_SECRET.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return binascii.hexlify(payload).decode() + '.' + sig


def verify_token(token: str):
    try:
        p_hex, sig = token.split('.')
        payload = binascii.unhexlify(p_hex)
        expected = hmac.new(_SECRET.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        obj = json.loads(payload.decode('utf-8'))
        if obj.get('exp',0) < int(time.time()):
            return None
        return obj.get('uid')
    except Exception:
        return None


def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id,email,role,company_id,created_at FROM users WHERE id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)
