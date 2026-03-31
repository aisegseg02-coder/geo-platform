# 🧪 LOCAL TESTING GUIDE - Production Features

## 📋 Prerequisites

1. **Install new dependencies:**
```bash
cd /media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform
./venv_new/bin/pip install stripe schedule
```

2. **Update .env file:**
```bash
# Add these to your .env file:

# SMTP Configuration (for testing, use Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
FROM_EMAIL=noreply@test.com

# Stripe Test Keys (get from https://dashboard.stripe.com/test/apikeys)
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_key
STRIPE_WEBHOOK_SECRET=whsec_test_your_webhook_secret
STRIPE_PRO_PRICE_ID=price_test_pro
STRIPE_ENTERPRISE_PRICE_ID=price_test_enterprise
```

---

## 🚀 Start the Server

```bash
cd /media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform
./venv_new/bin/python -m uvicorn server.api:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🚀 GEO Platform API starting...
📁 Working directory: /path/to/geo-platform
🐍 Python version: 3.x.x
✅ ai_visibility loaded
✅ ai_analysis loaded
✅ job_queue loaded
...
✅ FastAPI app created
✅ Frontend mounted: /path/to/frontend
🚀 GEO Platform API is ready!
🌐 Access at: http://0.0.0.0:8000
❤️  Health check: http://0.0.0.0:8000/health
```

---

## ✅ Test 1: Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "service": "GEO Platform"
}
```

---

## ✅ Test 2: Security Module

### Test Password Reset

```bash
# 1. Create test user first (if not exists)
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'

# 2. Request password reset
curl -X POST http://localhost:8000/api/auth/request-reset \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

**Expected:**
```json
{
  "ok": true,
  "message": "If email exists, reset link sent"
}
```

**Check:** Look in `output/security.db` for reset token:
```bash
sqlite3 output/security.db "SELECT * FROM password_reset_tokens ORDER BY created_at DESC LIMIT 1;"
```

### Test API Key Generation

```bash
# 1. Login first
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'

# Save the token from response

# 2. Create API key
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "name": "Test API Key",
    "permissions": "read"
  }'
```

**Expected:**
```json
{
  "ok": true,
  "api_key": "geo_xxxxxxxxxxxxxxxxxxxxx"
}
```

### Test Audit Logs

```bash
curl http://localhost:8000/api/audit-logs \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected:**
```json
{
  "ok": true,
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "action": "login",
      "resource": "auth",
      "created_at": "2025-01-XX..."
    }
  ]
}
```

---

## ✅ Test 3: Backup System

### Create Backup

```bash
curl -X POST http://localhost:8000/api/backup/create \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "manifest": {
    "timestamp": "20250128_120000",
    "created_at": "2025-01-28T12:00:00",
    "files": ["jobs.db", "users.db", "security.db", ...],
    "compressed": true,
    "archive_path": "output/backups/backup_20250128_120000.tar.gz",
    "size_mb": 2.5
  }
}
```

**Check:** Verify backup file exists:
```bash
ls -lh output/backups/
```

### List Backups

```bash
curl http://localhost:8000/api/backup/list \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Test Backup Status

```bash
curl http://localhost:8000/api/backup/status \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "status": {
    "total_backups": 1,
    "total_size_mb": 2.5,
    "latest_backup": {
      "name": "backup_20250128_120000",
      "created_at": "2025-01-28T12:00:00",
      "size_mb": 2.5
    },
    "backup_dir": "output/backups",
    "cloud_configured": {
      "s3": false,
      "gcs": false
    }
  }
}
```

---

## ✅ Test 4: Payment System

### Get Subscription

```bash
curl http://localhost:8000/api/subscription \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "subscription": {
    "id": 1,
    "user_id": 1,
    "plan": "free",
    "status": "active",
    "plan_details": {
      "name": "Free",
      "price": 0,
      "features": {
        "crawls_per_month": 5,
        "max_pages_per_crawl": 3,
        "competitor_analysis": false,
        "ai_content_generation": false
      }
    }
  }
}
```

### Check Usage

```bash
curl http://localhost:8000/api/subscription/usage \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "usage": {
    "crawls": 0
  }
}
```

### Test Usage Tracking

```bash
# Run a crawl
curl -X POST http://localhost:8000/api/crawl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://example.com",
    "org_name": "Test",
    "org_url": "https://example.com",
    "max_pages": 1
  }'

# Check usage again
curl http://localhost:8000/api/subscription/usage \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "usage": {
    "crawls": 1
  }
}
```

### Test Usage Limit

```bash
# Try to exceed free plan limit (5 crawls)
# Run 6 crawls and the 6th should fail

for i in {1..6}; do
  echo "Crawl $i"
  curl -X POST http://localhost:8000/api/crawl \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -d '{
      "url": "https://example.com",
      "org_name": "Test",
      "org_url": "https://example.com",
      "max_pages": 1
    }'
  sleep 2
done
```

**Expected on 6th crawl:**
```json
{
  "ok": false,
  "error": "Usage limit exceeded",
  "limit": 5,
  "used": 5,
  "upgrade_url": "/billing"
}
```

