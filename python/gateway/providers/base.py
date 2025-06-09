"""
Base provider implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, AsyncGenerator, Protocol, runtime_checkable
import logging
from abc import ABC, abstractmethod

from gateway.core.types import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse,
    EmbeddingRequest, EmbeddingResponse,
    ImageGenerationRequest, ImageGenerationResponse
)


logger = logging.getLogger(__name__)


@runtime_checkable
class Provider(Protocol):
    """Protocol defining the interface for all providers."""
    
    @property
    def name(self) -> str:
        """Get the provider name."""
        ...
    
    async def create_chat_completion(
        self, 
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> ChatCompletionResponse:
        """Create a chat completion."""
        ...
    
    async def create_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> AsyncGenerator[ChatCompletionStreamResponse, None]:
        """Create a streaming chat completion."""
        ...
    
    async def create_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[Any] = None
    ) -> EmbeddingResponse:
        """Create embeddings."""
        ...
    
    async def create_image(
        self,
        request: ImageGenerationRequest,
        context: Optional[Any] = None
    ) -> ImageGenerationResponse:
        """Create an image."""
        ...


class BaseProvider(ABC):
    """
    Base class for all providers.
    Implements common functionality and defines the interface for provider-specific implementations.
    """
    
    def __init__(self, provider_name: str):
        """
        Initialize the provider.
        
        Args:
            provider_name: Name of the provider
        """
        self._name = provider_name
    
    @property
    def name(self) -> str:
        """Get the provider name."""
        return self._name
    
    @abstractmethod
    async def create_chat_completion(
        self, 
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> ChatCompletionResponse:
        """
        Create a chat completion.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Returns:
            Chat completion response
        """
        pass
    
    @abstractmethod
    async def create_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> AsyncGenerator[ChatCompletionStreamResponse, None]:
        """
        Create a streaming chat completion.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Yields:
            Streaming response chunks
        """
        pass
    
    @abstractmethod
    async def create_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[Any] = None
    ) -> EmbeddingResponse:
        """
        Create embeddings.
        
        Args:
            request: Embeddings request
            context: Additional context
            
        Returns:
            Embeddings response
        """
        pass
    
    @abstractmethod
    async def create_image(
        self,
        request: ImageGenerationRequest,
        context: Optional[Any] = None
    ) -> ImageGenerationResponse:
        """
        Create an image.
        
        Args:
            request: Image generation request
            context: Additional context
            
        Returns:
            Image generation response
        """
        pass
    
    def prepare_headers(self, request_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers for provider API requests.
        
        Args:
            request_headers: Additional headers to include
            
        Returns:
            Prepared headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"AI-Gateway/0.1.0",
        }
        
        if request_headers:
            headers.update(request_headers)
        
        return headers