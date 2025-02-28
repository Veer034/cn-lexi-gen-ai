import os
from dotenv import load_dotenv

load_dotenv()


# Config (can be moved to separate file)
ES_CONFIG = {
    'hosts': ['http://localhost:9200'],
    'username': os.getenv('ES_USERNAME', ''),
    'password': os.getenv('ES_PASSWORD', ''),
    'index_name': 'messages'
}

KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_SERVERS', 'localhost:9092'),
    'output_topic': 'ai.chat.search.analytics',
    'input_topic':'topicname'
}

MISTRAL_CONFIG = {
    'service_url': os.getenv('MISTRAL_SERVICE_URL', 'http://localhost:11434/api/chat'),
    'model': os.getenv('MISTRAL_MODEL', 'mistral'),
    'timeout': 120,
}