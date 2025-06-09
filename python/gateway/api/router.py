"""
API router implementation for the AI Gateway.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, AsyncGenerator

from gateway.constants import (
    API_PREFIX, CHAT_COMPLETIONS_PATH, COMPLETIONS_PATH, 
    EMBEDDINGS_PATH, IMAGES_PATH, MODELS_PATH, HEALTH_PATH,
    AUTH_HEADER, REQUEST_ID_HEADER, THREAD_ID_HEADER, RUN_ID_HEADER
)
from gateway.core.types import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse,
    EmbeddingRequest, EmbeddingResponse,
    ImageGenerationRequest, ImageGenerationResponse,
    ModelListResponse, ErrorResponse, GatewayResponse
)
from gateway.core.executor import RequestExecutor, RequestContext
from gateway.core.models import model_registry
from gateway.middleware.auth import verify_api_key
from gateway.errors.exceptions import (
    GatewayError, AuthenticationError, ModelNotFoundError,
    RateLimitExceededError, QuotaExceededError
)


logger = logging.getLogger(__name__)

# Create API router
api_router = APIRouter(prefix=API_PREFIX)


def get_request_context(request: Request) -> RequestContext:
    """
    Create a request context from the HTTP request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request context
    """
    # Extract headers
    headers = dict(request.headers)
    
    # Create context
    context = RequestContext(
        request_id=headers.get(REQUEST_ID_HEADER, str(uuid.uuid4())),
        thread_id=headers.get(THREAD_ID_HEADER),
        run_id=headers.get(RUN_ID_HEADER),
        headers=headers,
        metadata={
            "client_host": request.client.host if request.client else None,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return context


def error_response(status_code: int, message: str, type: str = "gateway_error", param: Optional[str] = None) -> ErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        type: Error type
        param: Parameter that caused the error
        
    Returns:
        Error response
    """
    return ErrorResponse(
        error={
            "message": message,
            "type": type,
            "param": param,
            "code": status_code
        }
    )


@api_router.get(HEALTH_PATH, status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@api_router.get(MODELS_PATH, response_model=ModelListResponse)
async def list_models(request: Request, auth: str = Depends(verify_api_key)):
    """
    List available models.
    
    Args:
        request: FastAPI request
        auth: API key (from Authorization header)
    
    Returns:
        List of available models
    """
    try:
        # Get context
        context = get_request_context(request)
        
        # Get models
        models = model_registry.list_models()
        
        # Convert to response format
        model_data = []
        for model in models:
            model_data.append({
                "id": model.model,
                "object": "model",
                "created": 0,  # We don't track creation time
                "owned_by": model.model_provider,
                "capabilities": [cap.value for cap in model.capabilities],
                "type": model.type.value,
                "description": model.description,
                "limits": model.limits.model_dump(),
                "price": model.price.model_dump()
            })
        
        return ModelListResponse(
            object="list",
            data=model_data
        )
    
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                status_code=500,
                message=f"Failed to list models: {str(e)}",
                type="internal_server_error"
            ).model_dump()
        )


@api_router.post(CHAT_COMPLETIONS_PATH, response_model=GatewayResponse[ChatCompletionResponse])
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Create a chat completion.
    
    Args:
        request: FastAPI request
        body: Chat completion request
        auth: API key (from Authorization header)
    
    Returns:
        Chat completion response
    """
    try:
        # Get context
        context = get_request_context(request)
        
        # Check if streaming
        if body.stream:
            return StreamingResponse(
                streaming_chat_completion(body, context),
                media_type="text/event-stream"
            )
        
        # Execute request
        executor = RequestExecutor()
        response = await executor.execute_chat_completion(body, context)
        
        return response
    
    except GatewayError as e:
        logger.error(f"Gateway error in chat completion: {e}")
        status_code = 400
        
        if isinstance(e, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(e, ModelNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, RateLimitExceededError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(e, QuotaExceededError):
            status_code = status.HTTP_402_PAYMENT_REQUIRED
        
        raise HTTPException(
            status_code=status_code,
            detail=error_response(
                status_code=status_code,
                message=str(e),
                type=e.__class__.__name__.lower()
            ).model_dump()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                status_code=500,
                message=f"Internal server error: {str(e)}",
                type="internal_server_error"
            ).model_dump()
        )


async def streaming_chat_completion(
    request: ChatCompletionRequest,
    context: RequestContext
) -> AsyncGenerator[str, None]:
    """
    Stream a chat completion.
    
    Args:
        request: Chat completion request
        context: Request context
    
    Yields:
        SSE formatted response chunks
    """
    try:
        # Execute streaming request
        executor = RequestExecutor()
        
        async for chunk in executor.execute_streaming_chat_completion(request, context):
            # Format as SSE
            yield f"data: {json.dumps(chunk.model_dump())}\n\n"
        
        # End of stream
        yield "data: [DONE]\n\n"
    
    except GatewayError as e:
        logger.error(f"Gateway error in streaming chat completion: {e}")
        error_data = error_response(
            status_code=400,
            message=str(e),
            type=e.__class__.__name__.lower()
        ).model_dump()
        
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        logger.error(f"Unexpected error in streaming chat completion: {e}")
        error_data = error_response(
            status_code=500,
            message=f"Internal server error: {str(e)}",
            type="internal_server_error"
        ).model_dump()
        
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@api_router.post(EMBEDDINGS_PATH, response_model=GatewayResponse[EmbeddingResponse])
async def create_embeddings(
    request: Request,
    body: EmbeddingRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Create embeddings.
    
    Args:
        request: FastAPI request
        body: Embeddings request
        auth: API key (from Authorization header)
    
    Returns:
        Embeddings response
    """
    try:
        # Get context
        context = get_request_context(request)
        
        # Execute request
        executor = RequestExecutor()
        response = await executor.execute_embeddings(body, context)
        
        return response
    
    except GatewayError as e:
        logger.error(f"Gateway error in embeddings: {e}")
        status_code = 400
        
        if isinstance(e, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(e, ModelNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, RateLimitExceededError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(e, QuotaExceededError):
            status_code = status.HTTP_402_PAYMENT_REQUIRED
        
        raise HTTPException(
            status_code=status_code,
            detail=error_response(
                status_code=status_code,
                message=str(e),
                type=e.__class__.__name__.lower()
            ).model_dump()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                status_code=500,
                message=f"Internal server error: {str(e)}",
                type="internal_server_error"
            ).model_dump()
        )


@api_router.post(IMAGES_PATH, response_model=GatewayResponse[ImageGenerationResponse])
async def create_image(
    request: Request,
    body: ImageGenerationRequest,
    auth: str = Depends(verify_api_key)
):
    """
    Create an image.
    
    Args:
        request: FastAPI request
        body: Image generation request
        auth: API key (from Authorization header)
    
    Returns:
        Image generation response
    """
    try:
        # Get context
        context = get_request_context(request)
        
        # Execute request
        executor = RequestExecutor()
        response = await executor.execute_image_generation(body, context)
        
        return response
    
    except GatewayError as e:
        logger.error(f"Gateway error in image generation: {e}")
        status_code = 400
        
        if isinstance(e, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(e, ModelNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, RateLimitExceededError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(e, QuotaExceededError):
            status_code = status.HTTP_402_PAYMENT_REQUIRED
        
        raise HTTPException(
            status_code=status_code,
            detail=error_response(
                status_code=status_code,
                message=str(e),
                type=e.__class__.__name__.lower()
            ).model_dump()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in image generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                status_code=500,
                message=f"Internal server error: {str(e)}",
                type="internal_server_error"
            ).model_dump()
        )