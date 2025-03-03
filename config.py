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
    'analytics_output_topic': os.getenv('DATA_EXTRACTOR_AI_ANALYTICS_TOPIC', 'data.extractor.ai.analytics')
}

MISTRAL_CONFIG = {
    'service_url': os.getenv('MISTRAL_SERVICE_URL', 'http://localhost:11434/api/chat'),
    'model': os.getenv('MISTRAL_MODEL', 'mistral'),
    'timeout': 120,
}