"""
Payment System - Stripe Integration with Subscription Plans
"""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', './output'))
PAYMENT_DB = OUTPUT_DIR / 'payments.db'

# Subscription Plans
PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'currency': 'usd',
        'interval': 'month',
        'features': {
            'crawls_per_month': 5,
            'max_pages_per_crawl': 3,
            'competitor_analysis': False,
            'ai_content_generation': False,
            'paid_ads_management': False,
            'api_access': False,
            'priority_support': False,
            'white_label': False
        }
    },
    'pro': {
        'name': 'Professional',
        'price': 29,
        'currency': 'usd',
        'interval': 'month',
        'stripe_price_id': os.getenv('STRIPE_PRO_PRICE_ID'),
        'features': {
            'crawls_per_month': 100,
            'max_pages_per_crawl': 10,
            'competitor_analysis': True,
            'ai_content_generation': True,
            'paid_ads_management': True,
            'api_access': True,
            'priority_support': False,
            'white_label': False
        }
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 99,
        'currency': 'usd',
        'interval': 'month',
        'stripe_price_id': os.getenv('STRIPE_ENTERPRISE_PRICE_ID'),
        'features': {
            'crawls_per_month': -1,  # Unlimited
            'max_pages_per_crawl': 50,
            'competitor_analysis': True,
            'ai_content_generation': True,
            'paid_ads_management': True,
            'api_access': True,
            'priority_support': True,
            'white_label': True
        }
    }
}

def init_payment_db():
    """Initialize payment tables"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    
    # Subscriptions
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        plan TEXT NOT NULL DEFAULT 'free',
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        status TEXT DEFAULT 'active',
        current_period_start TIMESTAMP,
        current_period_end TIMESTAMP,
        cancel_at_period_end BOOLEAN DEFAULT 0,
        trial_end TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Usage tracking
    c.execute('''CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resource TEXT NOT NULL,
        count INTEGER DEFAULT 1,
        period_start TIMESTAMP NOT NULL,
        period_end TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Payment history
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        stripe_payment_id TEXT,
        amount INTEGER NOT NULL,
        currency TEXT DEFAULT 'usd',
        status TEXT DEFAULT 'pending',
        description TEXT,
        invoice_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Invoices
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        stripe_invoice_id TEXT,
        amount_due INTEGER,
        amount_paid INTEGER,
        currency TEXT DEFAULT 'usd',
        status TEXT,
        invoice_pdf TEXT,
        period_start TIMESTAMP,
        period_end TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# ── Subscription Management ─────────────────────────────────────────────────

def get_subscription(user_id: int) -> dict:
    """Get user subscription"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        sub = dict(result)
        sub['plan_details'] = PLANS.get(sub['plan'], PLANS['free'])
        return sub
    
    # Create free subscription if doesn't exist
    return create_subscription(user_id, 'free')

def create_subscription(user_id: int, plan: str = 'free', 
                       stripe_customer_id: str = None,
                       stripe_subscription_id: str = None,
                       trial_days: int = 14) -> dict:
    """Create new subscription"""
    now = datetime.utcnow()
    trial_end = now + timedelta(days=trial_days) if plan != 'free' else None
    period_end = now + timedelta(days=30)
    
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO subscriptions 
                 (user_id, plan, stripe_customer_id, stripe_subscription_id, 
                  current_period_start, current_period_end, trial_end)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, plan, stripe_customer_id, stripe_subscription_id, 
               now, period_end, trial_end))
    conn.commit()
    conn.close()
    
    return get_subscription(user_id)

def update_subscription(user_id: int, plan: str, 
                       stripe_subscription_id: str = None) -> dict:
    """Update subscription plan"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    c.execute('''UPDATE subscriptions 
                 SET plan = ?, stripe_subscription_id = ?, updated_at = ?
                 WHERE user_id = ?''',
              (plan, stripe_subscription_id, datetime.utcnow(), user_id))
    conn.commit()
    conn.close()
    
    return get_subscription(user_id)

def cancel_subscription(user_id: int, immediate: bool = False) -> dict:
    """Cancel subscription"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    
    if immediate:
        c.execute('''UPDATE subscriptions 
                     SET status = 'canceled', plan = 'free', updated_at = ?
                     WHERE user_id = ?''',
                  (datetime.utcnow(), user_id))
    else:
        c.execute('''UPDATE subscriptions 
                     SET cancel_at_period_end = 1, updated_at = ?
                     WHERE user_id = ?''',
                  (datetime.utcnow(), user_id))
    
    conn.commit()
    conn.close()
    
    return get_subscription(user_id)

# ── Usage Tracking ──────────────────────────────────────────────────────────

