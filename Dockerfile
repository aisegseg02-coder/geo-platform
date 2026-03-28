FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model (with retry)
RUN python -m spacy download en_core_web_sm || \
    python -m spacy download en_core_web_sm || \
    echo "spaCy model download failed, will retry at startup"

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p /tmp/geo-output
ENV OUTPUT_DIR=/tmp/geo-output

# Expose port
EXPOSE 7860

# Start application
CMD ["python", "-m", "uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
