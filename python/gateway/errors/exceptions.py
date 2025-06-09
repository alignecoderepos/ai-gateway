"""
Custom exceptions for the AI Gateway.
"""
from typing import Optional, Any


class GatewayError(Exception):
    """Base exception for all AI Gateway errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(GatewayError):
    """Error related to configuration issues."""
    pass


class ProviderError(GatewayError):
    """Error from a provider."""
    pass


class ModelNotFoundError(GatewayError):
    """Error when a requested model is not found."""
    pass


class ProviderNotFoundError(GatewayError):
    """Error when a requested provider is not found."""
    pass


class RouterError(GatewayError):
    """Error in the routing engine."""
    pass


class ExecutionError(GatewayError):
    """Error during request execution."""
    pass


class AuthenticationError(GatewayError):
    """Authentication error."""
    pass


class AuthorizationError(GatewayError):
    """Authorization error."""
    pass


class RateLimitExceededError(GatewayError):
    """Rate limit exceeded error."""
    pass


class QuotaExceededError(GatewayError):
    """Quota or budget exceeded error."""
    pass


class ValidationError(GatewayError):
    """Validation error."""
    pass


class GuardrailError(GatewayError):
    """Error in the guardrails service."""
    pass


class UsageTrackingError(GatewayError):
    """Error in usage tracking."""
    pass