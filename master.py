import datetime
import json
import os
import uuid
import logging
import uvicorn
from typing import List, Dict, Any, Optional
import asyncio
import numpy as np

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from elasticsearch import AsyncElasticsearch
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Consumer, KafkaError, KafkaException
import httpx
from config import KAFKA_CONFIG, ES_CONFIG, MISTRAL_CONFIG
from pythonjsonlogger import jsonlogger
from response import ExtractionAnalyticsDto
from manalLangaugeDetection import ManualLanguageDetector
from libaryLanguage import LibraryLanguageDetector
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
logger = logging.getLogger(__name__)


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
    result: str
    requestId: str
    contentSize: int


# Initialize app
app = FastAPI(title="Vector Search Service")



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
                
            self.producer.produce(topic, key=key, value=value, callback=callback)
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
    def __init__(self, models_path=None):
        # Initialize SentenceTransformer
        model_name = 'paraphrase-multilingual-mpnet-base-v2'
        model_path = models_path or os.path.join(os.getcwd(), 'models', 'sentence_transformer')
        

        # Use downloaded model if available, otherwise use the model name directly
        if os.path.exists(model_path):
            logger.info(f"Loading model from local path: {model_path}")
            self.st_model = SentenceTransformer(model_path)
        else:
            logger.info(f"Local model not found. Loading model {model_name} from Hugging Face")
            self.st_model = SentenceTransformer(model_name)
        
        # Initialize Async Elasticsearch client
        self.es_client = AsyncElasticsearch(
            ES_CONFIG['hosts'],
            basic_auth=(ES_CONFIG.get('username', ''), ES_CONFIG.get('password', '')),
            retry_on_timeout=True,
            max_retries=3
        )
        
         # TODO :: timeout need to be decreased to standard, 300 for local only
        # Initialize HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=300.0)
        
        # Initialize Kafka producer for async processing results
        try:
            self.producer = AsyncKafkaProducer(KAFKA_CONFIG['bootstrap_servers'])
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka producer: {str(e)}")
            self.producer = None
        
        # Create a pool of workers for CPU-bound tasks
        self.process_pool = None


        # Create detector
        self.manualDetector = ManualLanguageDetector()
        self.libraryDetector = LibraryLanguageDetector()


    
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
        language: str,
        top_k: int = 5, 
        threshold: float = 0.55,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search Elasticsearch using dot product with normalized vectors for ES 7.17"""
        try:
            
            # Build the filter conditions
            filter_conditions = [{"term": {"tenantId": tenant_id}}, {"term": {"metadata.language": language}}]
            
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
    
            # Strict system prompt to force context-only responses
            system_prompt = f"""CRITICAL INSTRUCTIONS:
            1. You MUST ONLY answer based on the EXACT provided context
            2. If the answer CANNOT be found in the context, return an empty string ""
            3. Use a {tone} but extremely concise tone
            4. Keep your answer exact to the point
            5. Never use generic phrases or add extra information
            6. Do NOT rely on any previous knowledge or conversations
            7. Your response must be strictly derived from the reference content
            8. VERY IMPORTANT: Entire response MUST be under {max_length // 4} tokens"""
            
            # User prompt emphasizing context-only response
            user_prompt = f"""Reference content ONLY:
            {context}
            
            Question: {query}
            
            IMPORTANT: Provide ONLY an answer found EXACTLY in the given context in {language} language. 
            If NO answer exists in the context, return an empty string."""
            
            # Prepare the request payload
            data = {
                "model": MISTRAL_CONFIG['model'],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "max_tokens": max_length // 4
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
        
        # Create tasks for concurrent Elasticsearch searches
        search_result = await self.search_elasticsearch(
                embedding, 
                tenant_id,
                language, 
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
            search_result["total_duration"] = mistral_response.get("total_duration", 0)
            search_result["load_duration"] = mistral_response.get("load_duration", 0)
            search_result["prompt_eval_duration"] = mistral_response.get("prompt_eval_duration", 0)
            search_result["eval_duration"] = mistral_response.get("eval_duration", 0)


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
    # Initialize the search service
    app.state.search_service = VectorSearchService()
    

    logger.info("Vector Search Service initialized")
    logger.info(f"Using Mistral service at: {MISTRAL_CONFIG['chat_url']}")

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
        

        answer  = responseData.get('answer', "Sorry, No details found.")
        
       
        content_size = len(responseData.get("contents", []))
        print(content_size)

        logger.info(f"[{request_id}] Search completed successfully")
        return AISearchResultDto(result=answer, requestId=request_id, contentSize =content_size)

       
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
    """Health check endpoint"""
    try:
        # Check Elasticsearch connection asynchronously
        es_healthy = await search_service.es_client.ping()
        
        # Check model loaded
        model_healthy = hasattr(search_service, 'st_model')
        
        # Check Mistral service connection asynchronously
        mistral_healthy = False
        try:
            # Simple ping to Mistral service
            response = await search_service.http_client.get(
                    MISTRAL_CONFIG['version_url'],
                    timeout=5
            )
            mistral_healthy = response.status_code == 200
        except Exception as e:
            logger.warning(f"Mistral service health check failed: {str(e)}")
        
        # Create response
        status = {
            "status": "healthy" if (es_healthy and model_healthy) else "unhealthy",
            "elasticsearch": es_healthy,
            "model": model_healthy,
            "mistral": mistral_healthy
        }
        
        if not (es_healthy and model_healthy):
            raise HTTPException(status_code=503, detail=status)
            
        return status
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

if __name__ == "__main__":
    # Use uvicorn with reload for development
    uvicorn.run("master:app", host="0.0.0.0", port=9000, reload=True)