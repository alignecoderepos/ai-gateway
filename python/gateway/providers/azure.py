"""Azure OpenAI provider implementation placeholder."""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from gateway.core.types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from gateway.errors.exceptions import ProviderError
from gateway.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AzureProvider(BaseProvider):
    """Placeholder provider for Azure OpenAI."""

    def __init__(self) -> None:
        super().__init__("azure")
        logger.warning("Azure provider is not fully implemented")

    async def create_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None,
    ) -> ChatCompletionResponse:
        raise ProviderError("Azure provider not implemented")

    async def create_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None,
    ) -> AsyncGenerator[ChatCompletionStreamResponse, None]:
        raise ProviderError("Azure provider not implemented")
        yield  # pragma: no cover

    async def create_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[Any] = None,
    ) -> EmbeddingResponse:
        raise ProviderError("Azure provider not implemented")

    async def create_image(
        self,
        request: ImageGenerationRequest,
        context: Optional[Any] = None,
    ) -> ImageGenerationResponse:
        raise ProviderError("Azure provider not implemented")
