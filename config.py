import os
from dotenv import load_dotenv

load_dotenv()


# Config (can be moved to separate file)
ES_CONFIG = {
    'hosts': [
        f"https://{host.strip()}" for host in os.getenv('ES_HOSTS', 'localhost:9200').split(",")
    ],
    'username': os.getenv('ES_USERNAME',''),
    'password': os.getenv('ES_PASSWORD',''),
    'ca_certs': '/usr/local/share/ca-certificates/elasticsearch.crt',  # Point to certificate file
    'verify_certs': False,
    'ssl_show_warn': True,
    'tenant_document_index_name': os.getenv('ES_TENANT_DOCUMENTS_VECTOR_INDEX_NAME', 'tenant-documents-vector')
}

KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    'analytics_output_topic': os.getenv('LEXI_GEN_AI_ANALYTICS_TOPIC', 'lexi.gen.ai.analytics')
}

MISTRAL_CONFIG = {
    'enabledForFAQ' : os.getenv('MISTRAL_FAQ_ENABLED', False),
    'chat_url': os.getenv('MISTRAL_CHAT_URL', 'http://localhost:11434/api/chat'),
    'version_url': os.getenv('MISTRAL_VERSION_URL', 'http://localhost:11434/api/version'),
    'model': os.getenv('MISTRAL_MODEL', 'mistral'),
    'timeout': 120,
}


AZURE_CLIENT_CONFIG = {
    'endpoint_url': os.getenv('AZURE_ENDPOINT_URL', 'https://external-ai-model-resource.cognitiveservices.azure.com/'),
    'api_key': os.getenv('AZURE_API_KEY', ''),
    'deployment_name': os.getenv('AZURE_DEPLOYMENT_ID', 'gpt-4o-mini'),
    'api_version': os.getenv('API_VERSION', '2024-12-01-preview')
}
