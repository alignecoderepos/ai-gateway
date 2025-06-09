"""
OpenAI provider implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
import logging
import json
import os
from datetime import datetime

from openai import AsyncOpenAI, AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion import Choice
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


class OpenAIProvider(BaseProvider):
    """
    Provider implementation for OpenAI.
    Handles API calls to OpenAI services for various AI capabilities.
    """
    
    def __init__(self):
        """Initialize the OpenAI provider."""
        super().__init__("openai")
        self.api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. Some functionality may not work.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.timeout = httpx.Timeout(DEFAULT_REQUEST_TIMEOUT)
    
    async def create_chat_completion(
        self, 
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> ChatCompletionResponse:
        """
        Create a chat completion using OpenAI.
        
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
            # Convert request to OpenAI format
            openai_messages = self._convert_messages(request.messages)
            
            # Prepare tools if present
            tools = self._prepare_tools(request)
            
            # Build request parameters
            params = {
                "model": request.model,
                "messages": openai_messages,
                "stream": False,
                "timeout": self.timeout,
            }
            
            # Add optional parameters if present
            for param in [
                "temperature", "top_p", "n", "max_tokens", 
                "presence_penalty", "frequency_penalty", "logit_bias",
                "user", "seed"
            ]:
                if hasattr(request, param) and getattr(request, param) is not None:
                    params[param] = getattr(request, param)
            
            # Add response format if present
            if request.response_format:
                params["response_format"] = request.response_format.model_dump()
            
            # Add tools if present
            if tools:
                params["tools"] = tools
                
                # Add tool_choice if present
                if request.tool_choice:
                    if isinstance(request.tool_choice, str):
                        params["tool_choice"] = request.tool_choice
                    else:
                        params["tool_choice"] = request.tool_choice.model_dump()
            # Legacy function calling support
            elif request.functions:
                params["functions"] = request.functions
                if request.function_call:
                    params["function_call"] = request.function_call
            
            # Make API call
            response = await self.client.chat.completions.create(**params)
            
            # Convert response to gateway format
            choices = []
            for choice_idx, choice in enumerate(response.choices):
                message = self._convert_openai_message(choice.message)
                choices.append(
                    ChatCompletionResponseChoice(
                        index=choice_idx,
                        message=message,
                        finish_reason=FinishReason(choice.finish_reason) if choice.finish_reason else None,
                        logprobs=choice.logprobs if hasattr(choice, "logprobs") else None
                    )
                )
            
            # Build usage
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
            
            # Build final response
            return ChatCompletionResponse(
                id=response.id,
                object=response.object,
                created=response.created,
                model=response.model,
                choices=choices,
                usage=usage,
                system_fingerprint=response.system_fingerprint if hasattr(response, "system_fingerprint") else None
            )
            
        except Exception as e:
            # Handle specific error types
            error_message = str(e)
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                raise AuthenticationError(f"OpenAI authentication error: {error_message}")
            elif "rate limit" in error_message.lower():
                raise RateLimitExceededError(f"OpenAI rate limit exceeded: {error_message}")
            else:
                raise ProviderError(f"OpenAI error: {error_message}")
    
    async def create_streaming_chat_completion(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> AsyncGenerator[ChatCompletionStreamResponse, None]:
        """
        Create a streaming chat completion using OpenAI.
        
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
            # Convert request to OpenAI format
            openai_messages = self._convert_messages(request.messages)
            
            # Prepare tools if present
            tools = self._prepare_tools(request)
            
            # Build request parameters
            params = {
                "model": request.model,
                "messages": openai_messages,
                "stream": True,
                "timeout": self.timeout,
            }
            
            # Add optional parameters if present
            for param in [
                "temperature", "top_p", "n", "max_tokens", 
                "presence_penalty", "frequency_penalty", "logit_bias",
                "user", "seed"
            ]:
                if hasattr(request, param) and getattr(request, param) is not None:
                    params[param] = getattr(request, param)
            
            # Add response format if present
            if request.response_format:
                params["response_format"] = request.response_format.model_dump()
            
            # Add tools if present
            if tools:
                params["tools"] = tools
                
                # Add tool_choice if present
                if request.tool_choice:
                    if isinstance(request.tool_choice, str):
                        params["tool_choice"] = request.tool_choice
                    else:
                        params["tool_choice"] = request.tool_choice.model_dump()
            # Legacy function calling support
            elif request.functions:
                params["functions"] = request.functions
                if request.function_call:
                    params["function_call"] = request.function_call
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)
            
            # Stream response chunks
            async for chunk in stream:
                # Convert chunk to gateway format
                choices = []
                for choice_idx, choice in enumerate(chunk.choices):
                    choices.append(
                        ChatCompletionStreamResponseChoice(
                            index=choice_idx,
                            delta=self._convert_openai_delta(choice.delta),
                            finish_reason=FinishReason(choice.finish_reason) if choice.finish_reason else None,
                            logprobs=choice.logprobs if hasattr(choice, "logprobs") else None
                        )
                    )
                
                # Build chunk response
                response = ChatCompletionStreamResponse(
                    id=chunk.id,
                    object="chat.completion.chunk",
                    created=chunk.created,
                    model=chunk.model,
                    choices=choices,
                    system_fingerprint=chunk.system_fingerprint if hasattr(chunk, "system_fingerprint") else None
                )
                
                yield response
                
        except Exception as e:
            # Handle specific error types
            error_message = str(e)
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                raise AuthenticationError(f"OpenAI authentication error: {error_message}")
            elif "rate limit" in error_message.lower():
                raise RateLimitExceededError(f"OpenAI rate limit exceeded: {error_message}")
            else:
                raise ProviderError(f"OpenAI error: {error_message}")
    
    async def create_embeddings(
        self,
        request: EmbeddingRequest,
        context: Optional[Any] = None
    ) -> EmbeddingResponse:
        """
        Create embeddings using OpenAI.
        
        Args:
            request: Embeddings request
            context: Additional context
            
        Returns:
            Embeddings response
            
        Raises:
            ProviderError: If the API call fails
        """
        try:
            params = {
                "model": request.model,
                "input": request.input,
                "timeout": self.timeout,
            }
            
            # Add optional parameters
            if request.user:
                params["user"] = request.user
            if request.encoding_format:
                params["encoding_format"] = request.encoding_format
            if request.dimensions:
                params["dimensions"] = request.dimensions
            
            # Make API call
            response = await self.client.embeddings.create(**params)
            
            # Convert response to gateway format
            data = []
            for idx, item in enumerate(response.data):
                data.append(
                    EmbeddingData(
                        index=idx,
                        embedding=item.embedding,
                        object="embedding"
                    )
                )
            
            # Build usage
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=0,  # Embeddings don't have completion tokens
                total_tokens=response.usage.total_tokens
            )
            
            # Build final response
            return EmbeddingResponse(
                object="list",
                data=data,
                model=response.model,
                usage=usage
            )
            
        except Exception as e:
            raise ProviderError(f"OpenAI embeddings error: {e}")
    
    async def create_image(
        self,
        request: ImageGenerationRequest,
        context: Optional[Any] = None
    ) -> ImageGenerationResponse:
        """
        Create an image using OpenAI.
        
        Args:
            request: Image generation request
            context: Additional context
            
        Returns:
            Image generation response
            
        Raises:
            ProviderError: If the API call fails
        """
        try:
            params = {
                "model": request.model,
                "prompt": request.prompt,
                "timeout": self.timeout,
            }
            
            # Add optional parameters
            if request.n is not None:
                params["n"] = request.n
            if request.size:
                params["size"] = request.size
            if request.response_format:
                params["response_format"] = request.response_format
            if request.quality:
                params["quality"] = request.quality
            if request.style:
                params["style"] = request.style
            if request.user:
                params["user"] = request.user
            
            # Make API call
            response = await self.client.images.generate(**params)
            
            # Convert response to gateway format
            data = []
            for item in response.data:
                image_data = ImageData(
                    url=item.url,
                    b64_json=item.b64_json,
                    revised_prompt=item.revised_prompt
                )
                data.append(image_data)
            
            # Build final response
            return ImageGenerationResponse(
                created=int(datetime.now().timestamp()),
                data=data
            )
            
        except Exception as e:
            raise ProviderError(f"OpenAI image generation error: {e}")
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[ChatCompletionMessageParam]:
        """
        Convert gateway message format to OpenAI format.
        
        Args:
            messages: Gateway format messages
            
        Returns:
            OpenAI format messages
        """
        openai_messages = []
        
        for message in messages:
            # Convert message content
            content = message.content
            
            # Handle structured content (text + images)
            if isinstance(content, list):
                # OpenAI requires a list of content parts
                converted_content = []
                
                for part in content:
                    if part.type == "text":
                        converted_content.append({
                            "type": "text",
                            "text": part.text
                        })
                    elif part.type == "image_url" and part.image_url:
                        converted_content.append({
                            "type": "image_url",
                            "image_url": part.image_url
                        })
                
                message_content = converted_content
            else:
                # Simple text content
                message_content = content
            
            # Build message object
            openai_message = {
                "role": message.role.value,
                "content": message_content
            }
            
            # Add name if present
            if message.name:
                openai_message["name"] = message.name
            
            # Add tool_call_id if present (for tool responses)
            if message.tool_call_id:
                openai_message["tool_call_id"] = message.tool_call_id
            
            # Add function_call if present (legacy)
            if message.function_call:
                openai_message["function_call"] = message.function_call
            
            # Add tool_calls if present
            if message.tool_calls:
                openai_message["tool_calls"] = message.tool_calls
            
            openai_messages.append(openai_message)
        
        return openai_messages
    
    def _convert_openai_message(self, message: Any) -> ChatMessage:
        """
        Convert OpenAI message format to gateway format.
        
        Args:
            message: OpenAI format message
            
        Returns:
            Gateway format message
        """
        # Handle content
        content = message.content
        
        # Check if content is structured (text + images)
        if isinstance(content, list):
            converted_content = []
            
            for part in content:
                if part.type == "text":
                    converted_content.append(
                        MessageContent(type="text", text=part.text)
                    )
                elif part.type == "image_url":
                    converted_content.append(
                        MessageContent(type="image_url", image_url=part.image_url)
                    )
            
            message_content = converted_content
        else:
            # Simple text content
            message_content = content
        
        # Build message object
        result = ChatMessage(
            role=Role(message.role),
            content=message_content,
            name=message.name if hasattr(message, "name") else None,
        )
        
        # Add tool_calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                tc_dict = {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                tool_calls.append(tc_dict)
            
            result.tool_calls = tool_calls
        
        # Add function_call if present (legacy)
        if hasattr(message, "function_call") and message.function_call:
            result.function_call = {
                "name": message.function_call.name,
                "arguments": message.function_call.arguments
            }
        
        return result
    
    def _convert_openai_delta(self, delta: Any) -> Dict[str, Any]:
        """
        Convert OpenAI delta format to gateway format.
        
        Args:
            delta: OpenAI format delta
            
        Returns:
            Gateway format delta as a dictionary
        """
        result = {}
        
        # Add role if present
        if hasattr(delta, "role") and delta.role:
            result["role"] = delta.role
        
        # Add content if present
        if hasattr(delta, "content") and delta.content is not None:
            result["content"] = delta.content
        
        # Add tool_calls if present
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            tool_calls = []
            for tool_call in delta.tool_calls:
                tc_dict = {"id": tool_call.id, "type": tool_call.type}
                
                if hasattr(tool_call, "function"):
                    tc_dict["function"] = {}
                    
                    if hasattr(tool_call.function, "name"):
                        tc_dict["function"]["name"] = tool_call.function.name
                    
                    if hasattr(tool_call.function, "arguments"):
                        tc_dict["function"]["arguments"] = tool_call.function.arguments
                
                tool_calls.append(tc_dict)
            
            result["tool_calls"] = tool_calls
        
        # Add function_call if present (legacy)
        if hasattr(delta, "function_call") and delta.function_call:
            function_call = {}
            
            if hasattr(delta.function_call, "name"):
                function_call["name"] = delta.function_call.name
            
            if hasattr(delta.function_call, "arguments"):
                function_call["arguments"] = delta.function_call.arguments
            
            result["function_call"] = function_call
        
        return result
    
    def _prepare_tools(self, request: ChatCompletionRequest) -> Optional[List[ChatCompletionToolParam]]:
        """
        Prepare tools for OpenAI request.
        
        Args:
            request: Chat completion request
            
        Returns:
            List of tools in OpenAI format, or None if no tools
        """
        if not request.tools:
            return None
        
        openai_tools = []
        
        for tool in request.tools:
            openai_tool = {
                "type": tool.type.value
            }
            
            if tool.type == "function":
                openai_tool["function"] = {
                    "name": tool.function.name,
                    "parameters": tool.function.parameters
                }
                
                if tool.function.description:
                    openai_tool["function"]["description"] = tool.function.description
            
            openai_tools.append(openai_tool)
        
        return openai_tools