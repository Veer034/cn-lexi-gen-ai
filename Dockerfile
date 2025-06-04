FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    librdkafka-dev \
    g++ \
    pkg-config \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages in stages to resolve dependency conflicts
# Core dependencies first
RUN pip install --no-cache-dir \
    "numpy<2.0.0" \
    elasticsearch[async]==7.17.9 \
    confluent-kafka==2.3.0 \
    httpx==0.27.0 \
    aiohttp==3.9.5 \
    python-json-logger==3.2.1 \
    python-dotenv==1.0.1 \
    fastapi==0.110.0 \
    uvicorn[standard]==0.27.1 \
    gunicorn==21.2.0 \
    pydantic==2.5.2 \
    aiokafka==0.10.0 \
    asyncio==3.4.3

# Install regex with a version that satisfies all requirements
RUN pip install --no-cache-dir regex==2022.10.31

# Install transformers, sentence-transformers and torch
RUN pip install --no-cache-dir \
    transformers==4.49.0 \
    torch==2.2.2+cpu -f https://download.pytorch.org/whl/torch_stable.html \
    sentence-transformers==3.4.1

# Install nltk
RUN pip install --no-cache-dir nltk==3.8.1

# Install language detection packages
RUN pip install --no-cache-dir \
    langdetect==1.0.9 \
    fasttext==0.9.2 \
    lingua-language-detector==1.3.2 \
    pycld2==0.41 

# Install polyglot last
RUN pip install --no-cache-dir polyglot==16.7.4

# Copy application files
COPY . /app/

# Expose port for FastAPI
EXPOSE 9001

# Command to run the application
CMD ["python", "master.py"]