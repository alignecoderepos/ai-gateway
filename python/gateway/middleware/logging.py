"""
Logging middleware for the AI Gateway.
"""
from fastapi import Request, Response
import logging
import time
from typing import Callable, Awaitable
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from gateway.constants import REQUEST_ID_HEADER


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process the request and log request/response details.
        
        Args:
            request: FastAPI request
            call_next: Function to call the next middleware or route handler
            
        Returns:
            FastAPI response
        """
        # Generate request ID if not present
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        
        # Add request ID to request headers
        if REQUEST_ID_HEADER not in request.headers:
            request.headers.__dict__["_list"].append((REQUEST_ID_HEADER.encode(), request_id.encode()))
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Record end time and calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add request ID to response headers
            response.headers[REQUEST_ID_HEADER] = request_id
            
            # Log response
            logger.info(
                f"Response: {response.status_code} in {duration_ms}ms",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            return response
            
        except Exception as e:
            # Record end time and calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                f"Error: {str(e)} in {duration_ms}ms",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True
            )
            
            # Re-raise exception
            raise