#!/bin/bash
set -e

echo " Starting GEO Platform..."

# Create output directory
mkdir -p /tmp/geo-output

# Check if spaCy model is installed
if ! python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
    echo " Downloading spaCy model..."
    python -m spacy download en_core_web_sm
fi

# Start the server
echo " Starting FastAPI server on port 7860..."
exec uvicorn server.api:app --host 0.0.0.0 --port 7860 --timeout-keep-alive 75
