"""
API router configuration for the AI Gateway.
"""
from fastapi import APIRouter

from gateway.constants import (
    API_PREFIX, CHAT_COMPLETIONS_PATH, COMPLETIONS_PATH,
    EMBEDDINGS_PATH, IMAGES_PATH, MODELS_PATH
)
from gateway.api.v1 import chat, embeddings, models, images


def create_api_router() -> APIRouter:
    """
    Create and configure the main API router.
    
    Returns:
        Configured API router
    """
    # Create main API router
    api_router = APIRouter(prefix=API_PREFIX)
    
    # Register v1 endpoint routers
    api_router.include_router(
        chat.router,
        prefix=CHAT_COMPLETIONS_PATH,
        tags=["chat"]
    )
    
    api_router.include_router(
        embeddings.router,
        prefix=EMBEDDINGS_PATH,
        tags=["embeddings"]
    )
    
    api_router.include_router(
        models.router,
        prefix=MODELS_PATH,
        tags=["models"]
    )
    
    api_router.include_router(
        images.router,
        prefix=IMAGES_PATH,
        tags=["images"]
    )
    
    return api_router