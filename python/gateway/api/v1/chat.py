"""
Chat completion endpoints for the AI Gateway.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, AsyncGenerator

from gateway.constants import (
    API_PREFIX, CHAT_COMPLETIONS_PATH, 
    AUTH_HEADER, REQUEST_ID_HEADER, THREAD_ID_HEADER, RUN_ID_HEADER
)
from gateway.core.types import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse,
    ErrorResponse, GatewayResponse
)
from gateway.core.executor import RequestExecutor, RequestContext
from gateway.middleware.auth import verify_api_key
from gateway.errors.exceptions import (
    GatewayError, AuthenticationError, ModelNotFoundError,
    RateLimitExceededError, QuotaExceededError
)
from gateway.guardrails.service import GuardrailsService


logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()
guardrails_service = GuardrailsService()


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
    
    # Extract user ID from Authorization header if available
    user_id = None
    auth_header = headers.get(AUTH_HEADER)
    if auth_header and auth_header.startswith("Bearer "):
        # This is a simplistic approach. In a real implementation, 
        # you might decode a JWT or look up the API key to get the user ID.
        user_id = auth_header[7:]  # Remove "Bearer " prefix
    
    # Create context
    context = RequestContext(
        request_id=headers.get(REQUEST_ID_HEADER, str(uuid.uuid4())),
        user_id=user_id,
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


@router.post("", response_model=GatewayResponse[ChatCompletionResponse])
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
        
        # Apply input guardrails if enabled
        if guardrails_service.is_enabled():
            await guardrails_service.evaluate_chat_input(body, context)
        
        # Check if streaming
        if body.stream:
            return StreamingResponse(
                streaming_chat_completion(body, context),
                media_type="text/event-stream"
            )
        
        # Execute request
        executor = RequestExecutor()
        response = await executor.execute_chat_completion(body, context)
        
        # Apply output guardrails if enabled
        if guardrails_service.is_enabled():
            await guardrails_service.evaluate_chat_output(response.response, context)
        
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