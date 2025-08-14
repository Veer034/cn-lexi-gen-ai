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

from logger_config import get_logger
logger = get_logger(__name__)

# Initialize app
app = FastAPI(title="Vector Search Service")


# For Getting trackingId
@app.middleware("http")
async def add_tracking_id_middleware(request: Request, call_next):
    tracking_id = request.headers.get("trackingId", "NA")
    tracking_id_var.set(tracking_id)
    response = await call_next(request)
    return response


# Define request and response models
class SearchRequest(BaseModel):
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
            self.producer.produce(topic, key=key, value=value, callback=callback,  headers=[("trackingId", tracking_id.encode("utf-8"))] )
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
        
        logger.info("🎯 VectorSearchService initialization completed!")


    
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
    

    async def search_elasticsearch(
        self, 
        embedding: List[float], 
        tenant_id: str, 
        top_k: int = 5, 
        threshold: float = 0.55,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search Elasticsearch using dot product with normalized vectors for ES 7.17"""
        try:
            
            # Build the filter conditions
            filter_conditions = [{"term": {"tenantId": tenant_id}}]
            
            # Add metadata filters if provided
            if metadata_filters:
                for key, value in metadata_filters.items():
                    if isinstance(value, list):
                        filter_conditions.append({"terms": {f"metadata.{key}": value}})
                    else:
                        filter_conditions.append({"term": {f"metadata.{key}": value}})
            
            # Build the query
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
                }
            }

            logger.info(f" query {query}")
            
            # Execute search
            response = await self.es_client.search(
                index=ES_CONFIG['tenant_document_index_name'],
                body=query,
                size=top_k
            )
            

            # Process results
            results = {
                "esTime": response['took'],
                "contents": []
            }
            for hit in response['hits']['hits']:
                score = hit['_score']
                if score >= threshold:
                    results["contents"].append(hit['_source']['content'])
            

            return results
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {str(e)}", exc_info=True)
            raise
  
    async def generate_answer_from_mistral(
        self,
        query: str,
        contents: List[str],
        language: str,
        tone: str = "polite",
        max_length: int = 200,
    ) -> Dict[str, Any]:
        """
        Generate an answer to the query using LLM based strictly on the provided context
        
        Args:
            query (str): The specific question to be answered
            contents (List[str]): List of context strings to base the answer on
            language (str): Language of the response
            tone (str): Tone of the response
            max_length (int): Maximum length of the response
        
        Returns:
            Dict[str, Any]: LLM response or error details
        """
        try:
            # Combine contents into context
            context = "\n\n".join(contents)  # Direct join of string array
            
            # Calculate an approximate token count (assuming ~4 chars per token on average)
            # For a 25-30 word limit (approximately 35-45 tokens)
            token_limit = min(max_length // 4, 45)  # Set upper bound to 45 tokens
       

            # Extract specific information if present
            info_extraction_prompt = f"""
            First, identify ALL specific facts, numbers, dates, limitations, and policy details in this context:
            {context}
            
            List only the specific details found (timeframes, deadlines, rules, limits, etc.). Be concise.
            """
            
            # Strict system prompt to force context-only responses
            system_prompt = f"""CRITICAL INSTRUCTIONS:
            1. You MUST ONLY answer based on the EXACT provided context
            2. You MUST provide a BRIEF response - no more than {token_limit} tokens
            3. Use a {tone} tone and be extremely concise
            4. Only include the most essential details that directly answer the query
            5. If the answer CANNOT be found in the context, respond with "Not provided in the context"
            6. Do NOT add any explanations or information not present in the context
            7. Do NOT exceed {token_limit} tokens in your response
            8. Format your answer as a single paragraph with no bullet points or lists"""
            
            # User prompt emphasizing context-only response
            user_prompt = f"""Reference content:
            {context}
            
            Question: {query}
            
            IMPORTANT: Provide a comprehensive answer based ONLY on information in the given context in {language} language.
            Include ALL relevant policy details, time limits, conditions, or restrictions that apply to this question.
            """
            
            # Prepare the request payload - adjusting max_tokens
            data = {
                "model": MISTRAL_CONFIG['model'],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "max_tokens": max_length,  # Allow more tokens for a complete answer
                "temperature": 0.2  # Lower temperature for more precise factual responses
            }
            
            # Log the request for debugging
            logger.info("Sending context-constrained request to LLM: %s", json.dumps(data, indent=2))
            
            # Use httpx for async request
            response = await self.http_client.post(
                    MISTRAL_CONFIG['chat_url'],
                    headers={"Content-Type": "application/json"},
                    json=data,
                    timeout=MISTRAL_CONFIG['timeout']
            )
            
            # Error handling for non-200 responses
            if response.status_code != 200:
                logger.error(f"LLM service error: {response.status_code} - {response.text}")
                return {"error": f"Error generating answer: LLM service returned status {response.status_code}"}
            
            # Log and return the response
            response_data = response.json()
            logger.info(f"Context-constrained Response Status: {response_data}")
            
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
            mistral_response = await self.generate_answer_from_mistral(
                query,
                search_result["contents"],
                language=language,
                tone=answer_tone,
                max_length=max_answer_length,
            )

            # Add extracted details to search_result
            message = mistral_response.get("message", {})
            content = message.get("content", "")

            search_result["answer"] = content
            # Convert nanoseconds to milliseconds for better integer-based analytics
            search_result["total_duration"] = int(mistral_response.get("total_duration", 0) / 1_000_000)  # nano to milli
            search_result["load_duration"] = int(mistral_response.get("load_duration", 0) / 1_000_000)
            search_result["prompt_eval_duration"] = int(mistral_response.get("prompt_eval_duration", 0) / 1_000_000)
            search_result["eval_duration"] = int(mistral_response.get("eval_duration", 0) / 1_000_000)

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
    request: SearchRequest,
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