FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir "numpy<2.0.0" \
    sentence-transformers==3.4.1 \
    torch==2.2.2+cpu -f https://download.pytorch.org/whl/torch_stable.html \ 
    elasticsearch[async]==8.17.1 \
    confluent-kafka==2.3.0 \
    httpx==0.27.0 \
    aiohttp==3.9.5 \
    python-json-logger==3.2.1 \
    transformers==4.49.0 \
    python-dotenv==1.0.1 \
    nltk==3.8.1 \
    langdetect==1.0.9 \
    fastapi==0.110.0 \
    uvicorn[standard]==0.27.1 \
    gunicorn==21.2.0 \
    pydantic==2.5.2 \
    aiokafka==0.10.0 \
    asyncio==3.4.3



# Copy your application
# COPY . .

CMD ["python", "master.py"]