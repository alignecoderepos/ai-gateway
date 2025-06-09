"""
Main application for the AI Gateway.
"""
import logging
import os
from pathlib import Path
import argparse
import uvicorn

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from gateway.config.settings import settings
from gateway.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION, LOGO
from gateway.api.router_config import create_api_router
from gateway.middleware import setup_middleware
from gateway.errors.handlers import register_exception_handlers
from gateway.telemetry.setup import init_telemetry
from gateway.core.models import model_registry
from gateway.providers.registry import provider_registry


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )
    
    # Set up middleware
    setup_middleware(app)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Include API router
    app.include_router(create_api_router())
    
    # Add startup event handler
    @app.on_event("startup")
    async def startup_event():
        # Load models
        models_path = os.environ.get("MODELS_PATH") or "models.yaml"
        model_count = len(model_registry.load_models(models_path))
        logger.info(f"Loaded {model_count} models")
        
        # Register default providers
        from gateway.providers.openai import OpenAIProvider
        from gateway.providers.anthropic import AnthropicProvider
        
        provider_registry.register_provider("openai", OpenAIProvider())
        provider_registry.register_provider("anthropic", AnthropicProvider())
        
        # Register additional providers if available
        try:
            from gateway.providers.gemini import GeminiProvider
            provider_registry.register_provider("gemini", GeminiProvider())
        except ImportError:
            logger.warning("Gemini provider not available")
        
        try:
            from gateway.providers.bedrock import BedrockProvider
            provider_registry.register_provider("bedrock", BedrockProvider())
        except ImportError:
            logger.warning("Bedrock provider not available")
        
        try:
            from gateway.providers.azure import AzureProvider
            provider_registry.register_provider("azure", AzureProvider())
        except ImportError:
            logger.warning("Azure provider not available")
        
        try:
            from gateway.providers.mistral import MistralProvider
            provider_registry.register_provider("mistral", MistralProvider())
        except ImportError:
            logger.warning("Mistral provider not available")
        
        # Log startup info
        logger.info(f"AI Gateway v{APP_VERSION} started - Mode: {settings.environment}")
        logger.info(f"Available providers: {', '.join(provider_registry.list_providers())}")
    
    # Add shutdown event handler
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("AI Gateway shutting down")
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": APP_VERSION}
    
    return app


def run_server(host: str = None, port: int = None, reload: bool = False, log_level: str = None):
    """
    Run the AI Gateway server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Whether to enable auto-reload
        log_level: Log level
    """
    # Initialize telemetry
    init_telemetry(log_level)
    
    # Print logo
    print(LOGO)
    
    # Get configuration
    host = host or settings.http.host
    port = port or settings.http.port
    workers = settings.http.workers or 1
    
    logger.info(f"Starting AI Gateway v{APP_VERSION} on http://{host}:{port}")
    
    # Run server
    uvicorn.run(
        "gateway.main:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        workers=workers if not reload else 1,
        log_level=log_level.lower() if log_level else settings.log_level.lower(),
    )


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI Gateway Server")
    parser.add_argument("--host", help="Host to bind to")
    parser.add_argument("--port", type=int, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", help="Log level")
    args = parser.parse_args()
    
    # Run server
    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )