"""
Image generation endpoints for the AI Gateway.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
from typing import Dict, Optional

from gateway.core.types import (
    ImageGenerationRequest, ImageGenerationResponse,
    ErrorResponse, GatewayResponse
)
from gateway.core.executor import RequestExecutor, RequestContext
from gateway.middleware.auth import verify_api_key
from gateway.errors.exceptions import (
    GatewayError, AuthenticationError, ModelNotFoundError,
    RateLimitExceededError, QuotaExceededError
)
from gateway.api.v1.chat import get_request_context, error_response


logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()


@router.post("", response_model=GatewayResponse[ImageGenerationResponse])
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