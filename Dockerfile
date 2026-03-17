FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy project
COPY . .

# Create output dir
ENV OUTPUT_DIR=/tmp/geo-output
RUN mkdir -p /tmp/geo-output

EXPOSE 8000

CMD ["uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8000"]
