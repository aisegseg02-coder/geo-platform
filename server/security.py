"""
Security Module - Password Reset, Email Verification, API Keys, Audit Logs
"""
import os
import secrets
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', './output'))
SECURITY_DB = OUTPUT_DIR / 'security.db'

def init_security_db():
    """Initialize security tables"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    
    # Password reset tokens
    c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Email verification tokens
    c.execute('''CREATE TABLE IF NOT EXISTS email_verification_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        verified BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # API keys
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key_name TEXT NOT NULL,
        api_key TEXT NOT NULL UNIQUE,
        key_hash TEXT NOT NULL,
        permissions TEXT DEFAULT 'read',
        rate_limit INTEGER DEFAULT 100,
        last_used TIMESTAMP,
        expires_at TIMESTAMP,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Audit logs
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        resource TEXT,
        details TEXT,
        ip_address TEXT,
        user_agent TEXT,
        status TEXT DEFAULT 'success',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# ── Password Reset ──────────────────────────────────────────────────────────

def create_password_reset_token(user_id: int) -> str:
    """Generate password reset token"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO password_reset_tokens (user_id, token, expires_at)
                 VALUES (?, ?, ?)''', (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return token

def verify_password_reset_token(token: str) -> Optional[int]:
    """Verify reset token and return user_id"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''SELECT user_id, expires_at, used FROM password_reset_tokens 
                 WHERE token = ?''', (token,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return None
    
    user_id, expires_at, used = result
    
    if used:
        return None
    
    if datetime.fromisoformat(expires_at) < datetime.utcnow():
        return None
    
    return user_id

def mark_reset_token_used(token: str):
    """Mark token as used"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = ?', (token,))
    conn.commit()
    conn.close()

# ── Email Verification ──────────────────────────────────────────────────────

def create_email_verification_token(user_id: int) -> str:
    """Generate email verification token"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO email_verification_tokens (user_id, token, expires_at)
                 VALUES (?, ?, ?)''', (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return token

def verify_email_token(token: str) -> Optional[int]:
    """Verify email token and return user_id"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''SELECT user_id, expires_at, verified FROM email_verification_tokens 
                 WHERE token = ?''', (token,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return None
    
    user_id, expires_at, verified = result
    
    if verified:
        return None
    
    if datetime.fromisoformat(expires_at) < datetime.utcnow():
        return None
    
    return user_id

def mark_email_verified(token: str):
    """Mark email as verified"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('UPDATE email_verification_tokens SET verified = 1 WHERE token = ?', (token,))
    conn.commit()
    conn.close()

# ── API Key Management ──────────────────────────────────────────────────────

def generate_api_key(user_id: int, key_name: str, permissions: str = 'read', 
                     rate_limit: int = 100, expires_days: int = 365) -> str:
    """Generate API key for user"""
    api_key = f"geo_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO api_keys 
                 (user_id, key_name, api_key, key_hash, permissions, rate_limit, expires_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, key_name, api_key, key_hash, permissions, rate_limit, expires_at))
    conn.commit()
    conn.close()
    
    return api_key

def verify_api_key(api_key: str) -> Optional[dict]:
    """Verify API key and return user info"""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    conn = sqlite3.connect(str(SECURITY_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT * FROM api_keys WHERE key_hash = ? AND active = 1''', (key_hash,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return None
    
    key_data = dict(result)
    
    # Check expiration
    if key_data['expires_at']:
        if datetime.fromisoformat(key_data['expires_at']) < datetime.utcnow():
            conn.close()
            return None
    
    # Update last used
    c.execute('UPDATE api_keys SET last_used = ? WHERE id = ?', 
              (datetime.utcnow(), key_data['id']))
    conn.commit()
    conn.close()
    
    return key_data

def list_api_keys(user_id: int) -> list:
    """List all API keys for user"""
    conn = sqlite3.connect(str(SECURITY_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT id, key_name, permissions, rate_limit, last_used, 
                 expires_at, active, created_at FROM api_keys 
                 WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
    keys = [dict(row) for row in c.fetchall()]
    conn.close()
    return keys

def revoke_api_key(key_id: int, user_id: int) -> bool:
    """Revoke API key"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('UPDATE api_keys SET active = 0 WHERE id = ? AND user_id = ?', 
              (key_id, user_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# ── Audit Logs ──────────────────────────────────────────────────────────────

def log_action(user_id: Optional[int], action: str, resource: str = None, 
               details: str = None, ip_address: str = None, 
               user_agent: str = None, status: str = 'success'):
    """Log user action"""
    conn = sqlite3.connect(str(SECURITY_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO audit_logs 
                 (user_id, action, resource, details, ip_address, user_agent, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, action, resource, details, ip_address, user_agent, status))
    conn.commit()
    conn.close()

def get_audit_logs(user_id: Optional[int] = None, limit: int = 100) -> list:
    """Get audit logs"""
    conn = sqlite3.connect(str(SECURITY_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if user_id:
        c.execute('''SELECT * FROM audit_logs WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    else:
        c.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?', (limit,))
    
    logs = [dict(row) for row in c.fetchall()]
    conn.close()
    return logs

# ── Email Sending ───────────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """Send email via SMTP"""
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    from_email = os.getenv('FROM_EMAIL', smtp_user)
    
    if not all([smtp_host, smtp_user, smtp_pass]):
        print("⚠️  SMTP not configured, email not sent")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False

def send_password_reset_email(email: str, token: str, base_url: str):
    """Send password reset email"""
    reset_link = f"{base_url}/reset-password?token={token}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">🔐 Password Reset Request</h2>
        <p>You requested to reset your password for GEO Platform.</p>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; 
           background: #4F46E5; color: white; text-decoration: none; 
           border-radius: 6px; margin: 20px 0;">Reset Password</a>
        <p style="color: #666; font-size: 14px;">
            This link expires in 1 hour.<br>
            If you didn't request this, please ignore this email.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            GEO Platform - AI-Powered SEO Analysis
        </p>
    </body>
    </html>
    """
    
    return send_email(email, "Reset Your Password - GEO Platform", html)

def send_verification_email(email: str, token: str, base_url: str):
    """Send email verification"""
    verify_link = f"{base_url}/verify-email?token={token}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">✉️ Verify Your Email</h2>
        <p>Welcome to GEO Platform! Please verify your email address.</p>
        <a href="{verify_link}" style="display: inline-block; padding: 12px 24px; 
           background: #10B981; color: white; text-decoration: none; 
           border-radius: 6px; margin: 20px 0;">Verify Email</a>
        <p style="color: #666; font-size: 14px;">
            This link expires in 7 days.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            GEO Platform - AI-Powered SEO Analysis
        </p>
    </body>
    </html>
    """
    
    return send_email(email, "Verify Your Email - GEO Platform", html)

# Initialize on import
try:
    init_security_db()
except Exception as e:
    print(f"⚠️  Security DB init failed: {e}")
