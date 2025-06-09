"""
Core executor implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable, TypeVar, Generic, AsyncGenerator
import logging
import time
import uuid
from datetime import datetime

from gateway.core.types import (
    ChatCompletionRequest, ChatCompletionResponse, 
    EmbeddingRequest, EmbeddingResponse,
    ImageGenerationRequest, ImageGenerationResponse,
    Usage, GatewayResponse
)
from gateway.core.models import model_registry
from gateway.providers.registry import provider_registry
from gateway.routing.router import RoutingEngine, Target
from gateway.telemetry.logging import request_logger
from gateway.usage.storage import UsageStorage
from gateway.errors.exceptions import (
    ModelNotFoundError, ProviderNotFoundError, ExecutionError,
    RateLimitExceededError, QuotaExceededError
)


logger = logging.getLogger(__name__)

T = TypeVar('T')
ResponseType = TypeVar('ResponseType')


class RequestContext:
    """Context for a request execution."""
    
    def __init__(
        self, 
        request_id: str = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize request context.
        
        Args:
            request_id: Unique ID for this request
            user_id: ID of the user making the request
            thread_id: Thread ID for conversation context
            run_id: Run ID for tracking executions
            headers: HTTP headers for the request
            metadata: Additional metadata for the request
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.headers = headers or {}
        self.metadata = metadata or {}
        self.start_time = time.time()
        self.target_model: Optional[str] = None
        self.target_provider: Optional[str] = None
        
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        return int((time.time() - self.start_time) * 1000)
    
    def with_target(self, target: Target) -> 'RequestContext':
        """Update context with target information."""
        if "model" in target:
            self.target_model = target["model"]
        if "provider" in target:
            self.target_provider = target["provider"]
        return self


class RequestExecutor:
    """
    Executor for AI Gateway requests.
    Handles routing, execution, telemetry, and error handling.
    """
    
    def __init__(
        self, 
        routing_engine: Optional[RoutingEngine] = None,
        usage_storage: Optional[UsageStorage] = None,
    ):
        """
        Initialize the request executor.
        
        Args:
            routing_engine: Engine for routing requests to providers
            usage_storage: Storage for tracking usage
        """
        self.routing_engine = routing_engine or RoutingEngine()
        self.usage_storage = usage_storage
    
    async def execute_chat_completion(
        self, 
        request: ChatCompletionRequest,
        context: Optional[RequestContext] = None,
    ) -> GatewayResponse[ChatCompletionResponse]:
        """
        Execute a chat completion request.
        
        Args:
            request: The chat completion request
            context: Request execution context
            
        Returns:
            Gateway response with the chat completion response
        """
        context = context or RequestContext()
        start_time = time.time()
        
        # Log request
        request_logger.info(
            "Chat completion request", 
            extra={
                "request_id": context.request_id,
                "model": request.model,
                "messages_count": len(request.messages),
                "stream": request.stream,
                "user_id": context.user_id,
                "thread_id": context.thread_id,
            }
        )
        
        try:
            # Get target from routing engine
            target = await self.routing_engine.route_chat_request(request, context)
            context.with_target(target)
            
            # Get provider for target
            provider_name = target.get("provider")
            if not provider_name:
                raise ProviderNotFoundError(f"No provider specified for model {target.get('model')}")
            
            provider = provider_registry.get_provider(provider_name)
            if not provider:
                raise ProviderNotFoundError(f"Provider not found: {provider_name}")
            
            # Execute request with provider
            model_name = target.get("model", request.model)
            modified_request = request.model_copy(update={"model": model_name})
            
            # Apply any target-specific parameters
            for key, value in target.items():
                if key not in ["model", "provider"] and hasattr(modified_request, key):
                    setattr(modified_request, key, value)
            
            response = await provider.create_chat_completion(modified_request, context)
            
            # Track usage
            if self.usage_storage and response.usage:
                await self.usage_storage.record_usage(
                    provider=provider_name,
                    model=model_name,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    latency_ms=context.elapsed_ms(),
                    success=True,
                )
            
            # Log success
            request_logger.info(
                "Chat completion success",
                extra={
                    "request_id": context.request_id,
                    "model": model_name,
                    "provider": provider_name,
                    "latency_ms": context.elapsed_ms(),
                    "tokens": response.usage.total_tokens if response.usage else None,
                }
            )
            
            return GatewayResponse(
                response=response,
                usage=response.usage or Usage(
                    prompt_tokens=0, 
                    completion_tokens=0, 
                    total_tokens=0
                )
            )
            
        except Exception as e:
            # Log error
            request_logger.error(
                f"Chat completion error: {str(e)}",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "error": str(e),
                    "latency_ms": context.elapsed_ms(),
                }
            )
            
            # Track failed usage
            if self.usage_storage:
                await self.usage_storage.record_usage(
                    provider=context.target_provider or "unknown",
                    model=context.target_model or request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=context.elapsed_ms(),
                    success=False,
                    error=str(e),
                )
            
            # Re-raise the exception
            raise
    
    async def execute_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[RequestContext] = None,
    ) -> AsyncGenerator[Any, None]:
        """
        Execute a streaming chat completion request.
        
        Args:
            request: The chat completion request
            context: Request execution context
            
        Yields:
            Streaming response chunks
        """
        context = context or RequestContext()
        start_time = time.time()
        
        # Log request
        request_logger.info(
            "Streaming chat completion request", 
            extra={
                "request_id": context.request_id,
                "model": request.model,
                "messages_count": len(request.messages),
                "user_id": context.user_id,
                "thread_id": context.thread_id,
            }
        )
        
        try:
            # Get target from routing engine
            target = await self.routing_engine.route_chat_request(request, context)
            context.with_target(target)
            
            # Get provider for target
            provider_name = target.get("provider")
            if not provider_name:
                raise ProviderNotFoundError(f"No provider specified for model {target.get('model')}")
            
            provider = provider_registry.get_provider(provider_name)
            if not provider:
                raise ProviderNotFoundError(f"Provider not found: {provider_name}")
            
            # Execute request with provider
            model_name = target.get("model", request.model)
            modified_request = request.model_copy(update={"model": model_name, "stream": True})
            
            # Apply any target-specific parameters
            for key, value in target.items():
                if key not in ["model", "provider"] and hasattr(modified_request, key):
                    setattr(modified_request, key, value)
            
            # Track metrics for streaming
            input_tokens = 0
            output_tokens = 0
            
            # Stream response
            async for chunk in provider.create_streaming_chat_completion(modified_request, context):
                yield chunk
                
                # Estimate token count for streaming (this is approximate)
                if hasattr(chunk, "choices") and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, "delta") and choice.delta.get("content"):
                            output_tokens += len(choice.delta["content"].split()) // 3  # Very rough approximation
            
            # Track usage after streaming completes
            if self.usage_storage:
                # For streaming, we don't have exact token counts, so we need to estimate
                # This could be improved with a proper token counter
                input_tokens = sum(len(m.content.split()) if isinstance(m.content, str) else 50 for m in request.messages) // 3
                
                await self.usage_storage.record_usage(
                    provider=provider_name,
                    model=model_name,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    latency_ms=context.elapsed_ms(),
                    success=True,
                )
            
            # Log success
            request_logger.info(
                "Streaming chat completion success",
                extra={
                    "request_id": context.request_id,
                    "model": model_name,
                    "provider": provider_name,
                    "latency_ms": context.elapsed_ms(),
                    "estimated_tokens": input_tokens + output_tokens,
                }
            )
            
        except Exception as e:
            # Log error
            request_logger.error(
                f"Streaming chat completion error: {str(e)}",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "error": str(e),
                    "latency_ms": context.elapsed_ms(),
                }
            )
            
            # Track failed usage
            if self.usage_storage:
                await self.usage_storage.record_usage(
                    provider=context.target_provider or "unknown",
                    model=context.target_model or request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=context.elapsed_ms(),
                    success=False,
                    error=str(e),
                )
            
            # Re-raise the exception
            raise
    
    async def execute_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[RequestContext] = None,
    ) -> GatewayResponse[EmbeddingResponse]:
        """
        Execute an embeddings request.
        
        Args:
            request: The embeddings request
            context: Request execution context
            
        Returns:
            Gateway response with the embeddings response
        """
        context = context or RequestContext()
        
        # Log request
        request_logger.info(
            "Embeddings request", 
            extra={
                "request_id": context.request_id,
                "model": request.model,
                "user_id": context.user_id,
            }
        )
        
        try:
            # For embeddings, we directly use the specified model and provider
            model_def = model_registry.get_model(request.model)
            if not model_def:
                raise ModelNotFoundError(f"Model not found: {request.model}")
            
            provider_name = model_def.inference_provider.provider
            provider = provider_registry.get_provider(provider_name)
            if not provider:
                raise ProviderNotFoundError(f"Provider not found: {provider_name}")
            
            # Execute request with provider
            response = await provider.create_embeddings(request, context)
            
            # Track usage
            if self.usage_storage and response.usage:
                await self.usage_storage.record_usage(
                    provider=provider_name,
                    model=request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=0,  # Embeddings don't have output tokens
                    total_tokens=response.usage.total_tokens,
                    latency_ms=context.elapsed_ms(),
                    success=True,
                )
            
            # Log success
            request_logger.info(
                "Embeddings success",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "provider": provider_name,
                    "latency_ms": context.elapsed_ms(),
                    "tokens": response.usage.total_tokens if response.usage else None,
                }
            )
            
            return GatewayResponse(
                response=response,
                usage=response.usage or Usage(
                    prompt_tokens=0, 
                    completion_tokens=0, 
                    total_tokens=0
                )
            )
            
        except Exception as e:
            # Log error
            request_logger.error(
                f"Embeddings error: {str(e)}",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "error": str(e),
                    "latency_ms": context.elapsed_ms(),
                }
            )
            
            # Track failed usage
            if self.usage_storage:
                await self.usage_storage.record_usage(
                    provider=context.target_provider or "unknown",
                    model=request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=context.elapsed_ms(),
                    success=False,
                    error=str(e),
                )
            
            # Re-raise the exception
            raise
    
    async def execute_image_generation(
        self,
        request: ImageGenerationRequest,
        context: Optional[RequestContext] = None,
    ) -> GatewayResponse[ImageGenerationResponse]:
        """
        Execute an image generation request.
        
        Args:
            request: The image generation request
            context: Request execution context
            
        Returns:
            Gateway response with the image generation response
        """
        context = context or RequestContext()
        
        # Log request
        request_logger.info(
            "Image generation request", 
            extra={
                "request_id": context.request_id,
                "model": request.model,
                "user_id": context.user_id,
            }
        )
        
        try:
            # For image generation, we directly use the specified model and provider
            model_def = model_registry.get_model(request.model)
            if not model_def:
                raise ModelNotFoundError(f"Model not found: {request.model}")
            
            provider_name = model_def.inference_provider.provider
            provider = provider_registry.get_provider(provider_name)
            if not provider:
                raise ProviderNotFoundError(f"Provider not found: {provider_name}")
            
            # Execute request with provider
            response = await provider.create_image(request, context)
            
            # Since there's no standard token usage for images, we use a fixed cost
            # This could be improved with a more sophisticated cost model
            estimated_usage = Usage(
                prompt_tokens=len(request.prompt.split()) // 3,  # Very rough approximation
                completion_tokens=0,
                total_tokens=len(request.prompt.split()) // 3
            )
            
            # Track usage
            if self.usage_storage:
                await self.usage_storage.record_usage(
                    provider=provider_name,
                    model=request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    input_tokens=estimated_usage.prompt_tokens,
                    output_tokens=0,
                    total_tokens=estimated_usage.total_tokens,
                    latency_ms=context.elapsed_ms(),
                    success=True,
                )
            
            # Log success
            request_logger.info(
                "Image generation success",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "provider": provider_name,
                    "latency_ms": context.elapsed_ms(),
                    "images_count": len(response.data),
                }
            )
            
            return GatewayResponse(
                response=response,
                usage=estimated_usage
            )
            
        except Exception as e:
            # Log error
            request_logger.error(
                f"Image generation error: {str(e)}",
                extra={
                    "request_id": context.request_id,
                    "model": request.model,
                    "error": str(e),
                    "latency_ms": context.elapsed_ms(),
                }
            )
            
            # Track failed usage
            if self.usage_storage:
                await self.usage_storage.record_usage(
                    provider=context.target_provider or "unknown",
                    model=request.model,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=context.elapsed_ms(),
                    success=False,
                    error=str(e),
                )
            
            # Re-raise the exception
            raise


# Global executor instance
executor = RequestExecutor()