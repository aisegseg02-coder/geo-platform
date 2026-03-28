"""
Notification System - Email, Webhooks, Browser Push
"""
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import requests
from server.security import send_email

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', './output'))
NOTIF_DB = OUTPUT_DIR / 'notifications.db'

def init_notification_db():
    """Initialize notification tables"""
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    
    # Notification preferences
    c.execute('''CREATE TABLE IF NOT EXISTS notification_preferences (
        user_id INTEGER PRIMARY KEY,
        email_enabled BOOLEAN DEFAULT 1,
        webhook_enabled BOOLEAN DEFAULT 0,
        push_enabled BOOLEAN DEFAULT 0,
        webhook_url TEXT,
        email_frequency TEXT DEFAULT 'instant',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Notification history
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT,
        data TEXT,
        channels TEXT,
        status TEXT DEFAULT 'pending',
        read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# ── Notification Preferences ────────────────────────────────────────────────

def get_preferences(user_id: int) -> dict:
    """Get user notification preferences"""
    conn = sqlite3.connect(str(NOTIF_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM notification_preferences WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    
    # Create default preferences
    return create_preferences(user_id)

def create_preferences(user_id: int) -> dict:
    """Create default notification preferences"""
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    c.execute('INSERT INTO notification_preferences (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    return get_preferences(user_id)

def update_preferences(user_id: int, **kwargs) -> dict:
    """Update notification preferences"""
    allowed_fields = ['email_enabled', 'webhook_enabled', 'push_enabled', 
                     'webhook_url', 'email_frequency']
    
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return get_preferences(user_id)
    
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    c.execute(f'UPDATE notification_preferences SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()
    
    return get_preferences(user_id)

# ── Send Notifications ──────────────────────────────────────────────────────

def send_notification(user_id: int, type: str, title: str, message: str, 
                     data: dict = None, channels: List[str] = None):
    """Send notification via configured channels"""
    prefs = get_preferences(user_id)
    
    if channels is None:
        channels = []
        if prefs['email_enabled']:
            channels.append('email')
        if prefs['webhook_enabled'] and prefs['webhook_url']:
            channels.append('webhook')
        if prefs['push_enabled']:
            channels.append('push')
    
    # Store notification
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO notifications 
                 (user_id, type, title, message, data, channels, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, type, title, message, json.dumps(data or {}), 
               json.dumps(channels), 'pending'))
    notif_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Send via channels
    results = {}
    
    if 'email' in channels:
        results['email'] = send_email_notification(user_id, title, message, data)
    
    if 'webhook' in channels and prefs['webhook_url']:
        results['webhook'] = send_webhook_notification(prefs['webhook_url'], 
                                                       type, title, message, data)
    
    if 'push' in channels:
        results['push'] = send_push_notification(user_id, title, message, data)
    
    # Update status
    status = 'sent' if any(results.values()) else 'failed'
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    c.execute('UPDATE notifications SET status = ? WHERE id = ?', (status, notif_id))
    conn.commit()
    conn.close()
    
    return {'id': notif_id, 'results': results}

def send_email_notification(user_id: int, title: str, message: str, data: dict = None) -> bool:
    """Send email notification"""
    # Get user email
    from server.users import get_user
    user = get_user(user_id)
    if not user:
        return False
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">🔔 {title}</h2>
        <p>{message}</p>
        {f'<pre style="background: #f5f5f5; padding: 15px; border-radius: 5px;">{json.dumps(data, indent=2)}</pre>' if data else ''}
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            GEO Platform - AI-Powered SEO Analysis
        </p>
    </body>
    </html>
    """
    
    return send_email(user['email'], title, html)

def send_webhook_notification(webhook_url: str, type: str, title: str, 
                              message: str, data: dict = None) -> bool:
    """Send webhook notification"""
    try:
        payload = {
            'type': type,
            'title': title,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Webhook failed: {e}")
        return False

def send_push_notification(user_id: int, title: str, message: str, data: dict = None) -> bool:
    """Send browser push notification (placeholder)"""
    # Implement with web push libraries
    # For now, just return True
    return True

# ── Notification Templates ──────────────────────────────────────────────────

def notify_job_complete(user_id: int, job_id: int, score: int):
    """Notify when analysis job completes"""
    send_notification(
        user_id,
        'job_complete',
        '✅ Analysis Complete',
        f'Your SEO analysis (Job #{job_id}) is ready! GEO Score: {score}/100',
        {'job_id': job_id, 'score': score}
    )

def notify_score_change(user_id: int, url: str, old_score: int, new_score: int):
    """Notify when GEO score changes significantly"""
    change = new_score - old_score
    emoji = '📈' if change > 0 else '📉'
    
    send_notification(
        user_id,
        'score_change',
        f'{emoji} Score Changed',
        f'GEO score for {url} changed from {old_score} to {new_score} ({change:+d} points)',
        {'url': url, 'old_score': old_score, 'new_score': new_score, 'change': change}
    )

def notify_competitor_found(user_id: int, competitor: str, url: str):
    """Notify when new competitor detected"""
    send_notification(
        user_id,
        'competitor_found',
        '🔍 New Competitor Detected',
        f'Found new competitor: {competitor} for {url}',
        {'competitor': competitor, 'url': url}
    )

def notify_usage_limit(user_id: int, resource: str, limit: int):
    """Notify when approaching usage limit"""
    send_notification(
        user_id,
        'usage_limit',
        '⚠️ Usage Limit Warning',
        f'You\'ve used 80% of your {resource} quota ({limit} per month). Consider upgrading.',
        {'resource': resource, 'limit': limit}
    )

def notify_payment_success(user_id: int, amount: int, plan: str):
    """Notify successful payment"""
    send_notification(
        user_id,
        'payment_success',
        '💳 Payment Successful',
        f'Your payment of ${amount/100:.2f} for {plan} plan was successful.',
        {'amount': amount, 'plan': plan}
    )

def notify_subscription_expiring(user_id: int, days_left: int):
    """Notify when subscription is expiring"""
    send_notification(
        user_id,
        'subscription_expiring',
        '⏰ Subscription Expiring Soon',
        f'Your subscription expires in {days_left} days. Renew to keep access.',
        {'days_left': days_left}
    )

# ── Get Notifications ───────────────────────────────────────────────────────

def get_notifications(user_id: int, unread_only: bool = False, limit: int = 50) -> list:
    """Get user notifications"""
    conn = sqlite3.connect(str(NOTIF_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if unread_only:
        c.execute('''SELECT * FROM notifications WHERE user_id = ? AND read = 0 
                     ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    else:
        c.execute('''SELECT * FROM notifications WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    
    notifications = []
    for row in c.fetchall():
        notif = dict(row)
        notif['data'] = json.loads(notif['data']) if notif['data'] else {}
        notif['channels'] = json.loads(notif['channels']) if notif['channels'] else []
        notifications.append(notif)
    
    conn.close()
    return notifications

def mark_read(notification_ids: List[int], user_id: int):
    """Mark notifications as read"""
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    placeholders = ','.join(['?' for _ in notification_ids])
    c.execute(f'UPDATE notifications SET read = 1 WHERE id IN ({placeholders}) AND user_id = ?',
              notification_ids + [user_id])
    conn.commit()
    conn.close()

def delete_notification(notification_id: int, user_id: int):
    """Delete notification"""
    conn = sqlite3.connect(str(NOTIF_DB))
    c = conn.cursor()
    c.execute('DELETE FROM notifications WHERE id = ? AND user_id = ?', 
              (notification_id, user_id))
    conn.commit()
    conn.close()

# Initialize on import
try:
    init_notification_db()
except Exception as e:
    print(f"⚠️  Notification DB init failed: {e}")
