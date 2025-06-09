"""
Error handlers for the AI Gateway.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from gateway.errors.exceptions import (
    GatewayError, AuthenticationError, AuthorizationError,
    ModelNotFoundError, ProviderNotFoundError, RateLimitExceededError,
    QuotaExceededError, ValidationError, GuardrailError
)


logger = logging.getLogger(__name__)


def create_error_response(status_code: int, message: str, type: str = "gateway_error", param: str = None) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        type: Error type
        param: Parameter that caused the error
        
    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "message": message,
            "type": type,
            "param": param,
            "code": status_code
        }
    }


async def gateway_exception_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """
    Handler for generic gateway errors.
    
    Args:
        request: FastAPI request
        exc: Gateway error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Gateway error: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            status_code=400,
            message=exc.message,
            type="gateway_error"
        )
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """
    Handler for authentication errors.
    
    Args:
        request: FastAPI request
        exc: Authentication error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Authentication error: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=create_error_response(
            status_code=401,
            message=exc.message,
            type="authentication_error"
        )
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """
    Handler for authorization errors.
    
    Args:
        request: FastAPI request
        exc: Authorization error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Authorization error: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=create_error_response(
            status_code=403,
            message=exc.message,
            type="authorization_error"
        )
    )


async def model_not_found_exception_handler(request: Request, exc: ModelNotFoundError) -> JSONResponse:
    """
    Handler for model not found errors.
    
    Args:
        request: FastAPI request
        exc: Model not found error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Model not found: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=create_error_response(
            status_code=404,
            message=exc.message,
            type="model_not_found_error"
        )
    )


async def provider_not_found_exception_handler(request: Request, exc: ProviderNotFoundError) -> JSONResponse:
    """
    Handler for provider not found errors.
    
    Args:
        request: FastAPI request
        exc: Provider not found error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Provider not found: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=create_error_response(
            status_code=404,
            message=exc.message,
            type="provider_not_found_error"
        )
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    """
    Handler for rate limit exceeded errors.
    
    Args:
        request: FastAPI request
        exc: Rate limit exceeded error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Rate limit exceeded: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=create_error_response(
            status_code=429,
            message=exc.message,
            type="rate_limit_exceeded_error"
        )
    )


async def quota_exceeded_exception_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
    """
    Handler for quota exceeded errors.
    
    Args:
        request: FastAPI request
        exc: Quota exceeded error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Quota exceeded: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content=create_error_response(
            status_code=402,
            message=exc.message,
            type="quota_exceeded_error"
        )
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Handler for validation errors.
    
    Args:
        request: FastAPI request
        exc: Validation error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Validation error: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            status_code=400,
            message=exc.message,
            type="validation_error",
            param=exc.details.get("param") if exc.details else None
        )
    )


async def guardrail_exception_handler(request: Request, exc: GuardrailError) -> JSONResponse:
    """
    Handler for guardrail errors.
    
    Args:
        request: FastAPI request
        exc: Guardrail error exception
        
    Returns:
        JSON response with error details
    """
    logger.error(f"Guardrail error: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            status_code=400,
            message=exc.message,
            type="guardrail_error",
            param="content"
        )
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(GatewayError, gateway_exception_handler)
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(ModelNotFoundError, model_not_found_exception_handler)
    app.add_exception_handler(ProviderNotFoundError, provider_not_found_exception_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)
    app.add_exception_handler(QuotaExceededError, quota_exceeded_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(GuardrailError, guardrail_exception_handler)