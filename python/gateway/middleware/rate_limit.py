"""
Rate limiting middleware for the AI Gateway.
"""
from fastapi import Request, Response
import logging
import time
from typing import Dict, Tuple, Optional, Callable, Awaitable
import asyncio

from starlette.middleware.base import BaseHTTPMiddleware
from gateway.config.settings import settings
from gateway.errors.exceptions import RateLimitExceededError


logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, rate_limit: int, period: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests per period
            period: Time period in seconds
        """
        self.rate_limit = rate_limit
        self.period = period
        self.requests: Dict[str, Tuple[int, float]] = {}  # key -> (count, start_time)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, key: str) -> bool:
        """
        Check if the rate limit is exceeded for the given key.
        
        Args:
            key: Rate limit key (e.g., API key or IP address)
            
        Returns:
            True if the rate limit is not exceeded, False otherwise
        """
        async with self._lock:
            current_time = time.time()
            count, start_time = self.requests.get(key, (0, current_time))
            
            # Reset count if period has passed
            if current_time - start_time > self.period:
                count = 0
                start_time = current_time
            
            # Check rate limit
            if count >= self.rate_limit:
                return False
            
            # Increment count
            count += 1
            self.requests[key] = (count, start_time)
            
            return True
    
    async def get_rate_limit_headers(self, key: str) -> Dict[str, str]:
        """
        Get rate limit headers for the given key.
        
        Args:
            key: Rate limit key (e.g., API key or IP address)
            
        Returns:
            Dictionary of rate limit headers
        """
        async with self._lock:
            current_time = time.time()
            count, start_time = self.requests.get(key, (0, current_time))
            
            # Reset count if period has passed
            if current_time - start_time > self.period:
                count = 0
                start_time = current_time
                self.requests[key] = (count, start_time)
            
            # Calculate remaining requests and reset time
            remaining = max(0, self.rate_limit - count)
            reset_time = int(start_time + self.period - current_time)
            
            return {
                "X-RateLimit-Limit": str(self.rate_limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        Rate limiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        requests = settings.rate_limit_requests
        period = settings.rate_limit_period
        _rate_limiter = RateLimiter(requests, period)
    
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(
        self,
        app,
        rate_limit: int = None,
        period: int = None,
        key_func: Callable[[Request], str] = None
    ):
        """
        Initialize the rate limit middleware.
        
        Args:
            app: FastAPI application
            rate_limit: Maximum number of requests per period
            period: Time period in seconds
            key_func: Function to extract the rate limit key from the request
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(
            rate_limit or settings.rate_limit_requests,
            period or settings.rate_limit_period
        )
        self.key_func = key_func or self._default_key_func
    
    @staticmethod
    def _default_key_func(request: Request) -> str:
        """
        Default function to extract the rate limit key from the request.
        Uses the API key if available, otherwise the client IP.
        
        Args:
            request: FastAPI request
            
        Returns:
            Rate limit key
        """
        # Try to get API key from authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Return API key
        
        # Fall back to client IP
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Function to call the next middleware or route handler
            
        Returns:
            FastAPI response
        """
        # Skip rate limiting for some paths
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Skip rate limiting if disabled
        if not settings.enable_rate_limit:
            return await call_next(request)
        
        # Get rate limit key
        key = self.key_func(request)
        
        # Check rate limit
        if not await self.rate_limiter.check_rate_limit(key):
            logger.warning(f"Rate limit exceeded for key: {key}")
            raise RateLimitExceededError("Rate limit exceeded. Please try again later.")
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        rate_limit_headers = await self.rate_limiter.get_rate_limit_headers(key)
        for header_name, header_value in rate_limit_headers.items():
            response.headers[header_name] = header_value
        
        return response