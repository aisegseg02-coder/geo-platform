#!/bin/bash

echo " Checking Hugging Face Space Status..."
echo ""

SPACE="alinabil21/geo-platform"
URL="https://alinabil21-geo-platform.hf.space"

# Check runtime status
echo " Runtime Status:"
curl -s "https://huggingface.co/api/spaces/$SPACE/runtime" | python3 -m json.tool
echo ""

# Check if Space is accessible
echo " Testing Space URL:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo " Space is RUNNING! Health check returned 200"
    echo "Response:"
    curl -s "$URL/health" | python3 -m json.tool
elif [ "$HTTP_CODE" = "502" ] || [ "$HTTP_CODE" = "503" ]; then
    echo " Space is BUILDING or STARTING (HTTP $HTTP_CODE)"
    echo "   Wait 2-5 minutes and try again"
elif [ "$HTTP_CODE" = "000" ]; then
    echo " Cannot connect to Space"
    echo "   Check if Space exists and is public"
else
    echo "  Unexpected status: HTTP $HTTP_CODE"
fi
echo ""

# Check homepage
echo " Testing Homepage:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/" 2>/dev/null)
echo "   Homepage: HTTP $HTTP_CODE"
echo ""

echo " Quick Links:"
echo "   Space: https://huggingface.co/spaces/$SPACE"
echo "   Logs: https://huggingface.co/spaces/$SPACE/logs"
echo "   App: $URL"
echo ""

echo " Troubleshooting:"
echo "   1. If BUILDING: Wait 3-5 minutes"
echo "   2. If 502/503: Space is starting, wait 30 seconds"
echo "   3. If 000: Check Space visibility (must be Public)"
echo "   4. Check logs at: https://huggingface.co/spaces/$SPACE/logs"
