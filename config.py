import os
from dotenv import load_dotenv

load_dotenv()


# Config (can be moved to separate file)
ES_CONFIG = {
    'hosts': ['http://localhost:9200'],
    'username': os.getenv('ES_USERNAME', ''),
    'password': os.getenv('ES_PASSWORD', ''),
    'tenant_document_index_name': 'tenant-documents'
}

KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_SERVERS', 'localhost:9092'),
    'analytics_output_topic': os.getenv('DATA_EXTRACTOR_AI_ANALYTICS_TOPIC', 'lexi.gen.ai.analytics')
}

MISTRAL_CONFIG = {
    'chat_url': os.getenv('MISTRAL_CHAT_URL', 'http://localhost:11434/api/chat'),
    'version_url': os.getenv('MISTRAL_VERSION_URL', 'http://localhost:11434/api/version'),
    'model': os.getenv('MISTRAL_MODEL', 'mistral'),
    'timeout': 240,
}