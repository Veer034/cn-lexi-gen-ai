import datetime
import json
import os
import uuid
import logging
import uvicorn
from typing import List, Dict, Any, Optional
import asyncio
import numpy as np

from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from elasticsearch import AsyncElasticsearch
from confluent_kafka import Producer
import httpx
from config import KAFKA_CONFIG, ES_CONFIG, MISTRAL_CONFIG
from pythonjsonlogger import jsonlogger
from response import ExtractionAnalyticsDto
from manalLangaugeDetection import ManualLanguageDetector
from libaryLanguage import LibraryLanguageDetector
from logger_config import tracking_id_var, get_logger
from azure_openai_client import AzureOpenAIServiceClient


from logger_config import get_logger
logger = get_logger(__name__)

# Initialize app
app = FastAPI(title="Vector Search Service")

isMistralEnabledForFAQ = MISTRAL_CONFIG['enabledForFAQ'];
# For Getting trackingId
@app.middleware("http")
async def add_tracking_id_middleware(request: Request, call_next):
    tracking_id = request.headers.get("X-Tracking-ID", "NA")
    tracking_id_var.set(tracking_id)
    response = await call_next(request)
    return response


# Define request and response models
class AISearchRequest(BaseModel):
    query: str
    tenantId: str
    language:  str  
    topK: int = 5
    threshold: float = 0.7
    metadataFilters: Optional[Dict[str, Any]] = None
    answerTone: str = "polite"
    maxAnswerLength: int = 300

class AISearchResultDto(BaseModel):
    isGreeting: bool
    result: str
    requestId: str
    contentSize: int






class AsyncKafkaProducer:
    """Wrapper for Kafka producer with async interface"""
    def __init__(self, bootstrap_servers):
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers
        })
        self.is_connected = True


    async def send(self, topic, key=None, value=None):
        return await asyncio.to_thread(
            self._produce, topic, key, value
        )
    
    def _produce(self, topic, key, value, callback=None):
        """Send message to Kafka topic"""
        try:
            if isinstance(value, dict):
                value = json.dumps(value).encode('utf-8')
            elif not isinstance(value, bytes):
                value = str(value).encode('utf-8')
                
            if key is not None and not isinstance(key, bytes):
                key = str(key).encode('utf-8')
            
            tracking_id = tracking_id_var.get() or "NA"
            self.producer.produce(topic, key=key, value=value, callback=callback,  headers=[("X-Tracking-ID", tracking_id.encode("utf-8"))] )
            self.producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to produce to Kafka: {str(e)}")
            return False
    
    def close(self):
        """Close the producer"""
        if self.is_connected:
            self.producer.flush()
            self.is_connected = False

