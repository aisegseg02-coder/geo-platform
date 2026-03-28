# Hugging Face Space Deployment Guide

## Quick Fix for "No Logs" Issue

### Problem
Your Hugging Face Space shows "No logs" and the app doesn't start.

### Solution

**1. Check Build Logs First**
- Go to your Space settings
- Click on "Logs" tab
- Select "build" (not "container")
- Look for error messages during Docker build

**2. Common Issues & Fixes**

#### Issue: Missing Dependencies
**Fix:** Updated `requirements.txt` with all required packages:
```
requests>=2.28
beautifulsoup4>=4.11
spacy>=3.5
python-dotenv>=1.0
fastapi>=0.95
uvicorn[standard]>=0.22
openai>=1.0
groq>=0.1
lxml>=4.9
html5lib>=1.1
```

#### Issue: No Health Check
**Fix:** Added `/health` endpoint in `server/api.py`:
```python
@app.get('/health')
async def health_check():
    return {'status': 'healthy', 'service': 'GEO Platform'}
```

#### Issue: Large Docker Image
**Fix:** Created `.dockerignore` to exclude unnecessary files:
```
venv_new/
__pycache__/
*.pyc
output/job-*
test_*.py
```

#### Issue: Startup Failures
**Fix:** Created `start.sh` with error handling:
```bash
#!/bin/bash
set -e
mkdir -p /tmp/geo-output
python -m spacy download en_core_web_sm
exec uvicorn server.api:app --host 0.0.0.0 --port 7860
```

**3. Environment Variables**

Hugging Face Spaces requires secrets to be set in Settings > Repository secrets:

Required secrets:
- `OPENAI_API_KEY` - For AI analysis
- `GROQ_API_KEY` - Alternative AI backend
- `SERPAPI_KEY` - For search analysis (optional)

**4. Dockerfile Configuration**

Updated Dockerfile includes:
- Health check endpoint
- Proper timeout settings
- Startup script for graceful error handling
- Minimal system dependencies

**5. Verify Deployment**

After pushing changes:

```bash
git add .
git commit -m "fix: Hugging Face Space deployment configuration"
git push
```

Then check:
1. Build logs complete without errors
2. Container logs show "Starting FastAPI server"
3. Health check returns 200 OK
4. App loads at your-space-url.hf.space

**6. Test Locally First**

Before deploying to Hugging Face:

```bash
# Build Docker image
docker build -t geo-platform .

# Run container
docker run -p 7860:7860 geo-platform

# Test health endpoint
curl http://localhost:7860/health
```

**7. Debugging Container Logs**

If container still shows "No logs":

1. Check Space is set to "Running" (not "Sleeping")
2. Verify port 7860 is exposed in Dockerfile
3. Check app_port in README.md matches (should be 7860)
4. Restart the Space from Settings

**8. README.md Configuration**

Ensure your README.md has correct metadata:

```yaml
---
title: GEO Platform
emoji: 🌍
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---
```

## Success Indicators

✅ Build logs show "Successfully built"
✅ Container logs show "Starting FastAPI server"
✅ `/health` endpoint returns 200
✅ Homepage loads without errors
✅ No "Application startup failed" errors

## Still Not Working?

1. Check Hugging Face Space status page
2. Verify your account has Docker SDK enabled
3. Try rebuilding from Settings > Factory reboot
4. Check Space visibility (Public vs Private)
5. Review Hugging Face Spaces documentation

## Performance Optimization

For production deployment:
- Enable persistent storage for database
- Set up proper logging
- Configure rate limiting
- Add monitoring endpoints
- Use environment variables for all secrets

## Support

If issues persist:
- Check Hugging Face Community forums
- Review Space logs carefully
- Test Docker build locally first
- Verify all dependencies are compatible
