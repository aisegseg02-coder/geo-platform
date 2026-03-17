#!/bin/bash
# Start GEO Platform server with DataForSEO credentials

export DATAFORSEO_LOGIN=ai.seg01@seginvest.com
export DATAFORSEO_PASSWORD=712e269a1e24e50f

echo "🚀 Starting GEO Platform server..."
echo "📊 DataForSEO enrichment: ENABLED"
echo "🔑 Login: $DATAFORSEO_LOGIN"
echo ""

cd "$(dirname "$0")"
python3 -m uvicorn server.api:app --host 0.0.0.0 --port 8000 --reload
