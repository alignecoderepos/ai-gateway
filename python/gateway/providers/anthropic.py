"""
Anthropic provider implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
import logging
import json
import os
from datetime import datetime
import re

from anthropic import AsyncAnthropic
import httpx

from gateway.providers.base import BaseProvider
from gateway.core.types import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse,
    ChatCompletionResponseChoice, ChatCompletionStreamResponseChoice,
    EmbeddingRequest, EmbeddingResponse, EmbeddingData,
    ImageGenerationRequest, ImageGenerationResponse, ImageData,
    Usage, ChatMessage, Role, FinishReason, MessageContent, ToolCall
)
from gateway.constants import DEFAULT_REQUEST_TIMEOUT
from gateway.config.settings import settings
from gateway.errors.exceptions import ProviderError, AuthenticationError, RateLimitExceededError


logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """
    Provider implementation for Anthropic.
    Handles API calls to Anthropic services for various AI capabilities.
    """
    
    def __init__(self):
        """Initialize the Anthropic provider."""
        super().__init__("anthropic")
        self.api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.warning("Anthropic API key not found. Some functionality may not work.")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.timeout = DEFAULT_REQUEST_TIMEOUT
    
    async def create_chat_completion(
        self, 
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> ChatCompletionResponse:
        """
        Create a chat completion using Anthropic.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Returns:
            Chat completion response
            
        Raises:
            ProviderError: If the API call fails
            AuthenticationError: If authentication fails
            RateLimitExceededError: If rate limits are exceeded
        """
        try:
            # Convert request to Anthropic format
            anthropic_messages = self._convert_messages(request.messages)
            
            # Prepare tools if present
            tools = self._prepare_tools(request)
            
            # Build request parameters
            params = {
                "model": request.model,
                "messages": anthropic_messages,
                "timeout": self.timeout,
            }
            
            # Add optional parameters if present
            if request.max_tokens is not None:
                params["max_tokens"] = request.max_tokens
            if request.temperature is not None:
                params["temperature"] = request.temperature
            if request.top_p is not None:
                params["top_p"] = request.top_p
            if request.stop is not None:
                params["stop_sequences"] = request.stop if isinstance(request.stop, list) else [request.stop]
            if request.user:
                params["metadata"] = {"user_id": request.user}
            if request.stream:
                params["stream"] = request.stream
            
            # Add tools if present
            if tools:
                params["tools"] = tools
                
                # Add tool_choice if present
                if request.tool_choice:
                    if isinstance(request.tool_choice, str):
                        params["tool_choice"] = request.tool_choice
                    else:
                        params["tool_choice"] = request.tool_choice.model_dump()
            
            # Make API call
            response = await self.client.messages.create(**params)
            
            # Extract content
            content = response.content[0].text if response.content else ""
            
            # Extract tool calls if present
            tool_calls = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.input)
                        }
                    }
                    for tc in response.tool_calls
                ]
            
            # Build message
            message = ChatMessage(
                role=Role.ASSISTANT,
                content=content,
                tool_calls=tool_calls
            )
            
            # Create choices
            choices = [
                ChatCompletionResponseChoice(
                    index=0,
                    message=message,
                    finish_reason=self._map_stop_reason(response.stop_reason),
                    logprobs=None
                )
            ]
            
            # Build usage
            usage = Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
            )
            
            # Generate a unique ID
            completion_id = f"chatcmpl-{response.id}"
            
            # Build final response
            return ChatCompletionResponse(
                id=completion_id,
                object="chat.completion",
                created=int(datetime.now().timestamp()),
                model=response.model,
                choices=choices,
                usage=usage,
                system_fingerprint=response.system if hasattr(response, "system") else None
            )
            
        except Exception as e:
            # Handle specific error types
            error_message = str(e)
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                raise AuthenticationError(f"Anthropic authentication error: {error_message}")
            elif "rate limit" in error_message.lower():
                raise RateLimitExceededError(f"Anthropic rate limit exceeded: {error_message}")
            else:
                raise ProviderError(f"Anthropic error: {error_message}")
    
    async def create_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> AsyncGenerator[ChatCompletionStreamResponse, None]:
        """
        Create a streaming chat completion using Anthropic.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Yields:
            Streaming response chunks
            
        Raises:
            ProviderError: If the API call fails
            AuthenticationError: If authentication fails
            RateLimitExceededError: If rate limits are exceeded
        """
        try:
            # Convert request to Anthropic format
            anthropic_messages = self._convert_messages(request.messages)
            
            # Prepare tools if present
            tools = self._prepare_tools(request)
            
            # Build request parameters
            params = {
                "model": request.model,
                "messages": anthropic_messages,
                "timeout": self.timeout,
                "stream": True,
            }
            
            # Add optional parameters if present
            if request.max_tokens is not None:
                params["max_tokens"] = request.max_tokens
            if request.temperature is not None:
                params["temperature"] = request.temperature
            if request.top_p is not None:
                params["top_p"] = request.top_p
            if request.stop is not None:
                params["stop_sequences"] = request.stop if isinstance(request.stop, list) else [request.stop]
            if request.user:
                params["metadata"] = {"user_id": request.user}
            
            # Add tools if present
            if tools:
                params["tools"] = tools
                
                # Add tool_choice if present
                if request.tool_choice:
                    if isinstance(request.tool_choice, str):
                        params["tool_choice"] = request.tool_choice
                    else:
                        params["tool_choice"] = request.tool_choice.model_dump()
            
            # Make streaming API call
            stream = await self.client.messages.create(**params)
            
            # Generate a unique ID for the completion
            completion_id = f"chatcmpl-anthropic-{datetime.now().timestamp()}"
            created_time = int(datetime.now().timestamp())
            
            # Stream response chunks
            async for chunk in stream:
                # Handle different types of chunks
                if hasattr(chunk, "type"):
                    # Content block (text)
                    if chunk.type == "content_block_delta":
                        # Create choices
                        choices = [
                            ChatCompletionStreamResponseChoice(
                                index=0,
                                delta={"content": chunk.delta.text},
                                finish_reason=None
                            )
                        ]
                        
                        # Build chunk response
                        response = ChatCompletionStreamResponse(
                            id=completion_id,
                            object="chat.completion.chunk",
                            created=created_time,
                            model=request.model,
                            choices=choices
                        )
                        
                        yield response
                    
                    # Tool call
                    elif chunk.type == "tool_use":
                        # Extract tool call information
                        tool_call = {
                            "id": chunk.id,
                            "type": "function",
                            "function": {
                                "name": chunk.name,
                                "arguments": json.dumps(chunk.input)
                            }
                        }
                        
                        # Create choices
                        choices = [
                            ChatCompletionStreamResponseChoice(
                                index=0,
                                delta={"tool_calls": [tool_call]},
                                finish_reason=None
                            )
                        ]
                        
                        # Build chunk response
                        response = ChatCompletionStreamResponse(
                            id=completion_id,
                            object="chat.completion.chunk",
                            created=created_time,
                            model=request.model,
                            choices=choices
                        )
                        
                        yield response
                    
                    # Message stop
                    elif chunk.type == "message_stop":
                        # Create choices
                        choices = [
                            ChatCompletionStreamResponseChoice(
                                index=0,
                                delta={},
                                finish_reason=self._map_stop_reason(chunk.stop_reason)
                            )
                        ]
                        
                        # Build final chunk with usage
                        usage = None
                        if hasattr(chunk, "usage"):
                            usage = Usage(
                                prompt_tokens=chunk.usage.input_tokens,
                                completion_tokens=chunk.usage.output_tokens,
                                total_tokens=chunk.usage.input_tokens + chunk.usage.output_tokens
                            )
                        
                        response = ChatCompletionStreamResponse(
                            id=completion_id,
                            object="chat.completion.chunk",
                            created=created_time,
                            model=request.model,
                            choices=choices,
                            usage=usage
                        )
                        
                        yield response
                
        except Exception as e:
            # Handle specific error types
            error_message = str(e)
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                raise AuthenticationError(f"Anthropic authentication error: {error_message}")
            elif "rate limit" in error_message.lower():
                raise RateLimitExceededError(f"Anthropic rate limit exceeded: {error_message}")
            else:
                raise ProviderError(f"Anthropic error: {error_message}")
    
    async def create_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[Any] = None
    ) -> EmbeddingResponse:
        """
        Create embeddings using Anthropic.
        
        Args:
            request: Embeddings request
            context: Additional context
            
        Returns:
            Embeddings response
            
        Raises:
            ProviderError: If the API call fails
        """
        # Anthropic does not have an embeddings API yet
        raise ProviderError("Anthropic embeddings are not supported")
    
    async def create_image(
        self,
        request: ImageGenerationRequest,
        context: Optional[Any] = None
    ) -> ImageGenerationResponse:
        """
        Create an image using Anthropic.
        
        Args:
            request: Image generation request
            context: Additional context
            
        Returns:
            Image generation response
            
        Raises:
            ProviderError: If the API call fails
        """
        # Anthropic does not have an image generation API yet
        raise ProviderError("Anthropic image generation is not supported")
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Convert gateway message format to Anthropic format.
        
        Args:
            messages: Gateway format messages
            
        Returns:
            Anthropic format messages
        """
        anthropic_messages = []
        
        for message in messages:
            # Handle system message specially
            if message.role == Role.SYSTEM:
                anthropic_messages.append({
                    "role": "system",
                    "content": message.content if isinstance(message.content, str) else ""
                })
                continue
            
            # Convert message content
            content = message.content
            
            # Build message object based on role
            if message.role == Role.USER:
                # Handle structured content (text + images)
                if isinstance(content, list):
                    # Anthropic requires a list of content parts
                    converted_content = []
                    
                    for part in content:
                        if part.type == "text" and part.text:
                            converted_content.append({
                                "type": "text",
                                "text": part.text
                            })
                        elif part.type == "image_url" and part.image_url:
                            converted_content.append({
                                "type": "image",
                                "source": part.image_url
                            })
                    
                    anthropic_messages.append({
                        "role": "user",
                        "content": converted_content
                    })
                else:
                    # Simple text content
                    anthropic_messages.append({
                        "role": "user",
                        "content": content
                    })
            
            elif message.role == Role.ASSISTANT:
                # Assistant content is always text for Anthropic
                text_content = content if isinstance(content, str) else ""
                
                assistant_message = {
                    "role": "assistant",
                    "content": text_content
                }
                
                # Add tool_calls if present
                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"])
                        }
                        for tc in message.tool_calls
                    ]
                
                anthropic_messages.append(assistant_message)
            
            elif message.role == Role.TOOL:
                # Tool responses in Anthropic
                anthropic_messages.append({
                    "role": "tool",
                    "content": content if isinstance(content, str) else "",
                    "name": message.name if message.name else "unknown_tool",
                    "tool_call_id": message.tool_call_id
                })
        
        return anthropic_messages
    
    def _prepare_tools(self, request: ChatCompletionRequest) -> Optional[List[Dict[str, Any]]]:
        """
        Prepare tools for Anthropic request.
        
        Args:
            request: Chat completion request
            
        Returns:
            List of tools in Anthropic format, or None if no tools
        """
        if not request.tools:
            return None
        
        anthropic_tools = []
        
        for tool in request.tools:
            if tool.type == "function":
                anthropic_tool = {
                    "name": tool.function.name,
                    "description": tool.function.description or "",
                    "input_schema": tool.function.parameters
                }
                
                anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools if anthropic_tools else None
    
    def _map_stop_reason(self, stop_reason: Optional[str]) -> Optional[FinishReason]:
        """
        Map Anthropic stop reason to gateway finish reason.
        
        Args:
            stop_reason: Anthropic stop reason
            
        Returns:
            Gateway finish reason
        """
        if not stop_reason:
            return None
        
        if stop_reason == "end_turn":
            return FinishReason.STOP
        elif stop_reason == "max_tokens":
            return FinishReason.LENGTH
        elif stop_reason == "tool_use":
            return FinishReason.TOOL_CALLS
        elif "content_filter" in stop_reason:
            return FinishReason.CONTENT_FILTER
        else:
            return FinishReason.STOP