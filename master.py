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

# Configure JSON logging
logger = logging.getLogger(__name__)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Define request and response models
class SearchRequest(BaseModel):
    queries: List[str]
    tenant_id: str
    top_k: int = 5
    threshold: float = 0.7
    metadata_filters: Optional[Dict[str, Any]] = None
    generate_answer: bool = False
    answer_tone: str = "polite"
    max_answer_length: int = 300


class Message(BaseModel):
    role: str
    content: str

class GeneratedAnswer(BaseModel):
    model: str
    created_at: str
    message: Message
    done_reason: str
    done: bool
    total_duration: int
    load_duration: int
    prompt_eval_count: int
    prompt_eval_duration: int
    eval_count: int
    eval_duration: int

class RetrievedDocument(BaseModel):
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class SearchResult(BaseModel):
    query: str
    results: List[RetrievedDocument]

class SearchResponse(BaseModel):
    query_id: str
    processing_time: float
    generated_answer: Optional[GeneratedAnswer] = None
    results: List[SearchResult] = Field(..., alias="results")  # Include retrieved documents

# Initialize app
app = FastAPI(title="Vector Search Service")

# Async Kafka consumer handler
async def consume_messages():
    """Asynchronous kafka consumer to process messages"""
    consumer_config = {
        'bootstrap.servers': KAFKA_CONFIG['bootstrap_servers'],
        'group.id': KAFKA_CONFIG.get('consumer_group', 'vector_search_consumer'),
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    }
    
    consumer = Consumer(consumer_config)
    consumer.subscribe([KAFKA_CONFIG['input_topic']])
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                # No message, continue polling
                await asyncio.sleep(0.1)
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info(f"Reached end of partition {msg.partition()}")
                else:
                    logger.error(f"Error while consuming: {msg.error()}")
            else:
                try:
                    # Process the message asynchronously
                    value = json.loads(msg.value().decode('utf-8'))
                    
                    # Create a task to process the message asynchronously
                    asyncio.create_task(process_kafka_message(value))
                    
                    # Commit the message manually
                    consumer.commit(msg)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