---

## ✅ Test 5: Notifications

### Get Notification Preferences

```bash
curl http://localhost:8000/api/notifications/preferences \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "preferences": {
    "user_id": 1,
    "email_enabled": true,
    "webhook_enabled": false,
    "push_enabled": false,
    "webhook_url": null,
    "email_frequency": "instant"
  }
}
```

### Update Preferences

```bash
curl -X POST http://localhost:8000/api/notifications/preferences \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email_enabled": true,
    "webhook_enabled": true,
    "webhook_url": "https://webhook.site/your-unique-url"
  }'
```

### Get Notifications

```bash
curl http://localhost:8000/api/notifications \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
```json
{
  "ok": true,
  "notifications": [
    {
      "id": 1,
      "type": "job_complete",
      "title": "✅ Analysis Complete",
      "message": "Your SEO analysis (Job #1) is ready! GEO Score: 75/100",
      "read": false,
      "created_at": "2025-01-28T12:00:00"
    }
  ]
}
```

---

## 🔍 Database Inspection

### Check all databases created:

```bash
ls -lh output/*.db
```

**Expected:**
```
jobs.db          # Job queue
users.db         # Users and companies
security.db      # Security tokens and API keys
payments.db      # Subscriptions and payments
notifications.db # Notifications
```

### Inspect Security DB:

```bash
sqlite3 output/security.db

# List tables
.tables

# Check API keys
SELECT * FROM api_keys;

# Check audit logs
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;

# Exit
.quit
```

### Inspect Payment DB:

```bash
sqlite3 output/payments.db

# Check subscriptions
SELECT * FROM subscriptions;

# Check usage
SELECT * FROM usage;

# Exit
.quit
```

---

## 📊 Test Dashboard Access

Open in browser:

1. **Homepage:** http://localhost:8000/
2. **API Docs:** http://localhost:8000/docs
3. **Jobs:** http://localhost:8000/jobs.html
4. **Competitor Intel:** http://localhost:8000/competitor-intel.html
5. **GEO Services:** http://localhost:8000/geo-toolkit.html
6. **Ads Dashboard:** http://localhost:8000/ads.html

---

## 🐛 Troubleshooting

### Issue: Module import errors

**Solution:**
```bash
./venv_new/bin/pip install -r requirements.txt
```

### Issue: Database errors

**Solution:**
```bash
# Delete old databases and restart
rm output/*.db
# Restart server - databases will be recreated
```

### Issue: SMTP errors

**Solution:**
```bash
# For Gmail, create App Password:
# 1. Go to Google Account settings
# 2. Security > 2-Step Verification
# 3. App passwords > Generate
# 4. Use that password in SMTP_PASS
```

### Issue: Stripe errors

**Solution:**
```bash
# Use test mode keys from:
# https://dashboard.stripe.com/test/apikeys
# No real charges will be made
```

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Health check returns 200
- [ ] Can create user account
- [ ] Can login and get token
- [ ] Can create API key
- [ ] Can create backup
- [ ] Can view subscription
- [ ] Usage tracking works
- [ ] Notifications are created
- [ ] All databases exist
- [ ] API docs accessible at /docs

---

## 📝 Next Steps After Testing

1. **If all tests pass:**
   - Update .env with real API keys
   - Set up Stripe account
   - Configure SMTP for production
   - Push to GitHub/HuggingFace

2. **If tests fail:**
   - Check server logs
   - Verify .env configuration
   - Check database permissions
   - Review error messages

---

## 🎯 Quick Test Script

Save this as `test_production_features.sh`:

```bash
#!/bin/bash

echo "🧪 Testing Production Features..."
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Health Check
echo "1️⃣ Testing Health Check..."
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

# Test 2: API Docs
echo "2️⃣ Testing API Docs..."
curl -s $BASE_URL/docs | grep -q "FastAPI" && echo "✅ API Docs working" || echo "❌ API Docs failed"
echo ""

# Test 3: Database Files
echo "3️⃣ Checking Databases..."
for db in jobs users security payments notifications; do
  if [ -f "output/${db}.db" ]; then
    echo "✅ ${db}.db exists"
  else
    echo "❌ ${db}.db missing"
  fi
done
echo ""

# Test 4: Backup Directory
echo "4️⃣ Checking Backup System..."
if [ -d "output/backups" ]; then
  echo "✅ Backup directory exists"
  echo "   Backups: $(ls output/backups/ 2>/dev/null | wc -l)"
else
  echo "❌ Backup directory missing"
fi
echo ""

echo "✅ Basic tests complete!"
echo "📖 See LOCAL_TESTING_GUIDE.md for detailed tests"
```

Run it:
```bash
chmod +x test_production_features.sh
./test_production_features.sh
```

---

## 🎉 You're Ready!

Your GEO Platform now has:
- ✅ Enterprise-grade security
- ✅ Automated backups
- ✅ Payment processing
- ✅ Usage tracking
- ✅ Notification system

**Test everything locally, then we'll push to production!**
