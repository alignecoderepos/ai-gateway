"""
Authentication middleware for the AI Gateway.
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
import logging
import os
from typing import Optional, List, Dict

from gateway.errors.exceptions import AuthenticationError, AuthorizationError
from gateway.config.settings import settings


logger = logging.getLogger(__name__)

# API key header
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


# In-memory store of valid API keys (in a real implementation, this would be a database)
API_KEYS: Dict[str, Dict] = {}


def load_api_keys():
    """Load API keys from environment variables or other sources."""
    # Load a default API key from environment or settings
    default_api_key = settings.openai_api_key or os.environ.get("API_KEY")
    
    if default_api_key:
        # Strip "Bearer " prefix if present
        if default_api_key.startswith("Bearer "):
            default_api_key = default_api_key[7:]
        
        API_KEYS[default_api_key] = {
            "name": "default",
            "permissions": ["*"],  # All permissions
            "rate_limit": None,  # No rate limit
            "quota": None  # No quota
        }
    
    # Load additional API keys (in a real implementation, this would be from a database)
    # For now, we'll just add a test key
    test_api_key = "test-api-key"
    API_KEYS[test_api_key] = {
        "name": "test",
        "permissions": ["*"],
        "rate_limit": 100,  # 100 requests per minute
        "quota": 1000  # 1000 requests per day
    }


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Verify the API key.
    
    Args:
        api_key: API key from request header
        
    Returns:
        The verified API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    # If no keys are loaded, try to load them
    if not API_KEYS:
        load_api_keys()
    
    # If API key is missing, raise 401
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Missing API key", "type": "authentication_error"}}
        )
    
    # Strip "Bearer " prefix if present
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]
    
    # Check if API key exists
    if api_key not in API_KEYS:
        # In development mode, accept any API key
        if settings.environment == "development":
            logger.warning(f"Unknown API key '{api_key}' accepted in development mode")
            return api_key
        
        logger.warning(f"Invalid API key: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Invalid API key", "type": "authentication_error"}}
        )
    
    return api_key


async def check_permissions(api_key: str, required_permissions: List[str]) -> bool:
    """
    Check if the API key has the required permissions.
    
    Args:
        api_key: API key
        required_permissions: List of required permissions
        
    Returns:
        True if the API key has all required permissions, False otherwise
    """
    # If no keys are loaded, try to load them
    if not API_KEYS:
        load_api_keys()
    
    # Get API key data
    api_key_data = API_KEYS.get(api_key)
    
    # If API key doesn't exist, return False
    if not api_key_data:
        return False
    
    # Get permissions for this API key
    permissions = api_key_data.get("permissions", [])
    
    # Check if API key has wildcard permission
    if "*" in permissions:
        return True
    
    # Check if API key has all required permissions
    return all(perm in permissions for perm in required_permissions)


def has_permission(required_permissions: List[str]):
    """
    Dependency function to check if the API key has the required permissions.
    
    Args:
        required_permissions: List of required permissions
        
    Returns:
        Dependency function
    """
    
    async def check_permission_dependency(api_key: str = Depends(verify_api_key)) -> str:
        """
        Check if the API key has the required permissions.
        
        Args:
            api_key: API key from request header
            
        Returns:
            The verified API key
            
        Raises:
            HTTPException: If API key doesn't have the required permissions
        """
        has_perm = await check_permissions(api_key, required_permissions)
        
        if not has_perm:
            logger.warning(f"API key '{api_key}' doesn't have required permissions: {required_permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"message": "Insufficient permissions", "type": "authorization_error"}}
            )
        
        return api_key
    
    return check_permission_dependency