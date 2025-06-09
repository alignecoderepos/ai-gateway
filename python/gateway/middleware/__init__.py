"""
Middleware package initialization.
"""
from fastapi import FastAPI

from gateway.config.settings import settings
from gateway.middleware.cors import setup_cors
from gateway.middleware.logging import LoggingMiddleware
from gateway.middleware.rate_limit import RateLimitMiddleware


def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the FastAPI application.
    
    Args:
        app: FastAPI application
    """
    # Set up CORS
    setup_cors(app)
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add rate limiting middleware if enabled
    if settings.enable_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            rate_limit=settings.rate_limit_requests,
            period=settings.rate_limit_period
        )