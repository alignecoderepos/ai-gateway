"""
CORS middleware configuration for the AI Gateway.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from gateway.config.settings import settings


def setup_cors(app: FastAPI, origins: Optional[List[str]] = None) -> None:
    """
    Set up CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application
        origins: List of allowed origins
    """
    # Get origins from settings if not provided
    if origins is None:
        origins = settings.http.cors_allow_origins
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.http.cors_allow_credentials,
        allow_methods=settings.http.cors_allow_methods,
        allow_headers=settings.http.cors_allow_headers,
        max_age=600,  # 10 minutes
    )