async def process_kafka_message(message):
    """Process a message from Kafka"""
    try:
        # Get the search service
        search_service = app.state.search_service
        
        # Process the message based on its contents
        logger.info(f"Processing Kafka message: {message}")
        
        # Example: You might have different types of messages to process
        if 'request_type' in message:
            if message['request_type'] == 'search':
                # Process a search request
                result = await search_service.process_search_request(
                    message['queries'],
                    message['tenant_id'],
                    message.get('top_k', 5),
                    message.get('threshold', 0.7),
                    message.get('metadata_filters'),
                    message.get('generate_answer', False),
                    message.get('answer_tone', 'polite'),
                    message.get('max_answer_length', 300)
                )
                
                # Produce result to output topic if needed
                await search_service.send_results_to_kafka(result)
    except Exception as e:
        logger.error(f"Error processing Kafka message: {str(e)}", exc_info=True)

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
    
    def _produce(self, topic, key, value):
        """Send message to Kafka topic"""
        try:
            if isinstance(value, dict):
                value = json.dumps(value).encode('utf-8')
            elif not isinstance(value, bytes):
                value = str(value).encode('utf-8')
                
            if key is not None and not isinstance(key, bytes):
                key = str(key).encode('utf-8')
                
            self.producer.produce(topic, key=key, value=value)
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
    
    async def generate_embeddings(self, queries: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of queries using a thread pool"""
        try:
            start_time = datetime.datetime.now()
            
            # Move the embedding generation to a separate thread 
            # since SentenceTransformer is not async-compatible
            embeddings = await asyncio.to_thread(self._generate_embeddings_sync, queries)
            
            end_time = datetime.datetime.now()
            logger.info(f"Generated {len(queries)} embeddings in {(end_time - start_time).total_seconds()} seconds")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
            raise
    
    def _generate_embeddings_sync(self, queries: List[str]) -> List[List[float]]:
        """Synchronous method to generate embeddings (runs in a thread)"""
        embeddings = self.st_model.encode(queries)
        return embeddings.tolist()
    

    async def search_elasticsearch(
        self, 
        embedding: List[float], 
        tenant_id: str, 
        top_k: int = 5, 
        threshold: float = 0.7,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search Elasticsearch using dot product with normalized vectors for ES 7.17"""
        try:
            
            # Build the filter conditions
            filter_conditions = [{"term": {"tenant_id": tenant_id}}]
            
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
                            "source": "cosineSimilarity(params.query_vector, 'content_vector')",
                            "params": {"query_vector": embedding}
                        }
                    }
                }
            }
            
            logger.info("query: ")
            logger.info(query)
            
            # Execute search
            response = await self.es_client.search(
                index=ES_CONFIG['index_name'],
                body=query,
                size=top_k
            )
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                score = hit['_score']
                # Note: With normalized vectors, dot product results range from -1 to 1,
                # same as cosine similarity
                if score >= threshold:
                    results.append({
                        "content": hit['_source']['content'],
                        "document_id": hit['_source']['document_id'],
                        "score": score,
                        "metadata": hit['_source'].get('metadata', {})
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {str(e)}", exc_info=True)
            raise
    

    async def generate_answer_from_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        tone: str = "polite",
        max_length: int = 300
    ) -> Dict[str, Any]:
        """Generate an answer to the query using LLM based on the search results"""
        try:
            # Combine result contents into context
            context = "\n\n".join([result["content"] for result in results if "content" in result])
            
            # Prepare the prompt for model
            system_prompt = f"""You are a helpful assistant that answers questions based on provided documents. 
            Please respond in a {tone} tone. Keep your answer concise, around {max_length} characters.
            Use only the information from the documents to answer the question. If the documents don't contain
            the necessary information, admit that you don't know."""
            
            user_prompt = f"""Documents:
            {context}
            
            Question: {query}
            
            Please answer the question based only on the provided documents."""
            
            # Prepare the request payload
            data = {
                "model": MISTRAL_CONFIG['model'],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "max_tokens": max(100, max_length // 4)  # Estimate tokens based on characters
            }
            
            logger.info("Sending request to LLM: %s", json.dumps(data, indent=2))
            
            # Use httpx for async request
            async with self.http_client as client:
                response = await client.post(
                    MISTRAL_CONFIG['service_url'],
                    headers={"Content-Type": "application/json"},
                    json=data,
                    timeout=MISTRAL_CONFIG['timeout']
                )
            
            logger.info("Response Status: %d", response.status_code)
            
            if response.status_code != 200:
                logger.error(f"LLM service error: {response.status_code} - {response.text}")
                return {"error": f"Error generating answer: LLM service returned status {response.status_code}"}
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error generating answer with LLM: {str(e)}", exc_info=True)
            return {"error": f"Error generating answer: {str(e)}"}
    
    async def process_search_request(
        self, 
        queries: List[str], 
        tenant_id: str, 
        top_k: int = 5, 
        threshold: float = 0.7,
        metadata_filters: Optional[Dict[str, Any]] = None,
        generate_answer: bool = False,
        answer_tone: str = "polite",
        max_answer_length: int = 300
    ) -> Dict[str, Any]:
        """Process a search request end-to-end using async operations"""
        start_time = datetime.datetime.now()
        
        # Generate embeddings for all queries
        embeddings = await self.generate_embeddings(queries)
        
        # Create tasks for concurrent Elasticsearch searches
        search_tasks = [
            self.search_elasticsearch(
                embedding, 
                tenant_id, 
                top_k, 
                threshold,
                metadata_filters
            ) 
            for embedding in embeddings
        ]
        
        # Run searches concurrently
        search_results = await asyncio.gather(*search_tasks)
        
        # Process results and generate answers if requested
        all_results = []
        generated_answer = None
        
        # Create tasks for generating answers if needed
        answer_tasks = []
        
        for i, results in enumerate(search_results):
            # If we need to generate an answer and have valid results
            if generate_answer and results and len(results) > 0:
                answer_tasks.append((i, self.generate_answer_from_results(
                    queries[i],
                    results,
                    tone=answer_tone,
                    max_length=max_answer_length
                )))
            
            all_results.append({
                "query": queries[i],
                "results": results
            })
        
        # Run answer generation concurrently if there are any tasks
        if answer_tasks:
            # We need to keep track of which query each answer belongs to
            answers = await asyncio.gather(*(task for _, task in answer_tasks))
            # The first valid answer will be our generated_answer
            if answers:
                generated_answer = answers[0]
        
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Prepare response
        query_id = str(uuid.uuid4())
        response = {
            "query_id": query_id,
            "results": all_results,
            "processing_time": processing_time
        }
        
        # Add generated answer if available
        if generated_answer:
            response["generated_answer"] = generated_answer
        
        logger.info(f"Processed search request with ID: {query_id}, processing time: {processing_time}s")
        return response
    
    async def send_results_to_kafka(self, results: Dict[str, Any]) -> bool:
        """Send search results to Kafka topic for async processing"""
        if self.producer is None:
            logger.warning("Kafka producer not initialized, skipping message")
            return False
        
        try:
            await self.producer.send(
                KAFKA_CONFIG['output_topic'],
                value=results
            )
            return True
        except Exception as e:
            logger.error(f"Error sending to Kafka: {str(e)}", exc_info=True)
            return False
    
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
    
    # Start the Kafka consumer in the background
    app.state.consumer_task = asyncio.create_task(consume_messages())
    
    logger.info("Vector Search Service initialized")
    logger.info(f"Using Mistral service at: {MISTRAL_CONFIG['service_url']}")

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
@app.post("/search")
async def search(
    request: SearchRequest,
    search_service: VectorSearchService = Depends(get_search_service)
):
    """Endpoint to search documents using vector similarity"""
    try:
        responseData = await search_service.process_search_request(
            request.queries,
            request.tenant_id,
            request.top_k,
            request.threshold,
            request.metadata_filters,
            request.generate_answer,
            request.answer_tone,
            request.max_answer_length
        )
        
        # Optional: Send results to Kafka asynchronously
        # We use create_task to fire and forget
        asyncio.create_task(
            search_service.send_results_to_kafka(responseData)
        )
        
         # Extract the response
        generated_answer = responseData.generated_answer
        
        if generated_answer and generated_answer.done and generated_answer.message and generated_answer.message.content:
            return JSONResponse(content=generated_answer.message)

        # Return a custom response when no valid message is found
        return JSONResponse(content={
            "role": "hardcoded",
            "content": "Sorry, No details found."
        })
       
    except Exception as e:
        logger.error(f"Search request failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
            async with search_service.http_client as client:
                response = await client.get(
                    MISTRAL_CONFIG['service_url'].split('/v1')[0] + '/health',
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
    uvicorn.run("master:app", host="0.0.0.0", port=8000, reload=True)