About

    LexiGen(Lexicon + Generation) AI understands language, retrieves relevant information, and generates responses based on stored knowledge, making it ideal for AI-powered document search and answer generation.

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

    #make sure version is 3.10.*
    python --version

Install library in local VM

    #Required for kafka confluent
    brew install librdkafka


    pip install "numpy<2.0.0"  sentence-transformers torch elasticsearch confluent-kafka httpx aiohttp python-json-logger transformers python-dotenv nltk langdetect fastapi uvicorn gunicorn pydantic asyncio  fasttext regex

    #For language detection
    pip install langdetect fasttext lingua-language-detector pycld2 polyglot

Start in local

    python3.10 master.py

deactivate your virtual environment if it's active:

    deactivate

# Production Setup

### Login VM

    ssh azureuser@YOUR-VM-PUBLIC-IP

### Install Git

    sudo apt update
    sudo apt install git -y
    git clone https://github.com/Veer034/cn-lexi-gen-ai.git

### Install Python

    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install python3.10 python3.10-venv python3.10-distutils

### Install library in production VM

    pip install "numpy<2.0.0"  sentence-transformers torch elasticsearch confluent-kafka httpx aiohttp python-json-logger transformers python-dotenv nltk langdetect fastapi uvicorn gunicorn pydantic asyncio  fasttext regex

    # Install all required build tools and dependencies for language libraries
    sudo apt update
    sudo apt install -y \
        build-essential \
        g++ \
        gcc \
        python3-dev \
        libicu-dev \
        pkg-config \
        cmake \
        make \
        git \
        libc6-dev \
        linux-headers-generic

    # Install additional tools that FastText needs
    sudo apt install -y \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release

    # Check current GCC version
    gcc --version

    # If GCC is older than 7.x, update it
    sudo apt install -y gcc-9 g++-9
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60
    sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 60

    # Ensure pip build tools are up to date
    pip install --upgrade pip setuptools wheel
    pip install --upgrade build

    #For language detection
    pip install langdetect fasttext lingua-language-detector pycld2 polyglot

### Create Systemd file for as a service execution

    sudo tee /etc/systemd/system/cn-lexi-gen-ai.service > /dev/null << EOF
    [Unit]
    Description=For data forging
    After=network.target ollama.service
    Requires=ollama.service

    [Service]
    Type=simple
    User=azureuser
    WorkingDirectory=/home/azureuser/cn-lexi-gen-ai
    Environment=PATH=/home/azureuser/cn-lexi-gen-ai/myvenv/bin
    ExecStart=/home/azureuser/cn-lexi-gen-ai/myvenv/bin/python master.py
    Restart=always
    RestartSec=10
    StartLimitIntervalSec=0
    StandardOutput=journal
    StandardError=journal

    [Install]
    WantedBy=multi-user.target
    EOF

### HuggingFace model storage location

    ~/.cache/huggingface/

### List all services

    systemctl list-units --type=service
    systemctl list-units --type=service | grep cn-

### Reload systemd

    sudo systemctl daemon-reload

### Enable all services to start on boot

    sudo systemctl enable cn-lexi-gen-ai

### Start Service

    sudo systemctl start cn-lexi-gen-ai

### Check Status

    sudo systemctl status cn-lexi-gen-ai

### Stop service

    sudo systemctl stop cn-lexi-gen-ai

### Restart service

    sudo systemctl restart cn-lexi-gen-ai

### Check logs for specific service

    sudo journalctl -u cn-lexi-gen-ai -f

### Check service generated logs

    tail -n 50 ~/cn-lexi-gen-ai/logs/server.log

### Check logs for that service

    journalctl -u cn-lexi-gen-ai.service

### Rotate the journal for that service (so old logs can be vacuumed)

    sudo journalctl --unit=cn-lexi-gen-ai.service --rotate

### Delete old logs for that service

    sudo journalctl --unit=cn-lexi-gen-ai.service --vacuum-time=1s


    # Or to keep only the last 7 days:
    sudo journalctl --unit=cn-lexi-gen-ai.service --vacuum-time=7d

### List all topics

kafka-topics.sh --list --bootstrap-server 57.159.53.43:9092

### Create a specific topic

kafka-topics.sh --create --topic my-topic --bootstrap-server 57.159.53.43:9092

### Describe a specific topic

kafka-topics.sh --describe --topic tenant.documents.vector.storage.request --bootstrap-server 57.159.53.43:9092

### Describe all topics

kafka-topics.sh --describe --bootstrap-server 57.159.53.43:9092

### Describe multiple specific topics

kafka-topics.sh --describe --topic tenant.documents.vector.storage.request,tenant.faq.vector.storage.request --bootstrap-server 57.159.53.43:9092

command to extract chat response:

    curl -X GET http://localhost:9001/search \
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

Command for health check

    curl -X GET http://localhost:9001/health