def track_usage(user_id: int, resource: str, count: int = 1):
    """Track resource usage"""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate period end (last day of month)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    
    # Check if usage record exists for this period
    c.execute('''SELECT id, count FROM usage 
                 WHERE user_id = ? AND resource = ? 
                 AND period_start = ? AND period_end = ?''',
              (user_id, resource, period_start, period_end))
    result = c.fetchone()
    
    if result:
        # Update existing
        usage_id, current_count = result
        c.execute('UPDATE usage SET count = ? WHERE id = ?', 
                  (current_count + count, usage_id))
    else:
        # Create new
        c.execute('''INSERT INTO usage 
                     (user_id, resource, count, period_start, period_end)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, resource, count, period_start, period_end))
    
    conn.commit()
    conn.close()

def get_usage(user_id: int, resource: str = None) -> dict:
    """Get current period usage"""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    conn = sqlite3.connect(str(PAYMENT_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if resource:
        c.execute('''SELECT * FROM usage 
                     WHERE user_id = ? AND resource = ? AND period_start = ?''',
                  (user_id, resource, period_start))
        result = c.fetchone()
        conn.close()
        return dict(result) if result else {'count': 0}
    else:
        c.execute('''SELECT resource, SUM(count) as total FROM usage 
                     WHERE user_id = ? AND period_start = ?
                     GROUP BY resource''',
                  (user_id, period_start))
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return {row['resource']: row['total'] for row in results}

def check_usage_limit(user_id: int, resource: str) -> dict:
    """Check if user has exceeded usage limit"""
    subscription = get_subscription(user_id)
    plan_features = subscription['plan_details']['features']
    
    # Get limit for resource
    limit_key = f"{resource}_per_month"
    limit = plan_features.get(limit_key, 0)
    
    # -1 means unlimited
    if limit == -1:
        return {'allowed': True, 'limit': -1, 'used': 0, 'remaining': -1}
    
    # Get current usage
    usage = get_usage(user_id, resource)
    used = usage.get('count', 0)
    
    return {
        'allowed': used < limit,
        'limit': limit,
        'used': used,
        'remaining': max(0, limit - used)
    }

# ── Stripe Integration ──────────────────────────────────────────────────────

def create_stripe_customer(user_id: int, email: str, name: str = None) -> str:
    """Create Stripe customer"""
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={'user_id': user_id}
        )
        
        # Update subscription with customer ID
        conn = sqlite3.connect(str(PAYMENT_DB))
        c = conn.cursor()
        c.execute('UPDATE subscriptions SET stripe_customer_id = ? WHERE user_id = ?',
                  (customer.id, user_id))
        conn.commit()
        conn.close()
        
        return customer.id
    except Exception as e:
        print(f"❌ Stripe customer creation failed: {e}")
        return None

def create_checkout_session(user_id: int, plan: str, success_url: str, 
                            cancel_url: str) -> dict:
    """Create Stripe checkout session"""
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        plan_data = PLANS.get(plan)
        if not plan_data or plan == 'free':
            return {'error': 'Invalid plan'}
        
        # Get or create customer
        subscription = get_subscription(user_id)
        customer_id = subscription.get('stripe_customer_id')
        
        if not customer_id:
            return {'error': 'Customer not found'}
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan_data['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={'user_id': user_id, 'plan': plan}
        )
        
        return {'session_id': session.id, 'url': session.url}
    except Exception as e:
        return {'error': str(e)}

def handle_webhook(payload: dict, sig_header: str) -> dict:
    """Handle Stripe webhook"""
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        event_type = event['type']
        data = event['data']['object']
        
        if event_type == 'checkout.session.completed':
            # Payment successful
            user_id = int(data['metadata']['user_id'])
            plan = data['metadata']['plan']
            subscription_id = data['subscription']
            
            update_subscription(user_id, plan, subscription_id)
            
            # Record payment
            record_payment(user_id, data['amount_total'], 'succeeded', 
                          data['id'], f"Subscription: {plan}")
        
        elif event_type == 'invoice.payment_succeeded':
            # Recurring payment successful
            user_id = int(data['metadata'].get('user_id', 0))
            if user_id:
                record_payment(user_id, data['amount_paid'], 'succeeded',
                              data['payment_intent'], 'Subscription renewal')
        
        elif event_type == 'customer.subscription.deleted':
            # Subscription canceled
            user_id = int(data['metadata'].get('user_id', 0))
            if user_id:
                cancel_subscription(user_id, immediate=True)
        
        return {'success': True, 'event': event_type}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ── Payment History ─────────────────────────────────────────────────────────

def record_payment(user_id: int, amount: int, status: str, 
                   stripe_payment_id: str = None, description: str = None):
    """Record payment"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    c = conn.cursor()
    c.execute('''INSERT INTO payments 
                 (user_id, stripe_payment_id, amount, status, description)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, stripe_payment_id, amount, status, description))
    conn.commit()
    conn.close()

def get_payment_history(user_id: int, limit: int = 50) -> list:
    """Get payment history"""
    conn = sqlite3.connect(str(PAYMENT_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT * FROM payments WHERE user_id = ? 
                 ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    payments = [dict(row) for row in c.fetchall()]
    conn.close()
    return payments

# ── Billing Portal ──────────────────────────────────────────────────────────

def create_billing_portal_session(user_id: int, return_url: str) -> dict:
    """Create Stripe billing portal session"""
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        subscription = get_subscription(user_id)
        customer_id = subscription.get('stripe_customer_id')
        
        if not customer_id:
            return {'error': 'No customer found'}
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return {'url': session.url}
    except Exception as e:
        return {'error': str(e)}

# Initialize on import
try:
    init_payment_db()
except Exception as e:
    print(f"⚠️  Payment DB init failed: {e}")
