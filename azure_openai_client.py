import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncAzureOpenAI
from config import AZURE_CLIENT_CONFIG
logger = logging.getLogger(__name__)

class AzureOpenAIServiceClient:
    """
    Azure OpenAI client for Azure AI Foundry deployments.
    Uses the official OpenAI Python SDK with Azure configuration.
    """
    
    def __init__(self, timeout: int = 60):
        """
        Initialize Azure OpenAI client.
        
        Args:
            timeout (int): Request timeout in seconds
        """
        self.endpoint_url = AZURE_CLIENT_CONFIG['endpoint_url']
        self.api_key = AZURE_CLIENT_CONFIG['api_key'] 
        self.deployment_name = AZURE_CLIENT_CONFIG['deployment_name']  # Changed from deployment_id
        self.api_version = AZURE_CLIENT_CONFIG.get('api_version', '2024-12-01-preview')
        self.timeout = timeout
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint_url,
            api_key=self.api_key,
            timeout=self.timeout
        )

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        top_p: float = 1.0,
        include_usage: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate answer using Azure OpenAI chat completions.

        Args:
            system_prompt (str): System-level instructions
            user_prompt (str): User-level instructions / question
            max_tokens (int): Maximum response tokens
            temperature (float): Sampling temperature for LLM response
            top_p (float): Top-p sampling parameter
            include_usage (bool): Whether to include token usage info (costs extra tokens)
            **kwargs: Additional parameters for the API call

        Returns:
            Dict[str, Any]: Minimal response with just content or error
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                messages=messages,
                model=self.deployment_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            
            # Return minimal response to save on token costs
            if include_usage:
                return {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "completion_tokens": response.usage.completion_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            else:
                # Just return the content - most cost-efficient
                return {"content": response.choices[0].message.content}

        except Exception as e:
            logger.error(f"Exception calling Azure OpenAI: {str(e)}", exc_info=True)
            return {"error": f"Exception calling Azure OpenAI: {str(e)}"}

    async def generate_answer_with_history(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.2,
        top_p: float = 1.0,
        include_usage: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate answer with full conversation history.

        Args:
            messages (List[Dict[str, str]]): List of message objects with 'role' and 'content'
            max_tokens (int): Maximum response tokens
            temperature (float): Sampling temperature
            top_p (float): Top-p sampling parameter
            include_usage (bool): Whether to include token usage info
            **kwargs: Additional parameters for the API call

        Returns:
            Dict[str, Any]: Minimal response with just content or error
        """
        try:
            response = await self.client.chat.completions.create(
                messages=messages,
                model=self.deployment_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            
            # Return minimal response to save on token costs
            if include_usage:
                return {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "completion_tokens": response.usage.completion_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            else:
                return {"content": response.choices[0].message.content}

        except Exception as e:
            logger.error(f"Exception calling Azure OpenAI: {str(e)}", exc_info=True)
            return {"error": f"Exception calling Azure OpenAI: {str(e)}"}

    async def close(self):
        """Close the HTTP client."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Example usage
async def example_usage():
    """Example of cost-efficient usage."""
    
    
    async with AzureOpenAIServiceClient() as client:
        # Most cost-efficient - just get the answer
        response = await client.generate_answer(
            system_prompt="You are a helpful assistant.",
            user_prompt="I am going to Paris, what should I see?",
            temperature=1.0
        )
        
        if "error" not in response:
            print("Answer:", response["content"])  # Just the content
        else:
            print("Error:", response["error"])
            
        # If you need token usage info (costs a bit more)
        response_with_usage = await client.generate_answer(
            system_prompt="You are a helpful assistant.",
            user_prompt="What's the weather like?",
            include_usage=True  # Only when you need to track costs
        )
        
        if "error" not in response_with_usage:
            print("Answer:", response_with_usage["content"])
            print("Tokens used:", response_with_usage["usage"]["total_tokens"])


if __name__ == "__main__":
    asyncio.run(example_usage())