class VectorSearchService:
    def __init__(self, model_path=None):
        logger.info("🔧 Initializing VectorSearchService components...")
        # Initialize SentenceTransformer
        model_name = 'paraphrase-multilingual-mpnet-base-v2'
        # model_path = models_path or os.path.join(os.getcwd(), 'models', 'sentence_transformer')
        
        try:
            if model_path:
                logger.info(f"📂 Loading model from local path: {model_path}")
                self.st_model = SentenceTransformer(model_path)
                logger.info("✅ Local model loaded successfully")
            else:
                logger.info(f"🌐 Loading model {model_name} from Hugging Face...")
                self.st_model = SentenceTransformer(model_name)
                logger.info("✅ Hugging Face model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading sentence transformer model: {e}")
            raise
        
        # Initialize async Elasticsearch client
        logger.info("🔍 Initializing Elasticsearch client...")
        self.es_client = AsyncElasticsearch(
            ES_CONFIG['hosts'],
            basic_auth=(ES_CONFIG['username'], ES_CONFIG['password']),
            verify_certs=ES_CONFIG.get('verify_certs', True),
            ssl_show_warn=ES_CONFIG.get('ssl_show_warn', True),
            ca_certs=ES_CONFIG.get('ca_certs'),
            retry_on_timeout=True,
            max_retries=3
        )
        logger.info("✅ Elasticsearch client initialized")
        
        # Initialize HTTP client for API calls
        logger.info("🌐 Initializing HTTP client...")
        self.http_client = httpx.AsyncClient(timeout=300.0)
        logger.info("✅ HTTP client initialized")
        
        # Initialize Kafka producer for async processing results
        logger.info("📨 Initializing Kafka producer...")
        try:
            self.producer = AsyncKafkaProducer(KAFKA_CONFIG['bootstrap_servers'])
            logger.info("✅ Kafka producer initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize Kafka producer: {str(e)}")
            self.producer = None
        
        # Initialize detectors
        logger.info("🔤 Initializing language detectors...")
        self.manualDetector = ManualLanguageDetector()
        self.libraryDetector = LibraryLanguageDetector()
        logger.info("✅ Language detectors initialized")
        
        # Create a pool of workers for CPU-bound tasks
        self.process_pool = None
        self.QUESTION_INDICATORS = self._initialize_question_indicators()
       
        logger.info("🎯 VectorSearchService initialization completed!")
            
        
        
    def _initialize_question_indicators(self) -> Dict[str, List[str]]:
        """Initialize question words for different languages"""
        question_words = {
            # Default/English
            'en': ['what', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'is', 'are', 'do', 'does', 'will', 'would', 'could', 'should'],
            
            # Latin script European languages
            'de': ['was', 'wie', 'wann', 'wo', 'warum', 'wer', 'welche', 'können', 'ist', 'sind', 'machen', 'wird', 'würde', 'könnte', 'sollte'],
            'es': ['qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'quién', 'cuál', 'puede', 'es', 'son', 'hacer', 'será', 'haría', 'podría', 'debería'],
            'fr': ['quoi', 'comment', 'quand', 'où', 'pourquoi', 'qui', 'quel', 'peut', 'est', 'sont', 'faire', 'sera', 'ferait', 'pourrait', 'devrait'],
            'it': ['cosa', 'come', 'quando', 'dove', 'perché', 'chi', 'quale', 'può', 'è', 'sono', 'fare', 'sarà', 'farebbe', 'potrebbe', 'dovrebbe'],
            'pt': ['o que', 'como', 'quando', 'onde', 'por que', 'quem', 'qual', 'pode', 'é', 'são', 'fazer', 'será', 'faria', 'poderia', 'deveria'],
            'nl': ['wat', 'hoe', 'wanneer', 'waar', 'waarom', 'wie', 'welke', 'kan', 'is', 'zijn', 'doen', 'zal', 'zou', 'kon', 'moest'],
            'pl': ['co', 'jak', 'kiedy', 'gdzie', 'dlaczego', 'kto', 'który', 'może', 'jest', 'są', 'robić', 'będzie', 'by', 'mógł', 'powinien'],
            'sv': ['vad', 'hur', 'när', 'var', 'varför', 'vem', 'vilken', 'kan', 'är', 'är', 'göra', 'kommer', 'skulle', 'kunde', 'borde'],
            'no': ['hva', 'hvordan', 'når', 'hvor', 'hvorfor', 'hvem', 'hvilken', 'kan', 'er', 'er', 'gjøre', 'vil', 'ville', 'kunne', 'burde'],
            'da': ['hvad', 'hvordan', 'hvornår', 'hvor', 'hvorfor', 'hvem', 'hvilken', 'kan', 'er', 'er', 'gøre', 'vil', 'ville', 'kunne', 'burde'],
            'fi': ['mitä', 'miten', 'milloin', 'missä', 'miksi', 'kuka', 'mikä', 'voi', 'on', 'ovat', 'tehdä', 'tulee', 'tekisi', 'voisi', 'pitäisi'],
            'hu': ['mi', 'hogyan', 'mikor', 'hol', 'miért', 'ki', 'melyik', 'tud', 'van', 'vannak', 'csinál', 'fog', 'tenné', 'tudna', 'kellene'],
            'cs': ['co', 'jak', 'kdy', 'kde', 'proč', 'kdo', 'který', 'může', 'je', 'jsou', 'dělat', 'bude', 'by', 'mohl', 'měl'],
            'tr': ['ne', 'nasıl', 'ne zaman', 'nerede', 'neden', 'kim', 'hangi', 'yapabilir', 'olan', 'olan', 'yapmak', 'olacak', 'yapardı', 'yapabilir', 'yapmalı'],
            
            # Cyrillic script languages
            'ru': ['что', 'как', 'когда', 'где', 'почему', 'кто', 'который', 'может', 'есть', 'являются', 'делать', 'будет', 'бы', 'мог', 'должен'],
            'uk': ['що', 'як', 'коли', 'де', 'чому', 'хто', 'який', 'може', 'є', 'є', 'робити', 'буде', 'б', 'міг', 'повинен'],
            'bg': ['какво', 'как', 'кога', 'къде', 'защо', 'кой', 'който', 'може', 'е', 'са', 'правя', 'ще', 'би', 'можеше', 'трябва'],
            
            # Hindi and other Indic languages
            'hi': ['क्या', 'कैसे', 'कब', 'कहाँ', 'क्यों', 'कौन', 'कौन सा', 'कर सकता', 'है', 'हैं', 'करना', 'होगा', 'करेगा', 'कर सकता', 'चाहिए'],
            'mr': ['काय', 'कसे', 'केव्हा', 'कुठे', 'का', 'कोण', 'कोणते', 'करू शकतो', 'आहे', 'आहेत', 'करणे', 'होईल', 'करेल', 'करू शकतो', 'पाहिजे'],
            'bn': ['কি', 'কিভাবে', 'কখন', 'কোথায়', 'কেন', 'কে', 'কোনটি', 'পারে', 'আছে', 'আছে', 'করা', 'হবে', 'করবে', 'পারে', 'উচিত'],
            'pa': ['ਕੀ', 'ਕਿਵੇਂ', 'ਕਦੋਂ', 'ਕਿੱਥੇ', 'ਕਿਉਂ', 'ਕੌਣ', 'ਕਿਹੜਾ', 'ਕਰ ਸਕਦਾ', 'ਹੈ', 'ਹਨ', 'ਕਰਨਾ', 'ਹੋਵੇਗਾ', 'ਕਰੇਗਾ', 'ਕਰ ਸਕਦਾ', 'ਚਾਹੀਦਾ'],
            'gu': ['શું', 'કેવી રીતે', 'ક્યારે', 'ક્યાં', 'શા માટે', 'કોણ', 'કયું', 'કરી શકે', 'છે', 'છે', 'કરવું', 'હશે', 'કરશે', 'કરી શકે', 'જોઈએ'],
            'ta': ['என்ன', 'எப்படி', 'எப்போது', 'எங்கே', 'ஏன்', 'யார்', 'எது', 'முடியும்', 'இருக்கிறது', 'உள்ளன', 'செய்ய', 'இருக்கும்', 'செய்யும்', 'முடியும்', 'வேண்டும்'],
            'te': ['ఏమిటి', 'ఎలా', 'ఎప్పుడు', 'ఎక్కడ', 'ఎందుకు', 'ఎవరు', 'ఏది', 'చేయగలరు', 'ఉంది', 'ఉన్నాయి', 'చేయడం', 'ఉంటుంది', 'చేస్తారు', 'చేయగలరు', 'చేయాలి'],
            'kn': ['ಏನು', 'ಹೇಗೆ', 'ಯಾವಾಗ', 'ಎಲ್ಲಿ', 'ಏಕೆ', 'ಯಾರು', 'ಯಾವುದು', 'ಮಾಡಬಹುದು', 'ಇದೆ', 'ಇವೆ', 'ಮಾಡುವುದು', 'ಇರುತ್ತದೆ', 'ಮಾಡುತ್ತಾರೆ', 'ಮಾಡಬಹುದು', 'ಮಾಡಬೇಕು'],
            'ml': ['എന്ത്', 'എങ്ങനെ', 'എപ്പോൾ', 'എവിടെ', 'എന്തുകൊണ്ട്', 'ആര്', 'ഏത്', 'കഴിയും', 'ഉണ്ട്', 'ഉണ്ട്', 'ചെയ്യുക', 'ഉണ്ടാകും', 'ചെയ്യും', 'കഴിയും', 'വേണം'],
            
            # Middle Eastern languages
            'ar': ['ما', 'كيف', 'متى', 'أين', 'لماذا', 'من', 'أي', 'يمكن', 'هو', 'هم', 'يفعل', 'سوف', 'سيفعل', 'يمكن', 'يجب'],
            'fa': ['چه', 'چگونه', 'کی', 'کجا', 'چرا', 'کی', 'کدام', 'می‌تواند', 'است', 'هستند', 'انجام دادن', 'خواهد', 'خواهد کرد', 'می‌تواند', 'باید'],
            'ur': ['کیا', 'کیسے', 'کب', 'کہاں', 'کیوں', 'کون', 'کون سا', 'کر سکتا', 'ہے', 'ہیں', 'کرنا', 'ہوگا', 'کرے گا', 'کر سکتا', 'چاہیے'],
            'he': ['מה', 'איך', 'מתי', 'איפה', 'למה', 'מי', 'איזה', 'יכול', 'הוא', 'הם', 'לעשות', 'יהיה', 'יעשה', 'יכול', 'צריך'],
            
            # East Asian languages
            'zh': ['什么', '如何', '什么时候', '哪里', '为什么', '谁', '哪个', '可以', '是', '是', '做', '将', '会', '可以', '应该'],
            'zh-tw': ['什麼', '如何', '什麼時候', '哪裡', '為什麼', '誰', '哪個', '可以', '是', '是', '做', '將', '會', '可以', '應該'],
            'ja': ['何', 'どのように', 'いつ', 'どこ', 'なぜ', '誰', 'どの', 'できる', 'です', 'である', 'する', 'でしょう', 'します', 'できる', 'すべき'],
            'ko': ['무엇', '어떻게', '언제', '어디', '왜', '누구', '어느', '할 수 있다', '이다', '이다', '하다', '것이다', '할 것이다', '할 수 있다', '해야 한다'],
            
            # Thai
            'th': ['อะไร', 'อย่างไร', 'เมื่อไหร่', 'ที่ไหน', 'ทำไม', 'ใคร', 'ไหน', 'สามารถ', 'เป็น', 'เป็น', 'ทำ', 'จะ', 'จะทำ', 'สามารถ', 'ควร'],
            
            # Indonesian and Malay
            'id': ['apa', 'bagaimana', 'kapan', 'dimana', 'mengapa', 'siapa', 'yang mana', 'bisa', 'adalah', 'adalah', 'melakukan', 'akan', 'akan melakukan', 'bisa', 'harus'],
            'ms': ['apa', 'bagaimana', 'bila', 'dimana', 'mengapa', 'siapa', 'yang mana', 'boleh', 'adalah', 'adalah', 'melakukan', 'akan', 'akan melakukan', 'boleh', 'harus'],
            
            # Vietnamese
            'vi': ['gì', 'làm thế nào', 'khi nào', 'ở đâu', 'tại sao', 'ai', 'cái nào', 'có thể', 'là', 'là', 'làm', 'sẽ', 'sẽ làm', 'có thể', 'nên'],
            
            # African languages
            'sw': ['nini', 'jinsi', 'lini', 'wapi', 'kwa nini', 'nani', 'ipi', 'inaweza', 'ni', 'ni', 'kufanya', 'itakuwa', 'itafanya', 'inaweza', 'inapaswa'],
            'ha': ['me', 'ta yaya', 'yaushe', 'ina', 'me yasa', 'wane', 'wanne', 'iya', 'shi ne', 'su ne', 'yi', 'zai', 'zai yi', 'iya', 'ya kamata'],
            'ig': ['gịnị', 'otú', 'mgbe', 'ebe', 'gịnị kpatara', 'onye', 'nke', 'nwere ike', 'bụ', 'bụ', 'ime', 'ga', 'ga ime', 'nwere ike', 'kwesịrị']
        }
        return question_words

  
    
    async def generate_embeddings(self, query: str) -> List[float]:
        """Generate embeddings for a list of queries using a thread pool"""
        try:
            start_time = datetime.datetime.now()
            
            # Move the embedding generation to a separate thread 
            # since SentenceTransformer is not async-compatible
            embeddings = await asyncio.to_thread(self._generate_embeddings_sync, query)
            
            end_time = datetime.datetime.now()
            logger.info(f"Generated {len(query)} embeddings in {(end_time - start_time).total_seconds()} seconds")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
            raise
    
    def _generate_embeddings_sync(self, query: str) -> List[float]:
        """Synchronous method to generate embeddings (runs in a thread)"""
        embeddings = self.st_model.encode(query)
        return embeddings.tolist()
    
    def _is_question(self, query: str, language: str = None) -> bool:
        """Check if query is a question in multiple languages"""
        if not query:
            return False
        
        query_lower = query.lower().strip()
        
        # Universal question mark check
        if query_lower.endswith('?') or '?' in query_lower:
            return True
        
        # Language-specific question marks
        if query_lower.endswith('؟'):  # Arabic question mark
            return True
        if query_lower.endswith('？'):  # CJK question mark
            return True
        
        # If no language specified, try to detect it
        if not language:
            language = self.detect_best_language(query)
        
        # Get question indicators for the language
        question_indicators = self.QUESTION_INDICATORS.get(language, self.QUESTION_INDICATORS.get('en', []))
        
        if not question_indicators:
            # Fallback: if language not supported, use English indicators
            question_indicators = self.QUESTION_INDICATORS['en']
        
        # Check for question words at the beginning (most common pattern)
        words = query_lower.split()
        if words:
            first_word = words[0]
            # Direct match
            if first_word in question_indicators:
                return True
            
            # Check if first word starts with a question word (for compound words)
            for indicator in question_indicators:
                if first_word.startswith(indicator) and len(indicator) > 2:
                    return True
        
        # Check for question words anywhere in short queries (< 6 words)
        if len(words) <= 5:
            for word in words:
                if word in question_indicators:
                    return True
        
        return False

    # Updated search function without the problematic _is_question call
    async def search_elasticsearch(
            self, 
            embedding: List[float], 
            tenant_id: str, 
            top_k: int = 5, 
            threshold: float = 0.55,
            metadata_filters: Optional[Dict[str, Any]] = None,
            include_context: bool = True,
            original_query: Optional[str] = None  # Add this to detect questions
        ) -> List[Dict[str, Any]]:
        """Enhanced search keeping your exact original logic but adding context"""
        try:
            # Build the filter conditions (exactly like your original)
            filter_conditions = [{"term": {"tenantId": tenant_id}}]
            
            if metadata_filters:
                for key, value in metadata_filters.items():
                    if isinstance(value, list):
                        filter_conditions.append({"terms": {f"metadata.{key}": value}})
                    else:
                        filter_conditions.append({"term": {f"metadata.{key}": value}})
            
            # Detect if query is a question (if original_query provided)
            is_question_query = False
            if original_query:
                # Get language from metadata or detect it
                query_language = None
                if metadata_filters and 'language' in metadata_filters:
                    query_language = metadata_filters['language']
                is_question_query = self._is_question(original_query, query_language)
            
            # Enhanced query with conditional FAQ boosting
            if is_question_query:
                # Boost FAQ content for questions
                query = {
                    "query": {
                        "script_score": {
                            "query": {
                                "bool": {
                                    "filter": filter_conditions
                                }
                            },
                            "script": {
                                "source": """
                                    double base_score = cosineSimilarity(params.query_vector, 'contentVector');
                                    double faq_boost = doc.containsKey('chunkType') && doc['chunkType'].size() > 0 && doc['chunkType'].value == 'faq' ? 1.15 : 1.0;
                                    return base_score * faq_boost;
                                """,
                                "params": {"query_vector": embedding}
                            }
                        }
                    },
                    "_source": ["content", "documentId", "chunkPosition", "totalChunks", "chunkType", "metadata"]
                }
            else:
                # Your exact original query
                query = {
                    "query": {
                        "script_score": {
                            "query": {
                                "bool": {
                                    "filter": filter_conditions
                                }
                            },
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'contentVector')",
                                "params": {"query_vector": embedding}
                            }
                        }
                    },
                    "_source": ["content", "documentId", "chunkPosition", "totalChunks", "chunkType", "metadata"]
                }

            logger.info(f"Enhanced query with question detection: {is_question_query}")
            
            # Execute search (same as original)
            response = await self.es_client.search(
                index=self.es_config['tenant_document_index_name'],
                body=query,
                size=top_k
            )
            
            # Process results with optional context enhancement
            results = {
                "esTime": response['took'],
                "contents": []
            }
            
            for hit in response['hits']['hits']:
                score = hit['_score']
                if score >= threshold:
                    if include_context:
                        # Get enhanced content with context
                        enhanced_content = await self._get_chunk_with_adjacent_context(
                            hit['_source'], 
                            tenant_id
                        )
                        results["contents"].append(enhanced_content)
                    else:
                        # Original behavior
                        results["contents"].append(hit['_source']['content'])
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {str(e)}", exc_info=True)
            raise

  
    async def _get_chunk_with_adjacent_context(self, chunk_data: Dict, tenant_id: str) -> str:
        """Get chunk content enhanced with adjacent context"""
        try:
            document_id = chunk_data.get('documentId')
            chunk_position = chunk_data.get('chunkPosition')
            total_chunks = chunk_data.get('totalChunks')
            main_content = chunk_data.get('content', '')
            
            # If no position info, return original content
            if chunk_position is None or total_chunks is None:
                return main_content
            
            # Determine adjacent positions to fetch
            adjacent_positions = []
            if chunk_position > 0:
                adjacent_positions.append(chunk_position - 1)  # Previous chunk
            if chunk_position < total_chunks - 1:
                adjacent_positions.append(chunk_position + 1)  # Next chunk
            
            # If no adjacent chunks, return main content
            if not adjacent_positions:
                return main_content
            
            # Query for adjacent chunks
            adjacent_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"tenantId": tenant_id}},
                            {"term": {"documentId": document_id}},
                            {"terms": {"chunkPosition": adjacent_positions}}
                        ]
                    }
                },
                "sort": [{"chunkPosition": "asc"}],
                "size": len(adjacent_positions),
                "_source": ["content", "chunkPosition"]
            }
            
            adjacent_response = await self.es_client.search(
                index=self.es_config['tenant_document_index_name'],
                body=adjacent_query
            )
            
            # Build enhanced content with context
            context_parts = []
            
            # Add previous context if available
            prev_content = ""
            next_content = ""
            
            for adj_hit in adjacent_response['hits']['hits']:
                adj_data = adj_hit['_source']
                adj_position = adj_data['chunkPosition']
                
                if adj_position == chunk_position - 1:  # Previous chunk
                    prev_content = adj_data['content']
                elif adj_position == chunk_position + 1:  # Next chunk
                    next_content = adj_data['content']
            
            # Construct enhanced content
            enhanced_content = ""
            
            if prev_content:
                # Add last portion of previous chunk for context
                prev_words = prev_content.split()
                prev_context = " ".join(prev_words[-50:]) if len(prev_words) > 50 else prev_content
                enhanced_content += f"[Previous context: ...{prev_context}]\n\n"
            
            # Add main content
            enhanced_content += main_content
            
            if next_content:
                # Add first portion of next chunk for context
                next_words = next_content.split()
                next_context = " ".join(next_words[:50]) if len(next_words) > 50 else next_content
                enhanced_content += f"\n\n[Following context: {next_context}...]"
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error getting adjacent context: {str(e)}")
            # Return original content if context retrieval fails
            return chunk_data.get('content', '')

    async def generate_answer_from_mistral_or_azure(
        self,
        query: str,
        contents: List[str],
        language: str,
        tone: str = "polite",
        max_length: int = 200,
    ) -> Dict[str, Any]:
        """
        Generate an answer to the query using either Mistral (self-hosted) or Azure OpenAI Service.
        """
        try:
            # Combine context
            context = "\n\n".join(contents)
            token_limit = min(max_length // 4, 45)  # Approximate token limit

            # System prompt
            system_prompt = f"""CRITICAL INSTRUCTIONS:
    1. You MUST ONLY answer based on the EXACT provided context
    2. You MUST provide a BRIEF response - no more than {token_limit} tokens
    3. Use a {tone} tone and be extremely concise
    4. Only include the most essential details that directly answer the query
    5. If the answer CANNOT be found in the context, respond with "Not provided in the context"
    6. Do NOT add any explanations or information not present in the context
    7. Do NOT exceed {token_limit} tokens in your response
    8. Format your answer as a single paragraph with no bullet points or lists"""

            # User prompt
            user_prompt = f"""Reference content:
    {context}

    Question: {query}

    IMPORTANT: Provide a comprehensive answer based ONLY on information in the given context in {language} language.
    Include ALL relevant policy details, time limits, conditions, or restrictions that apply to this question."""

            response_data = {}

            if isMistralEnabledForFAQ:
                # Prepare payload for Mistral
                data = {
                    "model": MISTRAL_CONFIG['model'],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "max_tokens": max_length,
                    "temperature": 0.2
                }

                logger.info("Sending context-constrained request to Mistral: %s", json.dumps(data, indent=2))

                response = await self.http_client.post(
                    MISTRAL_CONFIG['chat_url'],
                    headers={"Content-Type": "application/json"},
                    json=data,
                    timeout=MISTRAL_CONFIG['timeout']
                )

                if response.status_code != 200:
                    logger.error(f"Mistral LLM error: {response.status_code} - {response.text}")
                    return {"error": f"Mistral LLM returned status {response.status_code}"}

                response_data = response.json()

            else:
                # Call Azure OpenAI Service (updated to use new cost-efficient client)
                azure_client = AzureOpenAIServiceClient()  # Uses the updated cost-efficient client

                logger.info("Sending context-constrained request to system_prompt: %s , user_prompt: %s", system_prompt,user_prompt)

                response_data = await azure_client.generate_answer(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_length,
                    temperature=0.2,
                    include_usage=False  # Keep costs minimal - only get content
                )
                
                # Clean up the client
                await azure_client.close()

            logger.info(f"LLM Response: {response_data}")
            return response_data

        except Exception as e:
            logger.error(f"Error generating answer with LLM: {str(e)}", exc_info=True)
            return {"error": f"Error generating answer: {str(e)}"}
        
    async def process_search_request(
        self, 
        query: str, 
        tenant_id: str, 
        language: str,
        top_k: int = 5, 
        threshold: float = 0.7,
        metadata_filters: Optional[Dict[str, Any]] = None,
        answer_tone: str = "polite",
        max_answer_length: int = 300
    ) -> Dict[str, Any]:
        """Process a search request end-to-end using async operations"""
        

        # Generate embeddings for all queries
        embedding = await self.generate_embeddings(query)
        
        metadata_filters={}
        if language and language != "unknown":
            metadata_filters["language"] = language
                
        # Create tasks for concurrent Elasticsearch searches
        search_result = await self.search_elasticsearch(
                embedding, 
                tenant_id,
                top_k, 
                threshold,
                metadata_filters
            ) 
        
    
        
        if search_result["contents"]:
            response = await self.generate_answer_from_mistral_or_azure(
                query,
                search_result["contents"],
                language=language,
                tone=answer_tone,
                max_length=max_answer_length,
            )

            # Add extracted details to search_result
            message = response.get("message", {})
            content = message.get("content", "")

            search_result["answer"] = content
            # Convert nanoseconds to milliseconds for better integer-based analytics
            search_result["total_duration"] = int(response.get("total_duration", 0) / 1_000_000)  # nano to milli
            search_result["load_duration"] = int(response.get("load_duration", 0) / 1_000_000)
            search_result["prompt_eval_duration"] = int(response.get("prompt_eval_duration", 0) / 1_000_000)
            search_result["eval_duration"] = int(response.get("eval_duration", 0) / 1_000_000)

            logger.info(
                f"Processed search request for query: {query}, "
                f"Response: {search_result['answer']}, "
                f"Total Duration: {search_result['total_duration']}, "
                f"Load Duration: {search_result['load_duration']}"
            )

          

        else:
            search_result["answer"] =  ""
            search_result["total_duration"] = 0
            search_result["load_duration"] = 0
            search_result["prompt_eval_duration"] = 0
            search_result["eval_duration"] = 0




        return search_result  # Returning updated search_result
        

    async def publish_analytics_report_to_kafka(self, tenant_id:str, topic: str, analyticsDto: ExtractionAnalyticsDto):
        """
        Publishes analytics data to a Kafka topic.
        """
        # Serialize key and value
        serialized_key = str(tenant_id).encode("utf-8")
        serialized_analytics = json.dumps(analyticsDto.model_dump(), default=str).encode("utf-8")

        # Create an asyncio Future to wait for delivery report
        future = asyncio.Future()
        
        def delivery_callback(err, msg):
            if err:
                future.set_exception(Exception(f"Message delivery failed: {err}"))
            else:
                future.set_result(msg)
        
        self.producer._produce(topic, key=serialized_key, value=serialized_analytics, callback=delivery_callback)
        
        return await future


    def detect_best_language(self,text):
        # 1. For very short texts, try pattern matching first
        if len(text.split()) >= 5:  # Short customer queries
            service_lang = self.manualDetector.make_best_guess(text)
            return service_lang
                
        # 2. Try libraries next
        if len(self.libraryDetector.available_libraries) > 0:
            lib_signals = self.libraryDetector._detect_with_libraries(text)
            logger.info(f" libraryDetector {lib_signals} ")
            
            if lib_signals:
                # Get best library result
                best_signal = max(lib_signals, key=lambda x: x[2])
                _, lang, conf = best_signal
                if conf > 0.5:  # If reasonably confident
                    return lang
                    
        # 3. Fall back to combined approach
        return 'en'


    def get_best_response(self,language):
        return self.manualDetector.get_no_results_message(language)

    def handle_greeting(self, message, language):
        return self.manualDetector.handle_greeting(message,language)


    async def close(self):
        """Close connections and resources"""
        if self.producer:
            self.producer.close()
        
        if self.http_client:
            await self.http_client.aclose()
        
        if self.es_client:
            await self.es_client.close()

# Service dependency
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("=" * 60)
        logger.info("🚀 STARTING VECTOR SEARCH SERVICE")
        logger.info("=" * 60)
        
        # Initialize the search service
        logger.info("📦 Initializing Vector Search Service...")
        app.state.search_service = VectorSearchService()
        logger.info("✅ Vector Search Service initialized successfully")
        
        # Log configuration details
        logger.info(f"🔧 Mistral service configured at: {MISTRAL_CONFIG['chat_url']}")
        logger.info(f"🔧 Elasticsearch configured at: {ES_CONFIG['hosts']}")
        logger.info(f"🔧 Kafka configured at: {KAFKA_CONFIG['bootstrap_servers']}")
        
        # Perform initial health checks
        logger.info("🏥 Performing initial health checks...")
        
        # Check Elasticsearch
        try:
            es_healthy = await app.state.search_service.es_client.ping()
            if es_healthy:
                logger.info("✅ Elasticsearch connection: HEALTHY")
            else:
                logger.warning("⚠️  Elasticsearch connection: FAILED")
        except Exception as e:
            logger.error(f"❌ Elasticsearch connection error: {str(e)}")
        
        # Check Mistral service
        try:
            response = await app.state.search_service.http_client.get(
                MISTRAL_CONFIG['version_url'],
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ Mistral service connection: HEALTHY")
            else:
                logger.warning(f"⚠️  Mistral service responded with status: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Mistral service connection: {str(e)}")
        
        # Check model loading
        if hasattr(app.state.search_service, 'st_model'):
            logger.info("✅ Sentence Transformer model: LOADED")
        else:
            logger.error("❌ Sentence Transformer model: FAILED TO LOAD")
        
        # Check Kafka producer
        if app.state.search_service.producer and app.state.search_service.producer.is_connected:
            logger.info("✅ Kafka producer: CONNECTED")
        else:
            logger.warning("⚠️  Kafka producer: NOT CONNECTED")
        
        logger.info("=" * 60)
        logger.info("🎉 VECTOR SEARCH SERVICE STARTED SUCCESSFULLY")
        logger.info("🌐 Service is ready to accept requests on port 9001")
        logger.info("📍 Health check available at: http://localhost:9001/health")
        logger.info("📍 Search endpoint available at: http://localhost:9001/lexi-gen-ai/search")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("💥 STARTUP FAILED!")
        logger.error(f"❌ Error during startup: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    # Close Kafka producer
    if hasattr(app.state, 'search_service'):
        await app.state.search_service.close()
    
    # Cancel consumer task
    if hasattr(app.state, 'consumer_task'):
        app.state.consumer_task.cancel()
        try:
            await app.state.consumer_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Vector Search Service shut down")

async def get_search_service():
    return app.state.search_service

# API Endpoints
@app.post("/lexi-gen-ai/search")
async def search(
    request: AISearchRequest,
    search_service: VectorSearchService = Depends(get_search_service)
):
    """Endpoint to search documents using vector similarity"""
    try:
        # Generate a request ID for this specific request
        request_id = str(uuid.uuid4())
        logger.info(f"[{request_id}] Processing search request with query: {request}")

        if not request.language:
            # Use your language detection logic here
            detected_language = search_service.detect_best_language(request.query)
            logger.info(f"detected_language : {detected_language}")
            request.language = detected_language
          

        greeting = search_service.handle_greeting(request.query,request.language)

          # If greeting is detected, return the greeting response directly
        if greeting:
            logger.info(f"[{request_id}] Greeting detected, responding with appropriate greeting")
            return AISearchResultDto(isGreeting = True,result=greeting, requestId=request_id, contentSize=0)



        responseData = await search_service.process_search_request(
            request.query,
            request.tenantId,
            request.language,
            request.topK,
            request.threshold,
            request.metadataFilters,
            request.answerTone,
            request.maxAnswerLength
        )

        logger.info(f"responseData: {responseData}")
        
         # Extract analytics data from response if it has mistral performance metrics
        if responseData and isinstance(responseData, dict) and 'total_duration' in responseData:
            analytics_data = ExtractionAnalyticsDto(
                tenantId=request.tenantId,
                query=request.query,
                answer=  responseData.get("answer",''),
                contents = responseData.get('contents', []),
                totalDuration=responseData.get('total_duration', 0),
                loadDuration=responseData.get('load_duration', 0),
                promptEvalDuration=responseData.get('prompt_eval_duration', 0),
                evalDuration=responseData.get('eval_duration', 0)
            )
            
            # Send results to Kafka asynchronously
            # We use create_task to fire and forget
            asyncio.create_task(
                search_service.publish_analytics_report_to_kafka(
                    request.tenantId,
                    KAFKA_CONFIG['analytics_output_topic'],
                    analytics_data
                )
            )
        

        answer  = responseData.get('answer')
        if answer == '':
            language = request.language.lower()  # Get language from request
            answer = search_service.get_best_response(language)
       
        content_size = len(responseData.get("contents", []))
        print(content_size)

        logger.info(f"[{request_id}] Search completed successfully")
        return AISearchResultDto(isGreeting =False, result=answer, requestId=request_id, contentSize =content_size)

       
    except Exception as e:
        error_msg = f"Search request failed: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        
        # Return a custom error response that includes the request_id
        raise HTTPException(
            status_code=500, 
            detail={"error": 'Something went wrong', "request_id": request_id}
        )

@app.get("/health")
async def health_check(search_service: VectorSearchService = Depends(get_search_service)):
    """Enhanced health check endpoint with detailed logging"""
    health_check_id = str(uuid.uuid4())[:8]
    logger.info(f"🏥 [{health_check_id}] Health check requested")
    
    try:
        health_status = {
            "timestamp": datetime.datetime.now().isoformat(),
            "service": "Vector Search Service",
            "version": "1.0.0",
            "status": "unknown",
            "components": {}
        }
        
        # Check Elasticsearch connection
        logger.info(f"🔍 [{health_check_id}] Checking Elasticsearch connection...")
        try:
            es_healthy = await search_service.es_client.ping()
            health_status["components"]["elasticsearch"] = {
                "status": "healthy" if es_healthy else "unhealthy",
                "hosts": ES_CONFIG['hosts']
            }
            logger.info(f"✅ [{health_check_id}] Elasticsearch: {'HEALTHY' if es_healthy else 'UNHEALTHY'}")
        except Exception as e:
            health_status["components"]["elasticsearch"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            logger.error(f"❌ [{health_check_id}] Elasticsearch check failed: {str(e)}")
            es_healthy = False
        
        # Check model loaded
        logger.info(f"🤖 [{health_check_id}] Checking model status...")
        model_healthy = hasattr(search_service, 'st_model') and search_service.st_model is not None
        health_status["components"]["sentence_transformer"] = {
            "status": "healthy" if model_healthy else "unhealthy"
        }
        logger.info(f"✅ [{health_check_id}] Model: {'LOADED' if model_healthy else 'NOT LOADED'}")
        
        # Check Mistral service connection
        logger.info(f"🧠 [{health_check_id}] Checking Mistral service connection...")
        mistral_healthy = False
        try:
            response = await search_service.http_client.get(
                MISTRAL_CONFIG['version_url'],
                timeout=5
            )
            mistral_healthy = response.status_code == 200
            health_status["components"]["mistral_service"] = {
                "status": "healthy" if mistral_healthy else "unhealthy",
                "url": MISTRAL_CONFIG['version_url'],
                "response_code": response.status_code
            }
            logger.info(f"✅ [{health_check_id}] Mistral service: {'HEALTHY' if mistral_healthy else 'UNHEALTHY'}")
        except Exception as e:
            health_status["components"]["mistral_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            logger.warning(f"⚠️  [{health_check_id}] Mistral service check failed: {str(e)}")
        
        # Check Kafka producer
        logger.info(f"📨 [{health_check_id}] Checking Kafka producer...")
        kafka_healthy = (search_service.producer is not None and 
                        hasattr(search_service.producer, 'is_connected') and 
                        search_service.producer.is_connected)
        health_status["components"]["kafka_producer"] = {
            "status": "healthy" if kafka_healthy else "unhealthy",
            "bootstrap_servers": KAFKA_CONFIG['bootstrap_servers']
        }
        logger.info(f"✅ [{health_check_id}] Kafka producer: {'CONNECTED' if kafka_healthy else 'DISCONNECTED'}")
        
        # Overall health status
        overall_healthy = es_healthy and model_healthy
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        
        # Log overall result
        if overall_healthy:
            logger.info(f"🎉 [{health_check_id}] Overall health check: PASSED")
        else:
            logger.warning(f"⚠️  [{health_check_id}] Overall health check: FAILED")
        
        # Return appropriate response
        if not overall_healthy:
            raise HTTPException(status_code=503, detail=health_status)
            
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{health_check_id}] Health check error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        })

if __name__ == "__main__":
    logger.info("🚀 Starting application with uvicorn...")
    logger.info("📋 Configuration:")
    logger.info(f"   - Host: 0.0.0.0")
    logger.info(f"   - Port: 9001")
    logger.info(f"   - Reload: True")
    logger.info("🔄 Starting uvicorn server...")
    
    # Use uvicorn with reload for development
    uvicorn.run("master:app", host="0.0.0.0", port=9001, reload=True)