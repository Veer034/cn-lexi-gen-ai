Remove docker images

    docker-compose down

Just for building

    docker-compose build

Build with new code

    docker-compose up --build

Remove old venv

    rm -rf venv

Install Python

    brew install python@3.10

Activiate Env

    #can change the env names
    python3.10 -m venv myvenv
    source myvenv/bin/activate

    python --version

Install library in local VM

    #Required for kafka confluent
    brew install librdkafka


    pip install "numpy<2.0.0"  sentence-transformers torch elasticsearch confluent-kafka httpx aiohttp python-json-logger transformers python-dotenv nltk langdetect fastapi uvicorn gunicorn pydantic asyncio

Start in local

    python3.10 master.py

deactivate your virtual environment if it's active:

    deactivate

command to extract chat response:

    curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{
        "queries": [
        "How is my data stored?"
        ],
        "tenant_id": "tenant123",
        "top_k": 8,
        "threshold": 0.75,
        "metadata_filters": {
        "document_type": ["technical_guide", "best_practice"],
        "author": "database_team",
        "created_after": "2023-01-01",
        "tags": ["performance", "optimization"]
        },
        "generate_answer": true,
        "answer_tone": "professional",
        "max_answer_length": 350
    }'
