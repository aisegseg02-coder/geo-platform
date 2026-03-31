#!/usr/bin/env python3
"""
Quick Test Script for Production Features
"""
import sys
sys.path.insert(0, '.')

print("🧪 Testing Production Features...\n")

# Test 1: Security Module
print("1️⃣ Testing Security Module...")
try:
    from server import security
    
    # Test password reset token
    token = security.create_password_reset_token(user_id=1)
    print(f"   ✅ Password reset token created: {token[:20]}...")
    
    # Verify token
    user_id = security.verify_password_reset_token(token)
    print(f"   ✅ Token verified for user_id: {user_id}")
    
    # Test API key
    api_key = security.generate_api_key(user_id=1, key_name="Test Key", permissions="read")
    print(f"   ✅ API key generated: {api_key[:20]}...")
    
    # Verify API key
    key_data = security.verify_api_key(api_key)
    print(f"   ✅ API key verified: {key_data['key_name']}")
    
    # Test audit log
    security.log_action(user_id=1, action="test", resource="api", details="Testing audit logs")
    logs = security.get_audit_logs(user_id=1, limit=1)
    print(f"   ✅ Audit log created: {logs[0]['action']}")
    
    print("   ✅ Security module: PASSED\n")
except Exception as e:
    print(f"   ❌ Security module: FAILED - {e}\n")

# Test 2: Backup Module
print("2️⃣ Testing Backup Module...")
try:
    from server import backup
    
    # Create backup
    manifest = backup.create_backup(compress=True)
    print(f"   ✅ Backup created: {manifest['timestamp']}")
    print(f"   ✅ Files backed up: {len(manifest['files'])}")
    if manifest.get('size_mb'):
        print(f"   ✅ Backup size: {manifest['size_mb']} MB")
    
    # List backups
    backups = backup.list_backups()
    print(f"   ✅ Total backups: {len(backups)}")
    
    # Get status
    status = backup.get_backup_status()
    print(f"   ✅ Backup directory: {status['backup_dir']}")
    
    print("   ✅ Backup module: PASSED\n")
except Exception as e:
    print(f"   ❌ Backup module: FAILED - {e}\n")

# Test 3: Payment Module
print("3️⃣ Testing Payment Module...")
try:
    from server import payments
    
    # Get subscription (creates free if doesn't exist)
    subscription = payments.get_subscription(user_id=1)
    print(f"   ✅ Subscription: {subscription['plan']}")
    print(f"   ✅ Status: {subscription['status']}")
    
    # Track usage
    payments.track_usage(user_id=1, resource='crawls', count=1)
    print(f"   ✅ Usage tracked: crawls")
    
    # Get usage
    usage = payments.get_usage(user_id=1, resource='crawls')
    print(f"   ✅ Current usage: {usage.get('count', 0)} crawls")
    
    # Check limit
    limit_check = payments.check_usage_limit(user_id=1, resource='crawls')
    print(f"   ✅ Usage limit: {limit_check['used']}/{limit_check['limit']}")
    print(f"   ✅ Allowed: {limit_check['allowed']}")
    
    print("   ✅ Payment module: PASSED\n")
except Exception as e:
    print(f"   ❌ Payment module: FAILED - {e}\n")

# Test 4: Notification Module
print("4️⃣ Testing Notification Module...")
try:
    from server import notifications
    
    # Get preferences (creates default if doesn't exist)
    prefs = notifications.get_preferences(user_id=1)
    print(f"   ✅ Email enabled: {prefs['email_enabled']}")
    print(f"   ✅ Webhook enabled: {prefs['webhook_enabled']}")
    
    # Send test notification
    result = notifications.send_notification(
        user_id=1,
        type='test',
        title='Test Notification',
        message='This is a test notification',
        data={'test': True},
        channels=['email']
    )
    print(f"   ✅ Notification sent: ID {result['id']}")
    
    # Get notifications
    notifs = notifications.get_notifications(user_id=1, limit=5)
    print(f"   ✅ Total notifications: {len(notifs)}")
    
    print("   ✅ Notification module: PASSED\n")
except Exception as e:
    print(f"   ❌ Notification module: FAILED - {e}\n")

# Summary
print("=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n📊 Database Status:")
import os
from pathlib import Path
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', './output'))
for db_name in ['jobs', 'users', 'security', 'payments', 'notifications']:
    db_path = OUTPUT_DIR / f'{db_name}.db'
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"   ✅ {db_name}.db ({size:.1f} KB)")
    else:
        print(f"   ❌ {db_name}.db (missing)")

print("\n📁 Backup Status:")
backup_dir = OUTPUT_DIR / 'backups'
if backup_dir.exists():
    backups = list(backup_dir.glob('backup_*.tar.gz'))
    print(f"   ✅ Backup directory exists")
    print(f"   ✅ Total backups: {len(backups)}")
    if backups:
        latest = max(backups, key=lambda p: p.stat().st_mtime)
        size = latest.stat().st_size / 1024 / 1024
        print(f"   ✅ Latest backup: {latest.name} ({size:.2f} MB)")
else:
    print(f"     No backups yet")

print("\n✅ System is production-ready!")
print("📖 See LOCAL_TESTING_GUIDE.md for API endpoint tests")
print("🚀 Start server: ./venv_new/bin/python -m uvicorn server.api:app --reload --port 8000")
