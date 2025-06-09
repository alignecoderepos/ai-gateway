"""
Models endpoints for the AI Gateway.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
from typing import Dict, Optional

from gateway.core.types import ModelListResponse
from gateway.core.models import model_registry
from gateway.middleware.auth import verify_api_key
from gateway.api.v1.chat import get_request_context, error_response


logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()


@router.get("", response_model=ModelListResponse)
async def list_models(
    request: Request,
    auth: str = Depends(verify_api_key)
):
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


@router.get("/{model_id}", response_model=Dict)
async def get_model(
    model_id: str,
    request: Request,
    auth: str = Depends(verify_api_key)
):
    """
    Get a specific model by ID.
    
    Args:
        model_id: Model ID
        request: FastAPI request
        auth: API key (from Authorization header)
    
    Returns:
        Model details
    """
    try:
        # Get context
        context = get_request_context(request)
        
        # Get model
        model = model_registry.get_model(model_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response(
                    status_code=404,
                    message=f"Model not found: {model_id}",
                    type="model_not_found",
                    param="model_id"
                ).model_dump()
            )
        
        # Convert to response format
        return {
            "id": model.model,
            "object": "model",
            "created": 0,  # We don't track creation time
            "owned_by": model.model_provider,
            "capabilities": [cap.value for cap in model.capabilities],
            "type": model.type.value,
            "description": model.description,
            "limits": model.limits.model_dump(),
            "price": model.price.model_dump(),
            "parameters": model_registry.get_parameter_schema(model_id)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                status_code=500,
                message=f"Failed to get model: {str(e)}",
                type="internal_server_error"
            ).model_dump()
        )