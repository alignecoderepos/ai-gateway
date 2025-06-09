"""
Provider registry implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, Type
import logging
import importlib

from gateway.providers.base import Provider
from gateway.constants import (
    PROVIDER_OPENAI, PROVIDER_ANTHROPIC, 
    PROVIDER_GEMINI, PROVIDER_BEDROCK, 
    PROVIDER_AZURE, PROVIDER_MISTRAL
)


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for managing providers in the AI Gateway.
    Handles lazy loading and access to provider implementations.
    """
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, Provider] = {}
        self._provider_classes: Dict[str, Type[Provider]] = {}
        self._provider_modules: Dict[str, str] = {
            PROVIDER_OPENAI: "gateway.providers.openai",
            PROVIDER_ANTHROPIC: "gateway.providers.anthropic",
            PROVIDER_GEMINI: "gateway.providers.gemini",
            PROVIDER_BEDROCK: "gateway.providers.bedrock",
            PROVIDER_AZURE: "gateway.providers.azure",
            PROVIDER_MISTRAL: "gateway.providers.mistral",
        }
    
    def register_provider(self, provider_name: str, provider: Provider) -> None:
        """
        Register a provider instance.
        
        Args:
            provider_name: Name of the provider
            provider: Provider instance
        """
        self._providers[provider_name] = provider
        logger.debug(f"Registered provider: {provider_name}")
    
    def register_provider_class(self, provider_name: str, provider_class: Type[Provider]) -> None:
        """
        Register a provider class for lazy loading.
        
        Args:
            provider_name: Name of the provider
            provider_class: Provider class
        """
        self._provider_classes[provider_name] = provider_class
        logger.debug(f"Registered provider class: {provider_name}")
    
    def register_provider_module(self, provider_name: str, module_path: str) -> None:
        """
        Register a module path for a provider.
        
        Args:
            provider_name: Name of the provider
            module_path: Path to the provider module
        """
        self._provider_modules[provider_name] = module_path
        logger.debug(f"Registered provider module: {provider_name} -> {module_path}")
    
    def get_provider(self, provider_name: str) -> Optional[Provider]:
        """
        Get a provider instance, loading it if necessary.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider instance if found, None otherwise
        """
        # Return existing provider instance if available
        if provider_name in self._providers:
            return self._providers[provider_name]
        
        # Try to load from registered class
        if provider_name in self._provider_classes:
            provider_class = self._provider_classes[provider_name]
            provider = provider_class()
            self._providers[provider_name] = provider
            return provider
        
        # Try to load from registered module
        if provider_name in self._provider_modules:
            try:
                module_path = self._provider_modules[provider_name]
                module = importlib.import_module(module_path)
                
                # Look for a provider class in the module
                provider_class_name = f"{provider_name.capitalize()}Provider"
                if hasattr(module, provider_class_name):
                    provider_class = getattr(module, provider_class_name)
                    provider = provider_class()
                    self._providers[provider_name] = provider
                    return provider
                
                logger.error(f"Provider class '{provider_class_name}' not found in module '{module_path}'")
            except ImportError as e:
                logger.error(f"Failed to import provider module '{module_path}': {e}")
        
        logger.warning(f"Provider not found: {provider_name}")
        return None
    
    def list_providers(self) -> List[str]:
        """
        List all registered providers.
        
        Returns:
            List of provider names
        """
        # Combine all registered providers
        all_providers = set(self._providers.keys())
        all_providers.update(self._provider_classes.keys())
        all_providers.update(self._provider_modules.keys())
        
        return sorted(list(all_providers))


# Global provider registry instance
provider_registry = ProviderRegistry()